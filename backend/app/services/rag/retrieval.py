import json
from pathlib import Path

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI
from rank_bm25 import BM25Okapi

from app.core.config import settings

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None


_reranker = None


def _route_query(query: str) -> dict:
    q = query.lower()
    if any(t in q for t in ["when", "date", "version", "exact", "id"]):
        return {"name": "factual", "bm25_weight": 0.65, "semantic_weight": 0.35, "k": 8}
    if any(t in q for t in ["summarize", "explain", "compare", "why"]):
        return {"name": "analytical", "bm25_weight": 0.35, "semantic_weight": 0.65, "k": 8}
    return {"name": "balanced", "bm25_weight": 0.5, "semantic_weight": 0.5, "k": settings.retrieval_top_k}


def _expand_queries(query: str) -> list[str]:
    if not settings.openai_api_key:
        return [query]

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    prompt = (
        "Generate up to 3 short retrieval queries for this user query. "
        "Return each on a new line with no numbering.\n\n"
        f"Query: {query}"
    )
    try:
        out = llm.invoke(prompt).content or ""
        rewrites = [line.strip(" -0123456789.") for line in out.splitlines() if line.strip()]
        unique = []
        seen = set()
        for q in [query] + rewrites:
            key = q.lower().strip()
            if key and key not in seen:
                seen.add(key)
                unique.append(q)
        return unique[:4]
    except Exception:
        return [query]


def _normalize_scores(items: list[dict], key: str) -> dict[str, float]:
    if not items:
        return {}
    values = [i.get(key, 0.0) for i in items]
    min_v, max_v = min(values), max(values)
    if max_v - min_v <= 1e-8:
        return {i["chunk_id"]: 1.0 for i in items}
    return {i["chunk_id"]: (i.get(key, 0.0) - min_v) / (max_v - min_v) for i in items}


def _add_parent_context(items: list[dict], chunks: list[dict], window: int = 1) -> list[dict]:
    chunk_map = {c.get("chunk_id", ""): c for c in chunks}
    source_index = {}
    for c in chunks:
        source_index.setdefault(c.get("source", ""), []).append(c)

    for source, rows in source_index.items():
        rows.sort(key=lambda r: r.get("chunk_id", ""))
        source_index[source] = rows

    out = []
    for item in items:
        row = chunk_map.get(item.get("chunk_id", ""))
        if not row:
            out.append(item)
            continue
        siblings = source_index.get(row.get("source", ""), [])
        idx = next((i for i, r in enumerate(siblings) if r.get("chunk_id", "") == row.get("chunk_id", "")), 0)
        lo = max(0, idx - window)
        hi = min(len(siblings), idx + window + 1)
        parent_context = "\n".join([r.get("text", "") for r in siblings[lo:hi]])
        merged = dict(item)
        merged["parent_id"] = row.get("parent_id", row.get("source", ""))
        merged["parent_context"] = parent_context
        out.append(merged)
    return out


