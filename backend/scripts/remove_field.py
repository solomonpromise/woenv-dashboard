"""
Remove a field and everything attached to it.

Deletes, in dependency order: envelope points, erosional rates, test data,
wells, then the field itself.

    python -m scripts.remove_field OGIN YOKRI --dry-run
    python -m scripts.remove_field OGIN YOKRI

This is irreversible for the database. The data can be re-imported from the
original workbooks, but only after the code is re-added to
`data_ingestion.FIELD_CODE_MAP` - see RETIRED_FIELD_CODES there.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models.envelope_data import EnvelopeData  # noqa: E402
from app.models.erosional_rate import ErosionalRate  # noqa: E402
from app.models.field import Field  # noqa: E402
from app.models.reservoir import Reservoir  # noqa: E402
from app.models.test_data import TestData  # noqa: E402
from app.models.well import Well  # noqa: E402


def remove_field(db, code: str, dry_run: bool) -> dict:
    field = db.query(Field).filter(Field.code == code).first()
    if field is None:
        return {"code": code, "found": False}

    well_ids = [w.id for w in db.query(Well).filter(Well.field_id == field.id).all()]

    counts = {
        "code": code,
        "name": field.name,
        "found": True,
        "wells": len(well_ids),
        "tests": 0,
        "erosional": 0,
        "envelope": 0,
        "reservoirs": db.query(Reservoir).filter(Reservoir.field_id == field.id).count(),
    }

    if well_ids:
        counts["tests"] = db.query(TestData).filter(TestData.well_id.in_(well_ids)).count()
        counts["erosional"] = (db.query(ErosionalRate)
                               .filter(ErosionalRate.well_id.in_(well_ids)).count())
        counts["envelope"] = (db.query(EnvelopeData)
                              .filter(EnvelopeData.well_id.in_(well_ids)).count())

    if dry_run:
        return counts

    # Children first: these tables carry foreign keys onto wells.
    if well_ids:
        for model, column in ((EnvelopeData, EnvelopeData.well_id),
                              (ErosionalRate, ErosionalRate.well_id),
                              (TestData, TestData.well_id)):
            db.query(model).filter(column.in_(well_ids)).delete(synchronize_session=False)
        db.query(Well).filter(Well.id.in_(well_ids)).delete(synchronize_session=False)

    db.query(Reservoir).filter(Reservoir.field_id == field.id).delete(
        synchronize_session=False)
    db.query(Field).filter(Field.id == field.id).delete(synchronize_session=False)
    db.commit()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("codes", nargs="+", help="Field codes, e.g. OGIN YOKRI")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be deleted without writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        for code in args.codes:
            result = remove_field(db, code, args.dry_run)
            if not result["found"]:
                print(f"  {code}: not present, nothing to do")
                continue
            verb = "would delete" if args.dry_run else "deleted"
            print(f"  {code} ({result['name']}): {verb} "
                  f"{result['wells']} wells, {result['tests']} tests, "
                  f"{result['erosional']} erosional, {result['envelope']} envelope, "
                  f"{result['reservoirs']} reservoirs")
    finally:
        db.close()

    print("Dry run - nothing written." if args.dry_run else "Removal complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
