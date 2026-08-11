import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import require_role
from app.core.config import settings
from app.core.database import get_db
from app.services.data_ingestion import DataIngestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}
CSV_EXTENSIONS = {".csv"}

# Read the upload in chunks so a large file cannot be buffered entirely in
# memory before the size limit is applied.
CHUNK_SIZE = 1024 * 1024


def _safe_filename(filename: str) -> str:
    """
    Reduce an uploaded filename to a harmless basename.

    Strips any directory components and characters outside a conservative
    allow-list, so a name like '../../etc/passwd' cannot escape the upload
    directory.
    """
    base = os.path.basename(filename or "").replace("\\", "/").split("/")[-1]
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip(". ")
    return cleaned[:120] or "upload"


async def _save_upload(file: UploadFile, allowed_extensions: set) -> Path:
    """Validate and stream an upload to disk, returning the stored path."""
    safe_name = _safe_filename(file.filename)
    extension = Path(safe_name).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Expected one of: "
                   f"{', '.join(sorted(allowed_extensions))}",
        )

    upload_dir = Path(settings.UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)

    destination = upload_dir / f"{uuid.uuid4()}_{safe_name}"
    # Belt and braces: confirm the resolved path really is inside the directory.
    if upload_dir not in destination.resolve().parents:
        raise HTTPException(status_code=400, detail="Invalid file name.")

    written = 0
    try:
        with open(destination, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                written += len(chunk)
                if written > settings.MAX_UPLOAD_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds the maximum upload size of "
                               f"{settings.MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
                    )
                buffer.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:  # noqa: BLE001
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Could not store upload: {exc}")

    if written == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return destination


def _discard(path: Path) -> None:
    """
    Best-effort removal of a stored upload we are not going to keep.

    Never raises: failing to tidy up a scratch file must not turn a clean
    validation response into a 500.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Could not remove rejected upload %s", path, exc_info=True)


def _ingest(db: Session, path: Path, field_code: str, original_name: str) -> Dict[str, Any]:
    service = DataIngestionService(db)
    result = service.process_file(str(path), field_code)

    if result.get("status") == "retired":
        db.rollback()
        _discard(path)
        raise HTTPException(
            status_code=422,
            detail=result.get("message", "This field is not managed by this application."),
        )

    if result.get("status") == "error":
        db.rollback()
        raise HTTPException(status_code=400,
                            detail=result.get("message", "Processing failed"))

    return {
        "filename": original_name,
        "field_code": result.get("field_code", field_code),
        "wells_created": result.get("wells_created", 0),
        "wells_updated": result.get("wells_updated", 0),
        "tests_created": result.get("tests_created", 0),
        "tests_skipped": result.get("tests_skipped", 0),
        "erosionals_created": result.get("erosionals_created", 0),
        "envelope_points": result.get("envelope_points", 0),
        "errors": result.get("errors", []),
        "status": result.get("status", "success"),
    }


@router.post("/excel", response_model=Dict[str, Any])
async def upload_excel(
    file: UploadFile = File(...),
    field_code: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "engineer"])),
):
    """Upload a WOEnv field workbook. Re-uploading the same file is a no-op."""
    path = await _save_upload(file, EXCEL_EXTENSIONS)
    return _ingest(db, path, field_code, file.filename)


@router.post("/csv", response_model=Dict[str, Any])
async def upload_csv(
    file: UploadFile = File(...),
    field_code: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "engineer"])),
):
    """
    CSV upload.

    Not yet supported: ingestion depends on the multi-sheet structure of the
    field workbooks (historical data, erosional rates and envelope data), which
    a single CSV cannot express. This previously accepted the file and then
    failed inside the Excel reader with an opaque error.
    """
    raise HTTPException(
        status_code=501,
        detail="CSV upload is not supported. Please upload the .xlsx field "
               "workbook, which carries the Historical Data, Erosional Rates "
               "and Envelope Data sheets that ingestion requires.",
    )
