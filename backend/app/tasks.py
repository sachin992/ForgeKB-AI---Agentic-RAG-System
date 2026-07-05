import json
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session

from app.db.models import AuditLog, DocumentRegistry
from app.db.session import SessionLocal
from app.services.rag.ingestion import run_ingestion_pipeline
from app.worker import celery_app

logger = get_task_logger(__name__)


def _set_status(
    db: Session,
    datasource_id: int,
    status: str | None = None,
    error: str = "",
    progress_percent: int | None = None,
    stage: str | None = None,
    details: dict | None = None,
) -> None:
    row = db.query(DocumentRegistry).filter(DocumentRegistry.id == datasource_id).first()
    if not row:
        return

    if status is not None:
        row.status = status
    if progress_percent is not None:
        row.progress_percent = max(0, min(100, progress_percent))
    if stage is not None:
        row.stage = stage
    row.last_error = error

    telemetry = []
    try:
        telemetry = json.loads(row.telemetry_json or "[]")
    except Exception:
        telemetry = []

    telemetry.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "status": row.status,
            "progress_percent": row.progress_percent,
            "stage": row.stage,
            "details": details or {},
        }
    )
    row.telemetry_json = json.dumps(telemetry[-50:])

    db.add(row)
    db.commit()


@celery_app.task(name="app.tasks.ingest_datasource_task", bind=True)
def ingest_datasource_task(self, datasource_id: int):
    db: Session = SessionLocal()
    try:
        _set_status(db, datasource_id, status="Indexing", progress_percent=10, stage="started", details={})

        def _progress_callback(percent: int, stage: str, details: dict | None = None):
            _set_status(
                db,
                datasource_id,
                status="Indexing",
                progress_percent=percent,
                stage=stage,
                details=details or {},
            )

        result = run_ingestion_pipeline(progress_callback=_progress_callback)
        _set_status(
            db,
            datasource_id,
            status="Completed",
            progress_percent=100,
            stage="completed",
            details=result,
        )
        db.add(
            AuditLog(
                action="ingestion.completed",
                resource=f"datasource:{datasource_id}",
                details=str(result),
            )
        )
        db.commit()
        return result
    except Exception as exc:
        logger.exception("ingestion failed")
        _set_status(
            db,
            datasource_id,
            status="Failed",
            error=str(exc),
            stage="failed",
            details={"error": str(exc)},
        )
        db.add(
            AuditLog(
                action="ingestion.failed",
                resource=f"datasource:{datasource_id}",
                details=str(exc),
            )
        )
        db.commit()
        raise
    finally:
        db.close()
