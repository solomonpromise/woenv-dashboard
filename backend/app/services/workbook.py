"""
Low-level readers for the WOEnv Excel workbooks.

The workbooks are engineer-authored and irregular: header rows float, the
Erosional Rates sheet carries two independent header blocks side by side, and
several columns are mislabelled. Everything that knows about those quirks
lives here so the ingestion service can stay readable.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

# Sheet names, including the trailing-space variants present in the real files.
HISTORICAL_SHEETS = ["Historical Data ", "Historical Data", "Hist Data", "Hist Data "]
EROSIONAL_SHEETS = ["Erosional Rates", "Erosional Rates "]
ENVELOPE_SHEETS = ["Envelope Data", "Envelope Data "]
ENVELOPE_HEADER_SHEETS = ["Well Operating Envelope", "Well Operating Envelope "]


def find_sheet(available: List[str], candidates: List[str]) -> Optional[str]:
    """Match a sheet name, tolerating stray leading/trailing whitespace."""
    stripped = {str(s).strip(): s for s in available}
    for name in candidates:
        key = name.strip()
        if key in stripped:
            return stripped[key]
    return None


def safe_float(value: Any) -> Optional[float]:
    """Coerce a spreadsheet cell to float, returning None for blanks and text."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def safe_int(value: Any) -> Optional[int]:
    """Coerce to int via float, so that 24.0 becomes 24 and 'n/a' becomes None."""
    result = safe_float(value)
    if result is None:
        return None
    try:
        return int(round(result))
    except (TypeError, ValueError, OverflowError):
        return None


