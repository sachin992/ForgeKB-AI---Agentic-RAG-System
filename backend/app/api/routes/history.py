from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import ChatMessage, ChatSession, User
from app.db.session import get_db

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/sessions")
def sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "title": r.title,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/sessions/{session_id}")
def session_messages(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        return []

    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "citations_json": m.citations_json,
            "metadata_json": m.metadata_json,
            "created_at": m.created_at.isoformat(),
        }
        for m in msgs
    ]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()
    return {"status": "deleted", "session_id": session_id}
