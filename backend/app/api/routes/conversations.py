from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import ChatSession, User
from app.db.session import get_db

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
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
