from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import AuditLog, User
from app.db.session import get_db
from app.services.eval_service import run_eval

router = APIRouter(prefix="/eval", tags=["evaluation"])


@router.get("/run")
def run_eval_route(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = run_eval()
    db.add(
        AuditLog(
            user_id=user.id,
            action="eval.run",
            resource="dataset",
            details=str(result),
        )
    )
    db.commit()
    return result
