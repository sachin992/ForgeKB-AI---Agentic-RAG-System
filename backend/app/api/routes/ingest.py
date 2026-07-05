from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import DocumentRegistry, User
from app.db.session import get_db
from app.tasks import ingest_datasource_task

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    uploads = Path(settings.uploads_dir)
    uploads.mkdir(parents=True, exist_ok=True)
    target = uploads / file.filename
    target.write_bytes(await file.read())

    row = db.query(DocumentRegistry).filter(DocumentRegistry.file_path == str(target)).first()
    if row:
        row.version += 1
        row.is_deleted = False
        row.status = "Pending"
        row.last_error = ""
    else:
        row = DocumentRegistry(
            file_path=str(target),
            file_hash="",
            source_type="file",
            status="Pending",
            version=1,
            is_deleted=False,
        )
        db.add(row)
    db.commit()
    db.refresh(row)

    task = ingest_datasource_task.delay(row.id)
    row.task_id = task.id
    row.status = "Indexing"
    db.add(row)
    db.commit()

    return {
        "status": row.status,
        "file": file.filename,
        "datasource_id": row.id,
        "task_id": row.task_id,
    }


@router.post("/run")
def ingest_all(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.query(DocumentRegistry).filter(DocumentRegistry.is_deleted == False).all()
    queued = []
    for row in rows:
        task = ingest_datasource_task.delay(row.id)
        row.task_id = task.id
        row.status = "Indexing"
        db.add(row)
        queued.append({"datasource_id": row.id, "task_id": task.id})
    db.commit()
    return {"queued": queued, "count": len(queued)}
