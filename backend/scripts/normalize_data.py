"""
One-off repair of data ingested by the previous, buggy ingestion code.

Fixes, in order:
  1. duplicate test rows sharing a (well_id, test_start)
  2. BSW stored as a fraction where a percentage is meant
  3. GLR columns that were populated with GOR
  4. gas rates recorded in MMscf/d under an Mscf/d column name
  5. free-text well statuses collapsed onto the canonical vocabulary

Safe to re-run: every step detects whether it has already been applied.

    python -m scripts.normalize_data [--dry-run]
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.models.envelope_data import EnvelopeData  # noqa: E402
from app.models.erosional_rate import ErosionalRate  # noqa: E402
from app.models.test_data import TestData  # noqa: E402
from app.models.well import Well  # noqa: E402
from app.services.calculations import glr_from_gor  # noqa: E402
from app.services.data_ingestion import looks_like_well_name  # noqa: E402
from app.services.well_status import normalize_status  # noqa: E402


def dedupe_tests(db, dry_run: bool) -> int:
    """Delete duplicate test rows, keeping the lowest id for each (well, date)."""
    duplicates = db.execute(text("""
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY well_id, test_start ORDER BY id
            ) AS rn
            FROM test_data
        ) ranked WHERE rn > 1
    """)).scalars().all()

    if duplicates and not dry_run:
        db.query(TestData).filter(TestData.id.in_(duplicates)).delete(
            synchronize_session=False)
        db.commit()
    return len(duplicates)


def drop_epoch_tests(db, dry_run: bool) -> int:
    """
    Delete test rows whose date failed to parse and landed on the Unix epoch.

    A blank or zero date cell used to be accepted verbatim, producing records
    dated 1 Jan 1970 that dragged every trend chart's axis back fifty years.
    """
    stale = (db.query(TestData.id)
             .filter(TestData.test_start < datetime(1970, 1, 2))
             .all())
    ids = [row[0] for row in stale]
    if ids and not dry_run:
        db.query(TestData).filter(TestData.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return len(ids)


def drop_non_well_rows(db, dry_run: bool) -> int:
    """
    Remove 'wells' created from facility-code rows, such as a bare 'OGIN'.

    Their tests go with them, since those rows were never real well tests.
    """
    bogus = [w for w in db.query(Well).all() if not looks_like_well_name(w.name)]
    if bogus and not dry_run:
        ids = [w.id for w in bogus]
        db.query(TestData).filter(TestData.well_id.in_(ids)).delete(synchronize_session=False)
        db.query(ErosionalRate).filter(ErosionalRate.well_id.in_(ids)).delete(
            synchronize_session=False)
        db.query(EnvelopeData).filter(EnvelopeData.well_id.in_(ids)).delete(
            synchronize_session=False)
        db.query(Well).filter(Well.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
    return len(bogus)


def dedupe_erosional(db, dry_run: bool) -> int:
    """
    Collapse erosional-rate rows to one per well.

    Earlier ingestion appended a fresh row on every upload instead of updating,
    so a well could accumulate one row per re-upload. The most recently updated
    row wins.
    """
    duplicates = db.execute(text("""
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY well_id
                ORDER BY (q_erosion IS NULL), updated_at DESC NULLS LAST, id DESC
            ) AS rn
            FROM erosional_rates
        ) ranked WHERE rn > 1
    """)).scalars().all()

    if duplicates and not dry_run:
        db.execute(text("DELETE FROM erosional_rates WHERE id = ANY(:ids)"),
                   {"ids": duplicates})
        db.commit()
    return len(duplicates)


def clear_zero_limits(db, dry_run: bool) -> int:
    """
    Null out non-physical erosional limits.

    A zero or negative Qerosion means "not computed" in the source workbook,
    not "this well may not flow"; leaving it as zero would make every test
    appear to breach the envelope.
    """
    result = db.execute(text("""
        UPDATE erosional_rates SET q_erosion = NULL
        WHERE q_erosion IS NOT NULL AND q_erosion <= 0
    """) if not dry_run else text("""
        SELECT count(*) FROM erosional_rates
        WHERE q_erosion IS NOT NULL AND q_erosion <= 0
    """))
    count = result.scalar() if dry_run else result.rowcount
    if not dry_run:
        db.commit()
    return count or 0


def fix_bsw(db, dry_run: bool) -> int:
    """
    Rescale BSW from fraction to percentage.

    Detected by the maximum: a column that never exceeds 1.0 across a thousand
    water-cut measurements is a fraction, not a percentage.
    """
    max_bsw = db.query(func.max(TestData.bsw_percent)).scalar()
    if max_bsw is None or max_bsw > 1.0:
        return 0

    rows = db.query(TestData).filter(TestData.bsw_percent.isnot(None)).all()
    if not dry_run:
        for row in rows:
            row.bsw_percent = row.bsw_percent * 100.0
        db.commit()
    return len(rows)


def fix_glr(db, dry_run: bool) -> int:
    """
    Recompute GLR from GOR and BSW.

    The old code wrote the workbook's GOR column into both fgor_scfstb and
    glr_scfstb. GLR is gas per barrel of gross liquid: GOR * (1 - BSW).
    """
    rows = (db.query(TestData)
            .filter(TestData.fgor_scfstb.isnot(None),
                    TestData.bsw_percent.isnot(None))
            .all())
    changed = 0
    for row in rows:
        glr = glr_from_gor(row.fgor_scfstb, row.bsw_percent / 100.0)
        if glr is None:
            continue
        if row.glr_scfstb is None or abs(row.glr_scfstb - glr) > 0.01:
            if not dry_run:
                row.glr_scfstb = glr
            changed += 1
    if changed and not dry_run:
        db.commit()
    return changed


def fix_gas_rate(db, dry_run: bool) -> int:
    """
    Rebuild gas rate from oil rate and GOR.

    The workbook's 'Calculated Gas (Mscf/d)' column actually carries MMscf/d;
    deriving gas from oil x GOR sidesteps the mislabelling entirely.
    """
    rows = (db.query(TestData)
            .filter(TestData.oil_rate_stbd.isnot(None),
                    TestData.fgor_scfstb.isnot(None))
            .all())
    changed = 0
    for row in rows:
        expected_mscfd = row.oil_rate_stbd * row.fgor_scfstb / 1000.0
        if row.gas_rate_mscfd is None or abs(row.gas_rate_mscfd - expected_mscfd) > 0.01:
            if not dry_run:
                row.gas_rate_mscfd = expected_mscfd
            changed += 1
    if changed and not dry_run:
        db.commit()
    return changed


def fix_statuses(db, dry_run: bool) -> int:
    """Collapse free-text statuses onto the canonical vocabulary."""
    changed = 0
    for well in db.query(Well).all():
        canonical = normalize_status(well.status)
        if canonical != well.status:
            if not dry_run:
                well.status = canonical
            changed += 1
    for row in db.query(TestData).filter(TestData.status.isnot(None)).all():
        canonical = normalize_status(row.status)
        if canonical != row.status:
            if not dry_run:
                row.status = canonical
            changed += 1
    if changed and not dry_run:
        db.commit()
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would change without writing")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        steps = [
            ("epoch-dated test rows removed", drop_epoch_tests),
            ("non-well rows removed", drop_non_well_rows),
            ("duplicate test rows removed", dedupe_tests),
            ("duplicate erosional rows removed", dedupe_erosional),
            ("non-physical erosional limits cleared", clear_zero_limits),
            ("BSW values rescaled to percent", fix_bsw),
            ("GLR values recomputed from GOR", fix_glr),
            ("gas rates rebuilt from oil x GOR", fix_gas_rate),
            ("statuses normalised", fix_statuses),
        ]
        for label, step in steps:
            count = step(db, args.dry_run)
            print(f"  {count:>6}  {label}")
    finally:
        db.close()

    print("Dry run - nothing written." if args.dry_run else "Normalisation complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