def safe_text(value: Any) -> Optional[str]:
    """Coerce to a trimmed string, returning None for blanks and NaN."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text or text.lower() in ("nan", "none", "null"):
        return None
    return text


class ColumnResolver:
    """
    Resolves logical field names to actual DataFrame columns.

    Matching is case-insensitive and whitespace-insensitive so that
    'FTHP (psi)', 'fthp (psi) ' and 'FTHP  (PSI)' all resolve alike.
    """

    def __init__(self, columns):
        self._lookup = {}
        for col in columns:
            self._lookup.setdefault(self._key(col), col)

    @staticmethod
    def _key(name: Any) -> str:
        return " ".join(str(name).split()).lower()

    def find(self, *candidates: str) -> Optional[Any]:
        for candidate in candidates:
            col = self._lookup.get(self._key(candidate))
            if col is not None:
                return col
        return None

    def value(self, row, *candidates: str) -> Any:
        col = self.find(*candidates)
        if col is None:
            return None
        return row.get(col)


# ---------------------------------------------------------------------------
# Erosional Rates sheet
# ---------------------------------------------------------------------------

# The sheet holds two header blocks. The left block (cols 0-13) is the fluid
# property summary; the right block, starting at the 'Conduit' column, is the
# computed erosional-rate results. Column *offsets* are taken relative to the
# located header cell rather than hard-coded, because the block start differs
# between field workbooks.
EROSIONAL_RESULT_FIELDS = {
    "Conduit": "well_name",
    "Block": "block",
    "Rsi (scf/b)": "rsi_scfb",
    "Boi": "boi_vv",
    "DH SG": "dh_sg",
    "Casing ID": "casing_id_in",
    "Screen": "screen",
    "Gross Rate (stb/d)": "gross_rate_stbd",
    "Prosper PI": "prosper_pi",
    "Prosper Erosion": "prosper_erosion",
    "DD Press": "dd_press",
    "Vc": "vc",
    "Qmax, Vcm": "q_max_vcm",
    "Vs": "vs",
    "Qmax, Vsm": "q_max_vsm",
    "Qerosion, wellbore": "q_erosion_wellbore",
    "Qerosion,screen": "q_erosion_screen",
    "Qerosion, ann.destab": "q_erosion_ann_destab",
    "Qerosion": "q_erosion",
    "Tubing Material": "material_type",
    "Sand Presence": "sand_presence",
    "Sand Prod. Rate (pptb)": "sand_rate_pptb",
}

# Left-hand fluid-property block. Offsets are relative to the 'FIELD' cell.
EROSIONAL_FLUID_FIELDS = {
    "BLOCK": "block",
    "Press psia": "reservoir_press_psia",
    "PB psia": "reservoir_pb_psia",
    "RSI scf/b": "rsi_scfb",
    "Boi v/v": "boi_vv",
    "TR deg/f": "tr_deg_f",
    "SG Oil": "sg_oil",
    "Oil CP": "oil_cp",
    "Water CP": "water_cp",
    "GOR scf/b": "gor_scfb",
    "Oil 60/60f": "oil_sg_60",
    "Gas air=1": "gas_sg",
}


def _norm_header(value: Any) -> str:
    return " ".join(str(value).replace("\n", " ").split()).lower().rstrip(":")


def _build_header_index(df: pd.DataFrame, max_rows: int = 8) -> Dict[str, int]:
    """
    Scan the top rows of a header-less sheet and map normalised header text to
    its column index. Later rows win, so the more specific sub-headers on row 3
    override the merged group labels on row 2.
    """
    index: Dict[str, int] = {}
    for r in range(min(max_rows, len(df))):
        for c, value in enumerate(df.iloc[r]):
            text = _norm_header(value)
            if text and text not in ("nan", "none"):
                index[text] = c
    return index


def _build_header_candidates(df: pd.DataFrame, max_rows: int = 8) -> Dict[str, List[int]]:
    """
    Like `_build_header_index`, but keeps *every* column a label appears in.

    The Erosional Rates sheet stacks three independent tables side by side, and
    generic labels such as 'BLOCK' occur in all of them. Callers disambiguate
    by asking for the occurrence nearest their block's anchor column.
    """
    candidates: Dict[str, List[int]] = {}
    for r in range(min(max_rows, len(df))):
        for c, value in enumerate(df.iloc[r]):
            text = _norm_header(value)
            if text and text not in ("nan", "none"):
                cols = candidates.setdefault(text, [])
                if c not in cols:
                    cols.append(c)
    return candidates


def _looks_like_well_name(name: Optional[str]) -> bool:
    """
    True for values that plausibly name a well.

    The sheets interleave header text and section banners with data rows, so
    anything without a digit, or containing whitespace, is treated as chrome
    rather than a well. This keeps banners like 'EROSIONAL RATES' and stray
    header echoes such as 'BLOCK' out of the parsed records.
    """
    if not name:
        return False
    if any(ch.isspace() for ch in name):
        return False
    if not any(ch.isdigit() for ch in name):
        return False
    return len(name) >= 4


def parse_erosional_sheet(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Parse the Erosional Rates sheet into one record per well.

    Reads both header blocks and merges them on well name. Returns an empty
    list rather than raising when the sheet does not match the expected shape.
    """
    if df.empty:
        return []

    candidates = _build_header_candidates(df)

    def col_for(label: str, lo: int = 0, hi: int = 10_000) -> Optional[int]:
        """Column for `label`, restricted to the [lo, hi) window."""
        cols = [c for c in candidates.get(_norm_header(label), []) if lo <= c < hi]
        return min(cols) if cols else None

    results_by_well: Dict[str, Dict[str, Any]] = {}

    # --- right-hand results block, keyed off the 'Conduit' column -----------
    conduit_col = col_for("Conduit")
    # The results block ends where the next table's 'FIELD' banner begins.
    trailing_field = [c for c in candidates.get("field", []) if conduit_col is not None and c > conduit_col]
    results_end = min(trailing_field) if trailing_field else 10_000

    if conduit_col is not None:
        field_cols = {
            target: col_for(label, conduit_col, results_end)
            for label, target in EROSIONAL_RESULT_FIELDS.items()
            if label != "Conduit"
        }
        for r in range(len(df)):
            name = safe_text(df.iat[r, conduit_col]) if conduit_col < df.shape[1] else None
            if not _looks_like_well_name(name):
                continue
            record = results_by_well.setdefault(name, {"well_name": name})
            for target, c in field_cols.items():
                if c is None or c >= df.shape[1]:
                    continue
                record.setdefault(target, df.iat[r, c])

    # --- left-hand fluid property block, keyed off the 'FIELD' column -------
    # Bounded above by the results block so the two cannot borrow each other's
    # columns for shared labels like 'BLOCK' or 'Boi'.
    field_col = col_for("FIELD", 0, conduit_col if conduit_col is not None else 10_000)
    if field_col is not None:
        fluid_end = conduit_col if conduit_col is not None else 10_000
        fluid_cols = {
            target: col_for(label, field_col, fluid_end)
            for label, target in EROSIONAL_FLUID_FIELDS.items()
        }
        for r in range(len(df)):
            name = safe_text(df.iat[r, field_col]) if field_col < df.shape[1] else None
            if not _looks_like_well_name(name):
                continue
            record = results_by_well.setdefault(name, {"well_name": name})
            for target, c in fluid_cols.items():
                if c is None or c >= df.shape[1]:
                    continue
                value = df.iat[r, c]
                if record.get(target) is None and safe_text(value) is not None:
                    record[target] = value

    return [r for r in results_by_well.values() if r.get("well_name")]


