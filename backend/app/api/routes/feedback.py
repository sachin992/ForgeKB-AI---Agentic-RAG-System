from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import Feedback, User
from app.db.session import get_db
from app.schemas import FeedbackRequest

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("")
def add_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = Feedback(
        user_id=user.id,
        message_id=payload.message_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(row)
    db.commit()
    return {"status": "saved"}
