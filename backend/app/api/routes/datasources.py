import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_current_user
from app.core.config import settings
from app.db.models import AuditLog, DocumentRegistry, User
from app.db.session import get_db
from app.schemas import RetryIngestRequest
from app.services.rate_limit import allow_request
from app.tasks import ingest_datasource_task
from app.worker import celery_app

router = APIRouter(prefix="/datasources", tags=["datasources"])


def _safe_name(upload_name: str) -> str:
    # Prevent path traversal; keep only basename in storage path.
    return Path(upload_name).name


def _can_access_row(user: User, row: DocumentRegistry) -> bool:
    if user.role == "admin":
        return True

    owner_user_id = row.owner_user_id
    if owner_user_id is None:
        try:
            payload = json.loads(row.metadata_json or "{}")
            owner_user_id = int(payload.get("owner_user_id")) if payload.get("owner_user_id") is not None else None
        except Exception:
            owner_user_id = None
    return owner_user_id == user.id


def _storage_path_for(db: Session, user: User, filename: str) -> Path:
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    clean = _safe_name(filename)
    stem = Path(clean).stem
    suffix = Path(clean).suffix
    if user.role == "admin":
        base = uploads / "admin"
    else:
        base = uploads / "users" / str(user.id)
    base.mkdir(parents=True, exist_ok=True)

    target = base / clean
    idx = 1
    while target.exists() or db.query(DocumentRegistry).filter(DocumentRegistry.file_path == str(target)).first():
        target = base / f"{stem} ({idx}){suffix}"
        idx += 1
    return target