# ---------------------------------------------------------------------------
# Envelope Data sheet
# ---------------------------------------------------------------------------

def parse_envelope_sheet(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Parse the pre-computed operating envelope from the 'Envelope Data' sheet.

    The sheet is a chart-feeder table: columns Gross / THP curve / FLP /
    Critical Flow describe the envelope of the well currently selected in the
    workbook, whose name sits in the top-left cell.

    Returns {"well_name": str|None, "points": [{gross, thp, flp, critical_flow}]}.
    """
    if df.empty:
        return {"well_name": None, "points": []}

    well_name = safe_text(df.iat[0, 0]) if df.shape[1] else None

    # Locate the envelope header row by its distinctive 'THP curve' label, then
    # take every other column from that same row. Scanning columns globally
    # would latch onto the unrelated 'Gross' label that heads the per-well rate
    # ladder further right on the same sheet.
    header_row = thp_col = None
    for r in range(min(12, len(df))):
        for c in range(df.shape[1]):
            if _norm_header(df.iat[r, c]) == "thp curve":
                header_row, thp_col = r, c
                break
        if header_row is not None:
            break

    if header_row is None:
        return {"well_name": well_name, "points": []}

    row_labels = {_norm_header(df.iat[header_row, c]): c for c in range(df.shape[1])}
    gross_col = row_labels.get("gross")
    flp_col = row_labels.get("flp")
    crit_col = row_labels.get("critical flow")

    if gross_col is None:
        return {"well_name": well_name, "points": []}

    points = []
    for r in range(header_row + 1, len(df)):
        gross = safe_float(df.iat[r, gross_col]) if gross_col < df.shape[1] else None
        thp = safe_float(df.iat[r, thp_col]) if thp_col < df.shape[1] else None
        if gross is None or thp is None:
            continue

        flp = safe_float(df.iat[r, flp_col]) if flp_col is not None and flp_col < df.shape[1] else None
        critical = safe_float(df.iat[r, crit_col]) if crit_col is not None and crit_col < df.shape[1] else None

        # The sheet interleaves the envelope curve with single-point scatter
        # markers for the latest test. Genuine curve rows always carry a
        # positive flowline pressure; the markers leave it blank or zero.
        if not flp or flp <= 0:
            continue

        points.append({
            "gross": gross,
            "thp": thp,
            "flp": flp,
            "critical_flow": critical if critical is not None else flp * 1.7,
        })

    points.sort(key=lambda p: p["gross"])
    return {"well_name": well_name, "points": points}


def parse_bean_model_assignments(df: pd.DataFrame) -> Dict[str, str]:
    """
    Read per-well bean-model assignments from the 'Well Operating Envelope'
    sheet. The sheet shows the model for the currently selected well next to a
    'Bean' label; the available models are listed in the top-left column.
    """
    if df.empty:
        return {}

    # The models offered by the workbook are listed down the first column,
    # under a 'Bean Model' heading. Use them to validate what we read back, so
    # that an unrelated 'Bean' column header elsewhere on the sheet cannot be
    # mistaken for a model assignment.
    known_models = set()
    for r in range(min(12, len(df))):
        text = safe_text(df.iat[r, 0]) if df.shape[1] else None
        if text and _norm_header(text) not in ("bean model", "latest", "nan"):
            if not any(ch.isdigit() for ch in text):
                known_models.add(text)

    assignments: Dict[str, str] = {}
    for r in range(min(12, len(df))):
        labels = {_norm_header(df.iat[r, c]): c for c in range(min(df.shape[1], 30))}
        well_col, bean_col = labels.get("well"), labels.get("bean")
        if well_col is None or bean_col is None:
            continue
        well_name = safe_text(df.iat[r, well_col + 1]) if well_col + 1 < df.shape[1] else None
        model = safe_text(df.iat[r, bean_col + 1]) if bean_col + 1 < df.shape[1] else None
        if well_name and model and model in known_models:
            assignments[well_name] = model
    return assignments
