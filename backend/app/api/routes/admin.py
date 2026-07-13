from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.deps import get_admin_user
from app.db.models import AuditLog, DocumentRegistry, Feedback, User
from app.db.session import get_db
from app.tasks import ingest_datasource_task

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    rows = db.query(User).order_by(User.created_at.desc()).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "role": (u.role or "user"),
            "created_at": u.created_at.isoformat(),
        }
        for u in rows
    ]


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    role = str(payload.get("role", "")).strip().lower()
    if role not in {"admin", "user"}:
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id and role != "admin":
        raise HTTPException(status_code=400, detail="You cannot demote yourself")

    old_role = target.role or "user"
    if old_role == role:
        return {
            "id": target.id,
            "email": target.email,
            "role": old_role,
            "updated": False,
        }

    target.role = role
    db.add(target)
    db.add(
        AuditLog(
            user_id=admin.id,
            action="admin.user_role_updated",
            resource=str(target.id),
            details=f"{old_role}->{role}",
        )
    )
    db.commit()
    db.refresh(target)

    return {
        "id": target.id,
        "email": target.email,
        "role": target.role,
        "updated": True,
    }


@router.delete("/users/{user_id}")
def offboard_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot offboard yourself")

    if (target.role or "user") == "admin":
        admin_count = db.query(User).filter(User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")

    user_datasources = (
        db.query(DocumentRegistry)
        .filter(DocumentRegistry.owner_user_id == target.id, DocumentRegistry.is_deleted == False)
        .all()
    )

    for row in user_datasources:
        row.is_deleted = True
        row.status = "Pending"
        row.progress_percent = 0
        row.stage = "offboard_delete_pending"
        p = Path(row.file_path)
        if p.exists() and p.is_file():
            try:
                p.unlink()
            except Exception:
                pass
        db.add(row)

    db.query(Feedback).filter(Feedback.user_id == target.id).delete(synchronize_session=False)
    offboard_email = target.email
    offboard_id = target.id
    db.delete(target)

    db.add(
        AuditLog(
            user_id=admin.id,
            action="admin.user_offboarded",
            resource=str(offboard_id),
            details=offboard_email,
        )
    )
    db.commit()

    task_ids: list[str] = []
    if user_datasources:
        for ds in user_datasources:
            task = ingest_datasource_task.delay(ds.id)
            row = db.query(DocumentRegistry).filter(DocumentRegistry.id == ds.id).first()
            if row:
                row.task_id = task.id
                row.status = "Indexing"
                row.progress_percent = 5
                row.stage = "queued"
                db.add(row)
            task_ids.append(task.id)
        db.commit()

    return {
        "status": "offboarded",
        "user_id": offboard_id,
        "email": offboard_email,
        "datasource_cleanup_task_id": task_ids[0] if task_ids else None,
        "datasource_cleanup_task_ids": task_ids,
    }