def _load_manifest() -> dict:
    path = Path(settings.metadata_store_path)
    if not path.exists():
        return {"chunks": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _get_reranker():
    global _reranker
    if _reranker is None and CrossEncoder is not None:
        _reranker = CrossEncoder(settings.reranker_model)
    return _reranker


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _distance_to_similarity(distance: float) -> float:
    # FAISS returns distance-style scores for this index; lower is better.
    # Convert to a bounded similarity in [0, 1] for stable fusion.
    d = max(0.0, float(distance))
    return 1.0 / (1.0 + d)


def _can_view_chunk(chunk: dict, requester_user_id: int, requester_role: str) -> bool:
    visibility = (chunk.get("visibility") or "private").lower()
    if requester_role == "admin":
        return visibility == "global"

    owner_user_id = chunk.get("owner_user_id")
    try:
        owner_user_id = int(owner_user_id) if owner_user_id is not None else None
    except Exception:
        owner_user_id = None

    if visibility == "global":
        return True
    return owner_user_id == requester_user_id


def _latest_sources_by_display_name(chunks: list[dict]) -> set[str]:
    latest: dict[str, tuple[int, str]] = {}
    for c in chunks:
        source = c.get("source", "")
        if not source:
            continue
        display_name = c.get("display_name") or Path(source).name
        recency_id = c.get("recency_id")
        try:
            recency = int(recency_id) if recency_id is not None else 0
        except Exception:
            recency = 0

        current = latest.get(display_name)
        if current is None or recency > current[0]:
            latest[display_name] = (recency, source)

    return {src for _, src in latest.values()}


def hybrid_retrieve(query: str, k: int = 6, requester_user_id: int | None = None, requester_role: str = "user") -> list[dict]:
    manifest = _load_manifest()
    chunks = manifest.get("chunks", [])
    if requester_user_id is not None:
        chunks = [c for c in chunks if _can_view_chunk(c, requester_user_id, requester_role)]

    # If multiple files share the same display name, only keep the newest upload.
    allowed_sources = _latest_sources_by_display_name(chunks)
    if allowed_sources:
        chunks = [c for c in chunks if c.get("source", "") in allowed_sources]

    route = _route_query(query)
    expanded_queries = _expand_queries(query)
    k = max(k, route["k"])

    semantic_hits = []
    faiss_path = Path(settings.faiss_dir)
    if faiss_path.exists() and (faiss_path / "index.faiss").exists() and chunks:
        embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
        store = FAISS.load_local(settings.faiss_dir, embeddings, allow_dangerous_deserialization=True)
        docs_with_scores = []
        for q in expanded_queries:
            docs_with_scores.extend(store.similarity_search_with_score(q, k=k))
        semantic_hits = []
        for d, distance in docs_with_scores:
            source = d.metadata.get("source", "")
            if allowed_sources and source not in allowed_sources:
                continue
            owner_user_id = d.metadata.get("owner_user_id")
            visibility = d.metadata.get("visibility", "private")
            shadow_chunk = {
                "owner_user_id": owner_user_id,
                "visibility": visibility,
            }
            if requester_user_id is not None and not _can_view_chunk(shadow_chunk, requester_user_id, requester_role):
                continue
            semantic_hits.append(
                {
                    "chunk_id": d.metadata.get("chunk_id", ""),
                    "source": d.metadata.get("source", ""),
                    "text": d.page_content,
                    "semantic_score": _distance_to_similarity(float(distance)),
                    "owner_user_id": owner_user_id,
                    "visibility": visibility,
                }
            )

    keyword_hits = []
    if chunks:
        corpus = [c.get("text", "") for c in chunks]
        tokenized = [text.lower().split() for text in corpus]
        bm25 = BM25Okapi(tokenized)
        scores = [0.0 for _ in tokenized]
        for q in expanded_queries:
            q_scores = bm25.get_scores(q.lower().split())
            scores = [a + float(b) for a, b in zip(scores, q_scores)]
        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        keyword_hits = [
            {
                "chunk_id": chunks[i].get("chunk_id", ""),
                "source": chunks[i].get("source", ""),
                "text": chunks[i].get("text", ""),
                "bm25_score": float(scores[i]),
                "owner_user_id": chunks[i].get("owner_user_id"),
                "visibility": chunks[i].get("visibility", "private"),
            }
            for i in top_idx
        ]

    merged = {}
    for item in semantic_hits + keyword_hits:
        chunk_id = item["chunk_id"]
        if chunk_id not in merged:
            merged[chunk_id] = item
        else:
            if "semantic_score" in item and "semantic_score" in merged[chunk_id]:
                item = dict(item)
                item["semantic_score"] = max(float(merged[chunk_id]["semantic_score"]), float(item["semantic_score"]))
            merged[chunk_id].update(item)

    candidates = list(merged.values())[: max(2 * k, 10)]
    norm_sem = {
        c["chunk_id"]: _clamp01(float(c.get("semantic_score", 0.0)))
        for c in candidates
        if "semantic_score" in c
    }
    norm_bm = _normalize_scores([c for c in candidates if "bm25_score" in c], "bm25_score")
    for c in candidates:
        c["fusion_score"] = (
            route["semantic_weight"] * norm_sem.get(c["chunk_id"], 0.0)
            + route["bm25_weight"] * norm_bm.get(c["chunk_id"], 0.0)
        )

    reranker = _get_reranker()
    if reranker and candidates:
        pairs = [[query, c["text"]] for c in candidates]
        rr_scores = reranker.predict(pairs)
        for c, score in zip(candidates, rr_scores):
            c["rerank_score"] = float(score)
            c["final_score"] = 0.75 * c["rerank_score"] + 0.25 * c["fusion_score"]
        candidates.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)
    else:
        candidates.sort(key=lambda x: x.get("fusion_score", 0.0), reverse=True)

    top = _add_parent_context(candidates[:k], chunks, window=1)
    if top:
        raw_scores = [float(i.get("final_score", i.get("fusion_score", 0.0))) for i in top]
        min_score = min(raw_scores)
        max_score = max(raw_scores)
        span = max_score - min_score
        for i, raw in zip(top, raw_scores):
            if span <= 1e-8:
                i["confidence"] = 1.0
            else:
                i["confidence"] = _clamp01((raw - min_score) / span)

    return top