def _upsert_registry_row(db: Session, user: User, target: Path, original_name: str) -> DocumentRegistry:
    row = db.query(DocumentRegistry).filter(DocumentRegistry.file_path == str(target)).first()
    visibility = "global" if user.role == "admin" else "private"
    metadata = {
        "owner_user_id": user.id,
        "owner_email": user.email,
        "owner_role": user.role,
        "visibility": visibility,
        "display_name": original_name,
    }

    if row:
        row.version += 1
        row.owner_user_id = user.id
        row.visibility = visibility
        row.display_name = original_name
        row.metadata_json = json.dumps(metadata)
        row.status = "Pending"
        row.progress_percent = 0
        row.stage = "pending"
        row.telemetry_json = "[]"
        row.is_deleted = False
        row.last_error = ""
    else:
        row = DocumentRegistry(
            file_path=str(target),
            display_name=original_name,
            owner_user_id=user.id,
            visibility=visibility,
            metadata_json=json.dumps(metadata),
            file_hash="",
            source_type="file",
            status="Pending",
            progress_percent=0,
            stage="pending",
            telemetry_json="[]",
            version=1,
            is_deleted=False,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return row


@router.post("/upload")
async def upload_datasource(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not allow_request(f"upload:{user.id}", limit=10, window=60):
        raise HTTPException(status_code=429, detail="Upload rate limit exceeded")

    target = _storage_path_for(db, user, file.filename)
    target.write_bytes(await file.read())

    row = _upsert_registry_row(db, user, target, _safe_name(file.filename))

    task = ingest_datasource_task.delay(row.id)
    row.task_id = task.id
    row.status = "Indexing"
    row.progress_percent = 5
    row.stage = "queued"
    telemetry = json.loads(row.telemetry_json or "[]")
    telemetry.append({"stage": "queued", "progress_percent": 5, "status": "Indexing"})
    row.telemetry_json = json.dumps(telemetry[-50:])
    db.add(row)
    db.add(
        AuditLog(
            user_id=user.id,
            action="datasource.uploaded",
            resource=str(row.id),
            details=file.filename,
        )
    )
    db.commit()

    return {
        "id": row.id,
        "status": row.status,
        "task_id": row.task_id,
        "file_path": row.file_path,
    }


@router.post("/upload/bulk")
async def upload_datasource_bulk(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_admin_user),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    queued = []
    for f in files:
        target = _storage_path_for(db, user, f.filename)
        target.write_bytes(await f.read())
        row = _upsert_registry_row(db, user, target, _safe_name(f.filename))

        task = ingest_datasource_task.delay(row.id)
        row.task_id = task.id
        row.status = "Indexing"
        row.progress_percent = 5
        row.stage = "queued"
        telemetry = json.loads(row.telemetry_json or "[]")
        telemetry.append({"stage": "queued", "progress_percent": 5, "status": "Indexing"})
        row.telemetry_json = json.dumps(telemetry[-50:])
        db.add(row)
        db.add(
            AuditLog(
                user_id=user.id,
                action="datasource.bulk_uploaded",
                resource=str(row.id),
                details=f.filename,
            )
        )
        db.commit()

        queued.append({"id": row.id, "task_id": task.id, "file_path": row.file_path})

    return {"queued": queued, "count": len(queued)}


@router.get("")
def list_datasources(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    db.add(
        AuditLog(
            user_id=user.id,
            action="datasource.list",
            resource="all",
            details="",
        )
    )
    db.commit()
    rows = (
        db.query(DocumentRegistry)
        .filter(DocumentRegistry.is_deleted == False)
        .order_by(DocumentRegistry.updated_at.desc())
        .all()
    )
    if user.role == "admin":
        rows = [r for r in rows if (r.visibility or "private") == "global"]
    else:
        rows = [r for r in rows if _can_access_row(user, r)]
    return [
        {
            "id": r.id,
            "file_path": r.file_path,
            "display_name": r.display_name or Path(r.file_path).name,
            "source_type": r.source_type,
            "owner_user_id": r.owner_user_id,
            "visibility": r.visibility,
            "metadata_json": r.metadata_json,
            "status": r.status,
            "progress_percent": r.progress_percent,
            "stage": r.stage,
            "telemetry_json": r.telemetry_json,
            "version": r.version,
            "is_deleted": r.is_deleted,
            "task_id": r.task_id,
            "last_error": r.last_error,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
    ]


@router.delete("/{datasource_id}")
def delete_datasource(datasource_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    row = db.query(DocumentRegistry).filter(DocumentRegistry.id == datasource_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Data source not found")
    if not _can_access_row(user, row):
        raise HTTPException(status_code=403, detail="You can delete only your own files")

    display_name = row.display_name or Path(row.file_path).name
    rows_to_delete = [row]

    if user.role != "admin":
        rows_to_delete = (
            db.query(DocumentRegistry)
            .filter(
                DocumentRegistry.is_deleted == False,
                DocumentRegistry.owner_user_id == user.id,
                DocumentRegistry.display_name == display_name,
            )
            .all()
        )
        if not rows_to_delete:
            rows_to_delete = [row]

    deleted_ids: list[int] = []
    for r in rows_to_delete:
        if not _can_access_row(user, r):
            continue
        r.is_deleted = True
        r.status = "Pending"
        r.progress_percent = 0
        r.stage = "delete_pending"
        db.add(r)
        deleted_ids.append(r.id)

        file_path = Path(r.file_path)
        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except Exception:
                pass

    db.add(
        AuditLog(
            user_id=user.id,
            action="datasource.deleted",
            resource=",".join([str(i) for i in deleted_ids]) or str(datasource_id),
            details=display_name,
        )
    )
    db.commit()

    task = ingest_datasource_task.delay((deleted_ids[0] if deleted_ids else row.id))
    for r in rows_to_delete:
        if r.id not in deleted_ids:
            continue
        r.task_id = task.id
        r.status = "Indexing"
        r.progress_percent = 5
        r.stage = "queued"
        db.add(r)
    db.commit()

    return {
        "status": "queued",
        "task_id": task.id,
        "deleted_count": len(deleted_ids),
        "display_name": display_name,
    }


@router.post("/retry")
def retry_datasource(
    payload: RetryIngestRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = db.query(DocumentRegistry).filter(DocumentRegistry.id == payload.datasource_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Data source not found")
    if not _can_access_row(user, row):
        raise HTTPException(status_code=403, detail="You can retry only your own files")

    row.status = "Pending"
    row.progress_percent = 0
    row.stage = "retry_pending"
    row.last_error = ""
    db.add(row)
    db.commit()

    task = ingest_datasource_task.delay(row.id)
    row.task_id = task.id
    row.status = "Indexing"
    row.progress_percent = 5
    row.stage = "queued"
    db.add(row)
    db.commit()

    db.add(
        AuditLog(
            user_id=user.id,
            action="datasource.retry",
            resource=str(payload.datasource_id),
            details=row.file_path,
        )
    )
    db.commit()

    return {"status": "queued", "task_id": task.id}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    result = celery_app.AsyncResult(task_id)
    row = db.query(DocumentRegistry).filter(DocumentRegistry.task_id == task_id).first()
    if row and not _can_access_row(user, row):
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task_id,
        "state": result.state,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else False,
        "datasource": (
            {
                "id": row.id,
                "status": row.status,
                "progress_percent": row.progress_percent,
                "stage": row.stage,
                "telemetry_json": row.telemetry_json,
            }
            if row
            else None
        ),
    }
