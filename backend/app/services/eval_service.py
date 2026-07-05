import json
from pathlib import Path

from app.core.config import settings
from app.services.rag.retrieval import hybrid_retrieve


def run_eval() -> dict:
    path = Path(settings.eval_dataset_path)
    if not path.exists():
        return {
            "total": 0,
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "context_precision": 0.0,
        }

    rows = json.loads(path.read_text(encoding="utf-8"))
    total = len(rows)
    if total == 0:
        return {
            "total": 0,
            "answer_relevancy": 0.0,
            "faithfulness": 0.0,
            "context_precision": 0.0,
        }

    hits = 0
    precision_sum = 0.0
    for row in rows:
        contexts = hybrid_retrieve(row.get("question", ""), k=6)
        expected_source = row.get("expected_source", "")
        source_hits = [c for c in contexts if expected_source and expected_source in c.get("source", "")]
        if source_hits:
            hits += 1
        precision_sum += min(len(source_hits), 1)

    score = hits / total
    return {
        "total": total,
        "answer_relevancy": round(score, 3),
        "faithfulness": round(score, 3),
        "context_precision": round(precision_sum / total, 3),
    }
