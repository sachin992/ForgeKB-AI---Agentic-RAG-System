import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas import ChatRequest
from app.services.rate_limit import allow_request
from app.services.rag.chat_service import stream_answer, stream_answer_events

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not allow_request(f"chat:{user.id}", limit=20, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    async def token_stream():
        async for token in stream_answer(db, user, payload.message, payload.session_id):
            yield token

    return StreamingResponse(token_stream(), media_type="text/plain")


@router.post("/stream")
async def chat_stream(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not allow_request(f"chat:{user.id}", limit=20, window=60):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    async def sse_stream():
        async for event in stream_answer_events(db, user, payload.message, payload.session_id):
            event_name = str(event.get("event", "message"))
            event_payload = {k: v for k, v in event.items() if k != "event"}
            yield f"event: {event_name}\ndata: {json.dumps(event_payload)}\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")
