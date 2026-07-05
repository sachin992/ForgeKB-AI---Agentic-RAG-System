import json
from typing import Any
from collections.abc import AsyncGenerator

from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatMessage, ChatSession, User
from app.services.rag.graph import graph_app
from app.services.rag.guardrails import post_generation_guardrail, pre_generation_guardrail


async def stream_answer_events(
    db: Session,
    user: User,
    user_message: str,
    session_id: int | None,
) -> AsyncGenerator[dict[str, Any], None]:
    ok, result = pre_generation_guardrail(user_message)
    if not ok:
        yield {"event": "error", "message": result}
        yield {"event": "done"}
        return

    if session_id is None:
        session = ChatSession(user_id=user.id, title=user_message[:60] or "New Chat")
        db.add(session)
        db.commit()
        db.refresh(session)
        yield {"event": "session", "session_id": session.id}
    else:
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
            .first()
        )
        if not session:
            yield {"event": "error", "message": "Session not found"}
            yield {"event": "done"}
            return
        yield {"event": "session", "session_id": session.id}

    db.add(ChatMessage(session_id=session.id, role="user", content=user_message, citations_json="[]"))
    db.commit()

    recent_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(6)
        .all()
    )
    history_context = "\n".join([f"{m.role}: {m.content}" for m in reversed(recent_messages)])

    graph_result = graph_app.invoke(
        {
            "query": result,
            "query_type": "",
            "refined_query": "",
            "route_strategy": "",
            "requester_user_id": user.id,
            "requester_role": user.role,
            "contexts": [],
        }
    )
    contexts = graph_result.get("contexts", [])

    if not contexts or len(contexts) < settings.min_contexts_for_answer:
        abstain = "I do not have enough grounded context to answer this safely."
        yield {"event": "confidence", "avg_confidence": 0.0, "route_strategy": graph_result.get("route_strategy", "balanced")}
        yield {"event": "token", "token": abstain}
        yield {"event": "citations", "citations": []}
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=abstain,
                citations_json="[]",
                metadata_json=json.dumps({"abstained": True}),
            )
        )
        db.commit()
        yield {"event": "done"}
        return

    avg_conf = sum([float(c.get("confidence", 0.0)) for c in contexts]) / max(len(contexts), 1)
    yield {
        "event": "confidence",
        "avg_confidence": round(avg_conf, 4),
        "route_strategy": graph_result.get("route_strategy", "balanced"),
        "context_count": len(contexts),
    }

    if avg_conf < settings.confidence_floor:
        abstain = "I cannot confidently answer from the indexed knowledge right now."
        yield {"event": "token", "token": abstain}
        yield {"event": "citations", "citations": []}
        db.add(
            ChatMessage(
                session_id=session.id,
                role="assistant",
                content=abstain,
                citations_json="[]",
                metadata_json=json.dumps({"abstained": True, "avg_confidence": avg_conf}),
            )
        )
        db.commit()
        yield {"event": "done"}
        return

    context_block = "\n\n".join(
        [
            f"[Source: {c['source']} | Chunk: {c['chunk_id']}]\n"
            f"Context Window:\n{c.get('parent_context', c['text'])}"
            for c in contexts
        ]
    )

    llm = ChatOpenAI(model=settings.openai_model, api_key=settings.openai_api_key, temperature=0)
    prompt = (
        "You are a grounded RAG assistant. Use only provided context. "
        "If answer is not present, say so. Add citations [source|chunk_id].\n\n"
        f"Recent conversation:\n{history_context}\n\n"
        f"Context:\n{context_block}\n\n"
        f"User query:\n{result}\n"
    )

    full_answer = ""
    async for chunk in llm.astream(prompt):
        token = chunk.content or ""
        full_answer += token
        if token:
            yield {"event": "token", "token": token}

    citations = [
        {
            "source": c.get("source", ""),
            "chunk_id": c.get("chunk_id", ""),
            "parent_id": c.get("parent_id", ""),
            "snippet": (c.get("text", "") or "")[:180],
            "anchor": f"{c.get('source', '')}::{c.get('chunk_id', '')}",
        }
        for c in contexts
    ]
    full_answer = post_generation_guardrail(full_answer, citations)

    assistant_row = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=full_answer,
        citations_json=json.dumps(citations),
        metadata_json=json.dumps(
            {
                "route_strategy": graph_result.get("route_strategy", "balanced"),
                "avg_confidence": avg_conf,
                "abstained": False,
            }
        ),
    )
    db.add(assistant_row)
    db.commit()
    db.refresh(assistant_row)

    yield {"event": "citations", "citations": citations}
    yield {"event": "done", "session_id": session.id, "message_id": assistant_row.id}


async def stream_answer(
    db: Session,
    user: User,
    user_message: str,
    session_id: int | None,
) -> AsyncGenerator[str, None]:
    async for event in stream_answer_events(db, user, user_message, session_id):
        if event.get("event") == "token":
            yield str(event.get("token", ""))
