"""
Celery tasks.

These delegate to the same services the API uses, rather than reimplementing
ingestion. The previous copy of `process_excel_upload` carried its own parsing
logic with the original column and unit bugs, so files processed through the
worker were wrong in ways files processed through the API were not.
"""

from app.core.database import SessionLocal
from app.tasks import celery_app


@celery_app.task(name="process_excel_upload")
def process_excel_upload(file_path: str, field_code: str = ""):
    """Ingest an uploaded workbook in the background."""
    from app.services.data_ingestion import DataIngestionService

    db = SessionLocal()
    try:
        return DataIngestionService(db).process_file(file_path, field_code)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()


@celery_app.task(name="compute_envelopes")
def compute_envelopes(well_id: int):
    """Recompute and persist a well's modelled operating envelope."""
    from app.services.envelope_computation import store_envelope_snapshot

    db = SessionLocal()
    try:
        return {
            "status": "success",
            "well_id": well_id,
            "result": store_envelope_snapshot(db, well_id),
        }
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return {"status": "error", "well_id": well_id, "message": str(exc)}
    finally:
        db.close()
