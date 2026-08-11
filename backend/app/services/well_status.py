"""
Normalisation of the free-text well status vocabulary found in the source
workbooks.

The raw data contains at least nine distinct spellings of four real states
(CLOSED / Closed-in / SHUT IN / CLOSED_LT, FLOWING / Flowing / OPEN, ...),
plus junk values that are actually well-name fragments. Filtering on the raw
strings silently under-counts, which is why the dashboard reported zero closed
wells against forty-five CLOSED ones.
"""

from typing import Optional

FLOWING = "Flowing"
CLOSED = "Closed-in"
SUSPENDED = "Suspended"
UNKNOWN = "Unknown"

ALL_STATUSES = [FLOWING, CLOSED, SUSPENDED, UNKNOWN]

_STATUS_MAP = {
    "FLOWING": FLOWING,
    "OPEN": FLOWING,
    "PRODUCING": FLOWING,
    "ON": FLOWING,
    "CLOSED": CLOSED,
    "CLOSED-IN": CLOSED,
    "CLOSED IN": CLOSED,
    "CLOSEDIN": CLOSED,
    "CLOSED_LT": CLOSED,
    "SHUT IN": CLOSED,
    "SHUT-IN": CLOSED,
    "SHUTIN": CLOSED,
    "SI": CLOSED,
    "OFF": CLOSED,
    "SUSPENDED": SUSPENDED,
    "ABANDONED": SUSPENDED,
    "P&A": SUSPENDED,
}


def normalize_status(raw: Optional[object]) -> str:
    """
    Map a raw status value onto the canonical vocabulary.

    Anything unrecognised - including well-name fragments such as "036L" that
    leak in from misaligned spreadsheet rows - becomes "Unknown" rather than
    being trusted as a status.
    """
    if raw is None:
        return UNKNOWN
    text = str(raw).strip()
    if not text or text.lower() in ("nan", "none", "null"):
        return UNKNOWN

    key = text.upper().replace("_", " ").strip()
    if key in _STATUS_MAP:
        return _STATUS_MAP[key]

    collapsed = key.replace(" ", "").replace("-", "")
    for candidate, value in _STATUS_MAP.items():
        if candidate.replace(" ", "").replace("-", "").replace("_", "") == collapsed:
            return value

    return UNKNOWN


PRODUCTION_METHODS = {
    "NATURAL FLOW": "Natural Flow",
    "NATURAL": "Natural Flow",
    "NF": "Natural Flow",
    "GAS LIFT": "Gas Lift",
    "GASLIFT": "Gas Lift",
    "GL": "Gas Lift",
    "ESP": "ESP",
    "SUBMERSIBLE": "ESP",
}


def normalize_production_method(raw: Optional[object]) -> Optional[str]:
    """Map the workbook Prod_Method column onto a canonical vocabulary."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("nan", "none", "null"):
        return None
    return PRODUCTION_METHODS.get(text.upper(), text)
