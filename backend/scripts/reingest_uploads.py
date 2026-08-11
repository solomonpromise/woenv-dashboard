"""
Re-run ingestion over every workbook already in the uploads directory.

Ingestion is idempotent - tests are deduplicated on (well, test date) and the
workbook envelope is replaced rather than appended - so this is safe to run
repeatedly. Use it to backfill the erosional and envelope data that earlier
versions of the ingestion never read.

    python -m scripts.reingest_uploads
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.services.data_ingestion import DataIngestionService  # noqa: E402

SUPPORTED = {".xlsx", ".xlsm", ".xls"}


def main() -> int:
    upload_dir = Path(settings.UPLOAD_DIR)
    if not upload_dir.is_dir():
        print(f"Upload directory not found: {upload_dir.resolve()}")
        return 1

    files = sorted(p for p in upload_dir.iterdir()
                   if p.suffix.lower() in SUPPORTED and not p.name.startswith("~$"))
    if not files:
        print(f"No workbooks found in {upload_dir.resolve()}")
        return 0

    db = SessionLocal()
    totals = {"wells_created": 0, "tests_created": 0, "tests_skipped": 0,
              "erosionals_created": 0, "envelope_points": 0}
    try:
        for path in files:
            result = DataIngestionService(db).process_file(str(path), "")
            status = result.get("status")
            if status == "retired":
                # Workbooks for fields the app no longer manages are left on
                # disk but never imported.
                print(f"  skipped  {path.name[:58]:<58} "
                      f"{result.get('field_code', '?')} is retired")
                continue
            if status == "error":
                print(f"  ERROR  {path.name}: {result.get('message')}")
                continue
            for key in totals:
                totals[key] += result.get(key, 0)
            print(f"  {status:<8} {path.name[:58]:<58} "
                  f"field={result.get('field_code','?'):<7} "
                  f"wells+{result.get('wells_created',0):<4} "
                  f"tests+{result.get('tests_created',0):<5} "
                  f"eros={result.get('erosionals_created',0):<4} "
                  f"env={result.get('envelope_points',0)}")
            for err in result.get("errors", [])[:3]:
                print(f"           ! {err}")
    finally:
        db.close()

    print("\nTotals:", ", ".join(f"{k}={v}" for k, v in totals.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
