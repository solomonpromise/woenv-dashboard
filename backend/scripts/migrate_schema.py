"""
Idempotent schema migration for the corrected data model.

The project creates its tables with `Base.metadata.create_all`, which never
alters an existing table. This script brings a database that predates the
data-model fixes up to date without dropping anything.

    python -m scripts.migrate_schema
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.models import *  # noqa: F401,F403,E402  - register all mappers

# (table, column, DDL type)
NEW_COLUMNS = [
    ("wells", "prod_method", "VARCHAR(30)"),
    ("envelope_data", "source", "VARCHAR(20)"),
    ("erosional_rates", "reservoir_press_psia", "DOUBLE PRECISION"),
    ("erosional_rates", "gor_scfb", "DOUBLE PRECISION"),
    ("erosional_rates", "oil_sg_60", "DOUBLE PRECISION"),
    ("erosional_rates", "gas_sg", "DOUBLE PRECISION"),
    ("erosional_rates", "casing_id_in", "DOUBLE PRECISION"),
    ("erosional_rates", "screen", "VARCHAR(50)"),
    ("erosional_rates", "vc", "DOUBLE PRECISION"),
    ("erosional_rates", "vs", "DOUBLE PRECISION"),
    ("erosional_rates", "q_max_vsm", "DOUBLE PRECISION"),
    ("erosional_rates", "dd_press", "DOUBLE PRECISION"),
    ("erosional_rates", "prosper_pi", "DOUBLE PRECISION"),
    ("erosional_rates", "prosper_erosion", "DOUBLE PRECISION"),
    ("erosional_rates", "gross_rate_stbd", "DOUBLE PRECISION"),
    ("erosional_rates", "q_erosion_ann_destab", "DOUBLE PRECISION"),
    ("erosional_rates", "sand_rate_pptb", "DOUBLE PRECISION"),
    ("erosional_rates", "updated_at", "TIMESTAMP WITH TIME ZONE"),
]

STATEMENTS = [
    # bsw_percent now stores a true percentage; widen nothing, but make the
    # unique constraint that prevents duplicate wells explicit.
    """
    DO $$ BEGIN
        ALTER TABLE wells ADD CONSTRAINT uq_wells_field_name UNIQUE (field_id, name);
    EXCEPTION WHEN duplicate_table OR duplicate_object THEN NULL;
    END $$;
    """,
    "CREATE INDEX IF NOT EXISTS ix_envelope_data_well_source ON envelope_data (well_id, source)",
    "CREATE INDEX IF NOT EXISTS ix_test_data_well_start ON test_data (well_id, test_start)",
]


def main() -> int:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)

    added = 0
    with engine.begin() as conn:
        for table, column, ddl_type in NEW_COLUMNS:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN "{column}" {ddl_type}'))
            print(f"  + {table}.{column}")
            added += 1

        for statement in STATEMENTS:
            try:
                conn.execute(text(statement))
            except Exception as exc:  # noqa: BLE001
                print(f"  ! skipped: {str(exc).splitlines()[0]}")

    print(f"Schema migration complete ({added} column(s) added).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
