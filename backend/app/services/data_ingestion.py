"""
Ingestion of WOEnv field workbooks into the database.

Unit and column notes, established by cross-checking the workbooks against
their own derived columns:

* `Raw BSW (%)` holds a true percentage (0-100) while `BSW (%)` holds the same
  value as a fraction (0-1). BSW is stored here as a **percentage**.
* `Raw Gas/Duration (Mscf/d)` and `Calculated Gas (Mscf/d)` are labelled Mscf/d
  but actually carry MMscf/d - `Calculated Net * GOR` reproduces the value only
  after multiplying by 1e6, not 1e3. Gas is therefore derived from oil rate and
  GOR where possible, which is self-consistent regardless of the label.
* `GOR (scf/stb)` is gas per barrel of **oil**. The previous implementation
  wrote it into the GLR column as well; GLR (gas per barrel of gross liquid)
  is now derived as `GOR * (1 - BSW)`.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models.envelope_data import EnvelopeData
from app.models.erosional_rate import ErosionalRate
from app.models.field import Field
from app.models.test_data import TestData
from app.models.well import Well
from app.services import workbook as wb
from app.services.calculations import glr_from_gor
from app.services.well_status import (normalize_production_method,
                                      normalize_status)

logger = logging.getLogger(__name__)

FIELD_CODE_MAP = {
    "UGHELLI-EAST": "UGHE",
    "UGHELLI EAST": "UGHE",
    "UGHE": "UGHE",
    "UTOROGU": "UTOR",
    "UTOR": "UTOR",
    "UGHELLI-WEST": "UGWest",
    "UGHELLI WEST": "UGWest",
    "UGHW": "UGWest",
    "UGWEST": "UGWest",
}

FIELD_NAMES = {
    "UGHE": "Ughelli-East",
    "UTOR": "Utorogu",
    "UGWest": "Ughelli-West",
}

# Fields this application no longer manages. Recognised only so that uploading
# one of their workbooks fails with a clear explanation instead of the generic
# "cannot determine field code". To bring a field back, move its patterns into
# FIELD_CODE_MAP and add a display name to FIELD_NAMES, then re-run
# `python -m scripts.reingest_uploads`.
RETIRED_FIELD_CODES = {
    "OGIN": ["OGIN"],
    "YOKRI": ["YOKRI"],
}

# Well-name suffix conventions used across the field workbooks.
WELL_TYPE_BY_SUFFIX = {"T": "Tubing", "L": "Gas Lift", "S": "Subsea"}

MAX_REPORTED_ERRORS = 20

# Nigerian oil production long predates these workbooks, but a test date before
# this is a parsing artefact rather than a record.
MIN_TEST_DATE = datetime(1970, 1, 2)


def looks_like_well_name(name: Optional[str]) -> bool:
    """
    True for values that plausibly name a well.

    Workbook rows sometimes carry a bare facility code in the conduit column
    (a row reading just 'UGHE'), which would otherwise be created as a well.
    Real conduit names always carry a numeric identifier.
    """
    if not name:
        return False
    text = name.strip()
    return len(text) >= 4 and any(ch.isdigit() for ch in text)


def detect_field_code(filename: str, facility_values=None) -> str:
    """
    Detect the field code from the facility column, falling back to filename.

    Returns "UNKNOWN" when nothing matches, or "RETIRED:<CODE>" when the
    workbook belongs to a field this application no longer manages.
    """
    haystacks = []
    if facility_values is not None:
        haystacks.extend(
            str(value).upper().strip()
            for value in pd.Series(facility_values).dropna().unique()
        )
    haystacks.append(os.path.basename(filename).upper())

    for text in haystacks:
        for pattern, code in FIELD_CODE_MAP.items():
            if pattern in text:
                return code

    # Only consider a workbook retired once no active field has claimed it.
    for text in haystacks:
        for code, patterns in RETIRED_FIELD_CODES.items():
            if any(pattern in text for pattern in patterns):
                return f"RETIRED:{code}"

    return "UNKNOWN"


class DataIngestionService:
    """Ingests a single workbook, upserting fields, wells, tests and envelopes."""

    def __init__(self, db: Session):
        self.db = db

    # -- public API ---------------------------------------------------------

    def process_file(self, file_path: str, field_code: str = "") -> Dict[str, Any]:
        try:
            # Close the handle before doing anything else: on Windows an open
            # ExcelFile keeps the file locked, so the caller cannot delete or
            # move the upload afterwards.
            with pd.ExcelFile(file_path, engine="openpyxl") as excel:
                sheet_names = list(excel.sheet_names)
        except Exception as exc:  # noqa: BLE001 - surfaced to the caller
            return {"status": "error", "message": f"Cannot open Excel file: {exc}"}

        result: Dict[str, Any] = {
            "status": "success",
            "field_code": field_code,
            "wells_created": 0,
            "wells_updated": 0,
            "tests_created": 0,
            "tests_skipped": 0,
            "erosionals_created": 0,
            "envelope_points": 0,
            "errors": [],
        }

        hist_sheet = wb.find_sheet(sheet_names, wb.HISTORICAL_SHEETS)
        if not hist_sheet:
            result["status"] = "error"
            result["message"] = f"No historical data sheet found. Available: {sheet_names}"
            result["errors"].append(result["message"])
            return result

        bean_models = self._read_bean_models(file_path, sheet_names)

        hist = self._process_historical(file_path, hist_sheet, field_code, bean_models)
        if hist.get("status") == "retired":
            # Stop before touching the erosional and envelope sheets, so a
            # retired field cannot be recreated through a side door.
            result["status"] = "retired"
            result["field_code"] = hist.get("field_code", "")
            result["message"] = hist.get("message", "")
            return result
        if hist.get("status") == "error":
            result["status"] = "error"
            result["message"] = hist.get("message", "Historical data processing failed")
            result["errors"].extend(hist.get("errors", []))
            return result

        result.update({k: hist[k] for k in
                       ("field_code", "wells_created", "wells_updated",
                        "tests_created", "tests_skipped") if k in hist})
        result["errors"].extend(hist.get("errors", []))
        field_code = result["field_code"]

        erosional_sheet = wb.find_sheet(sheet_names, wb.EROSIONAL_SHEETS)
        if erosional_sheet:
            eros = self._process_erosional(file_path, erosional_sheet, field_code)
            result["erosionals_created"] = eros.get("records", 0)
            result["errors"].extend(eros.get("errors", []))

        envelope_sheet = wb.find_sheet(sheet_names, wb.ENVELOPE_SHEETS)
        if envelope_sheet:
            env = self._process_envelope(file_path, envelope_sheet, field_code)
            result["envelope_points"] = env.get("points", 0)
            result["errors"].extend(env.get("errors", []))

        if result["errors"]:
            result["status"] = "partial"
        result["errors"] = result["errors"][:MAX_REPORTED_ERRORS]
        return result

    # -- historical test data ----------------------------------------------

    def _process_historical(
        self,
        file_path: str,
        sheet_name: str,
        field_code: str,
        bean_models: Dict[str, str],
    ) -> Dict[str, Any]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "message": f"Cannot read {sheet_name!r}: {exc}"}

        if df.empty:
            return {"status": "error", "message": f"Sheet {sheet_name!r} is empty"}

        cols = wb.ColumnResolver(df.columns)

        if not field_code or field_code == "UNKNOWN":
            facility_col = cols.find("Facility")
            field_code = detect_field_code(
                file_path, df[facility_col] if facility_col is not None else None
            )
        if field_code.startswith("RETIRED:"):
            retired = field_code.split(":", 1)[1]
            return {
                "status": "retired",
                "field_code": retired,
                "message": f"{retired} is not managed by this application. "
                           f"Its workbooks are ignored.",
            }
        if field_code == "UNKNOWN":
            return {"status": "error", "message": "Cannot determine field code from file"}

        field = self._get_or_create_field(field_code)

        wells_created = wells_updated = tests_created = tests_skipped = 0
        errors: List[str] = []
        well_cache: Dict[str, Well] = {}
        # Test dates already present for each well, so re-uploading a workbook
        # updates rather than duplicating its rows.
        seen_tests: Dict[int, set] = {}

        for idx, row in df.iterrows():
            try:
                well_name = wb.safe_text(cols.value(row, "Conduit", "CONDUIT", "Well"))
                if not looks_like_well_name(well_name):
                    continue

                test_start = self._parse_date(cols.value(row, "Test Start Date", "TEST_START_DATE"))
                if test_start is None:
                    continue

                if well_name in well_cache:
                    well = well_cache[well_name]
                else:
                    well, created = self._upsert_well(field.id, well_name, row, cols, bean_models)
                    well_cache[well_name] = well
                    wells_created += int(created)
                    wells_updated += int(not created)
                    seen_tests[well.id] = {
                        d for (d,) in self.db.query(TestData.test_start)
                        .filter(TestData.well_id == well.id).all()
                    }

                if test_start in seen_tests.setdefault(well.id, set()):
                    tests_skipped += 1
                    continue

                self.db.add(self._build_test_data(well.id, test_start, row, cols))
                seen_tests[well.id].add(test_start)
                tests_created += 1

            except Exception as exc:  # noqa: BLE001 - one bad row must not abort the file
                errors.append(f"Row {idx}: {exc}")
                continue

        self.db.commit()
        return {
            "status": "success",
            "field_code": field_code,
            "wells_created": wells_created,
            "wells_updated": wells_updated,
            "tests_created": tests_created,
            "tests_skipped": tests_skipped,
            "errors": errors,
        }

    def _build_test_data(self, well_id: int, test_start, row, cols: wb.ColumnResolver) -> TestData:
        """Build a TestData row, reconciling the workbook's unit quirks."""
        oil = wb.safe_float(cols.value(row, "Calculated Net (stb/d)", "CALCULATED_NET"))
        water = wb.safe_float(cols.value(row, "Calculated Water (stb/d)", "CALCULATED_WATER"))
        gross = wb.safe_float(cols.value(
            row, "Gross (stb/d)", "Raw Gross/ Duration (stb/d)", "GROSS"))
        if gross is None and oil is not None and water is not None:
            gross = oil + water

        bsw_percent = self._resolve_bsw(row, cols, oil, water, gross)
        gor = wb.safe_float(cols.value(row, "GOR (scf/stb)", "GOR"))
        raw_fgor = wb.safe_float(cols.value(row, "Raw FGOR (scf/stb)", "RAW_FGOR"))

        # Prefer deriving gas from oil x GOR: it is unit-consistent, whereas the
        # workbook's own gas columns are mislabelled by a factor of 1000.
        gas_scfd = oil * gor if (oil is not None and gor is not None) else None
        gas_mscfd = gas_scfd / 1000.0 if gas_scfd is not None else None

        glr = None
        if gor is not None and bsw_percent is not None:
            glr = glr_from_gor(gor, bsw_percent / 100.0)
        if glr is None and gas_scfd is not None and gross:
            glr = gas_scfd / gross

        return TestData(
            well_id=well_id,
            test_start=test_start,
            duration_hours=wb.safe_int(cols.value(row, "Duration", "DURATION")),
            status=normalize_status(cols.value(row, "Status", "STATUS")),
            result_status=wb.safe_text(cols.value(
                row, "Results Status", "RESULT_STATUS", "Seperator Result Status")),
            fthp_psig=wb.safe_float(cols.value(row, "FTHP (psi)", "FTHP")),
            choke_size=wb.safe_float(cols.value(row, "Choke_1 (1/64th)", "CHOKE_1")),
            gross_rate_stbd=gross,
            oil_rate_stbd=oil,
            water_rate_stbd=water,
            gas_rate_mscfd=gas_mscfd,
            gas_lift_rate_mscfd=wb.safe_float(cols.value(
                row, "Raw Gaslift/Duration (Mscf/d)", "RAW_GAS_LIFT/DURATION")),
            bsw_percent=bsw_percent,
            sand_pptb=wb.safe_float(cols.value(row, "Sand (pptb)", "SAND")),
            fgor_scfstb=raw_fgor if raw_fgor is not None else gor,
            glr_scfstb=glr,
            sep_pressure=wb.safe_float(cols.value(
                row, "Separator Pressure (psi)", "SEP_PRES")),
            sep_temp=wb.safe_float(cols.value(
                row, "Separator Temp (deg F)", "SEP_TEMP")),
        )

    @staticmethod
    def _resolve_bsw(row, cols: wb.ColumnResolver, oil, water, gross) -> Optional[float]:
        """
        Return BSW as a percentage (0-100).

        'Raw BSW (%)' is already a percentage; 'BSW (%)' is a fraction despite
        its name. Where neither is usable, BSW is recomputed from the water and
        gross rates.
        """
        raw = wb.safe_float(cols.value(row, "Raw BSW (%)"))
        if raw is not None and 0.0 <= raw <= 100.0:
            return raw

        fraction = wb.safe_float(cols.value(row, "BSW (%)", "BSW"))
        if fraction is not None:
            # Tolerate files where this column is genuinely a percentage.
            if 0.0 <= fraction <= 1.0:
                return fraction * 100.0
            if 1.0 < fraction <= 100.0:
                return fraction

        if water is not None and gross:
            computed = water / gross * 100.0
            if 0.0 <= computed <= 100.0:
                return computed
        return None

    @staticmethod
    def _parse_date(value):
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass

        if isinstance(value, pd.Timestamp):
            parsed = value
        else:
            try:
                parsed = pd.to_datetime(value, errors="coerce")
            except Exception:  # noqa: BLE001
                return None
        if parsed is None or pd.isna(parsed):
            return None

        # Test dates are day-resolution; dropping sub-second precision keeps
        # pandas from warning about discarded nanoseconds on every row.
        result = parsed.to_pydatetime().replace(microsecond=0)

        # Reject implausible dates. A blank or zero cell parses to the Unix
        # epoch, which would otherwise land in the history as 1 Jan 1970 and
        # drag every trend chart's axis back fifty years.
        if not (MIN_TEST_DATE <= result <= datetime.now() + timedelta(days=365)):
            return None
        return result

    # -- erosional rates ----------------------------------------------------

    def _process_erosional(self, file_path: str, sheet_name: str, field_code: str) -> Dict[str, Any]:
        errors: List[str] = []
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl")
            records = wb.parse_erosional_sheet(df)
        except Exception as exc:  # noqa: BLE001
            return {"records": 0, "errors": [f"Erosional sheet: {exc}"]}

        field = self._get_or_create_field(field_code)
        count = 0

        for record in records:
            try:
                well = self._find_well(field.id, record["well_name"])
                if well is None:
                    continue

                row = (self.db.query(ErosionalRate)
                       .filter(ErosionalRate.well_id == well.id)
                       .first())
                if row is None:
                    row = ErosionalRate(well_id=well.id)
                    self.db.add(row)

                row.block = wb.safe_text(record.get("block"))
                for attr in ("reservoir_press_psia", "reservoir_pb_psia", "rsi_scfb",
                             "boi_vv", "tr_deg_f", "sg_oil", "oil_cp", "water_cp",
                             "gor_scfb", "oil_sg_60", "gas_sg", "casing_id_in",
                             "gross_rate_stbd", "prosper_pi", "prosper_erosion",
                             "dd_press", "vc", "vs", "q_max_vcm", "q_max_vsm",
                             "q_erosion_wellbore", "q_erosion_screen",
                             "q_erosion_ann_destab", "q_erosion", "sand_rate_pptb"):
                    value = wb.safe_float(record.get(attr))
                    if value is not None:
                        setattr(row, attr, value)

                row.screen = wb.safe_text(record.get("screen")) or row.screen
                row.material_type = wb.safe_text(record.get("material_type")) or row.material_type
                sand = wb.safe_text(record.get("sand_presence"))
                if sand is not None:
                    row.sand_presence = sand.strip().lower() in ("yes", "y", "true", "1")

                # Fall back to the wellbore limit when the governing figure is
                # blank, and ignore the 99999 sentinel used for "not limiting".
                if row.q_erosion is None or row.q_erosion >= 99999:
                    if row.q_erosion_wellbore and row.q_erosion_wellbore < 99999:
                        row.q_erosion = row.q_erosion_wellbore
                count += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Erosional {record.get('well_name')}: {exc}")

        self.db.commit()
        return {"records": count, "errors": errors}

    # -- operating envelope -------------------------------------------------

    def _process_envelope(self, file_path: str, sheet_name: str, field_code: str) -> Dict[str, Any]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine="openpyxl")
            parsed = wb.parse_envelope_sheet(df)
        except Exception as exc:  # noqa: BLE001
            return {"points": 0, "errors": [f"Envelope sheet: {exc}"]}

        well_name = parsed.get("well_name")
        points = parsed.get("points") or []
        if not well_name or not points:
            return {"points": 0, "errors": []}

        field = self._get_or_create_field(field_code)
        well = self._find_well(field.id, well_name)
        if well is None:
            return {"points": 0, "errors": [f"Envelope references unknown well {well_name!r}"]}

        # The sheet describes exactly one well, so replace that well's stored
        # workbook envelope rather than appending to it on every upload.
        (self.db.query(EnvelopeData)
         .filter(EnvelopeData.well_id == well.id,
                 EnvelopeData.source == EnvelopeData.SOURCE_WORKBOOK)
         .delete(synchronize_session=False))

        for point in points:
            self.db.add(EnvelopeData(
                well_id=well.id,
                gross_rate=point.get("gross"),
                thp_curve=point.get("thp"),
                flp=point.get("flp"),
                critical_flow=point.get("critical_flow"),
                source=EnvelopeData.SOURCE_WORKBOOK,
            ))

        self.db.commit()
        return {"points": len(points), "errors": []}

    def _read_bean_models(self, file_path: str, sheet_names: List[str]) -> Dict[str, str]:
        sheet = wb.find_sheet(sheet_names, wb.ENVELOPE_HEADER_SHEETS)
        if not sheet:
            return {}
        try:
            df = pd.read_excel(file_path, sheet_name=sheet, header=None, engine="openpyxl")
            return wb.parse_bean_model_assignments(df)
        except Exception:  # noqa: BLE001 - bean model is optional metadata
            return {}

    # -- persistence helpers ------------------------------------------------

    def _get_or_create_field(self, field_code: str) -> Field:
        field = self.db.query(Field).filter(Field.code == field_code).first()
        if field is None:
            field = Field(
                name=FIELD_NAMES.get(field_code, field_code),
                code=field_code,
                location="Nigeria",
            )
            self.db.add(field)
            self.db.commit()
            self.db.refresh(field)
        return field

    def _find_well(self, field_id: int, well_name: str) -> Optional[Well]:
        name = (well_name or "").strip()
        if not name:
            return None
        return (self.db.query(Well)
                .filter(Well.field_id == field_id, Well.name == name)
                .first())

    def _upsert_well(
        self,
        field_id: int,
        well_name: str,
        row,
        cols: wb.ColumnResolver,
        bean_models: Dict[str, str],
    ):
        """Create or update a well. Returns (well, created)."""
        prod_method = normalize_production_method(
            cols.value(row, "Prod_Method", "PROD_METHOD"))
        status = normalize_status(cols.value(row, "Status", "STATUS"))
        well_type = WELL_TYPE_BY_SUFFIX.get(well_name.strip()[-1:].upper(), "Unknown")

        well = self._find_well(field_id, well_name)
        created = well is None
        if created:
            well = Well(field_id=field_id, name=well_name.strip())
            self.db.add(well)

        well.well_type = well_type
        well.status = status
        if prod_method:
            well.prod_method = prod_method
        if bean_models.get(well_name):
            well.bean_model = bean_models[well_name]

        self.db.commit()
        self.db.refresh(well)
        return well, created
