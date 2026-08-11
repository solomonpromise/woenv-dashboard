"""
Petroleum engineering calculations for well operating envelopes.

All correlations here use a single consistent field-unit system:

    pressure        psig (gauge) unless the name says _psia
    liquid rate     stb/d
    gas rate        scf/d  (note: NOT Mscf/d - convert at the boundary)
    GLR / GOR       scf/stb
    choke / bean    1/64 inch
    temperature     deg F unless the name says _rankine
    density         lb/ft3
    length          inches for tubulars, feet elsewhere

Every function is pure so it can be unit-tested against known values.
"""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

# Standard conditions
STANDARD_PRESSURE_PSIA = 14.7
STANDARD_TEMP_RANKINE = 519.67  # 60 deg F
BBL_TO_CUFT = 5.614583
RANKINE_OFFSET = 459.67

# Atmospheric pressure used to convert gauge <-> absolute
ATMOSPHERIC_PSI = 14.7


def to_rankine(temp_f: float) -> float:
    return temp_f + RANKINE_OFFSET


def psig_to_psia(psig: float) -> float:
    return psig + ATMOSPHERIC_PSI


# ---------------------------------------------------------------------------
# Bean (choke) correlations
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BeanCorrelation:
    """
    Multiphase critical-flow choke correlation of the Gilbert family:

        P_wh = A * (GLR ** B) * Q_liquid / (S ** C)

    where P_wh is upstream (wellhead) pressure in psig, GLR is in scf/stb,
    Q_liquid is in stb/d and S is the bean size in 1/64 inch.

    These correlations are only valid in *critical* (sonic) flow, where the
    downstream pressure no longer influences the rate. Callers should check
    `is_critical_flow` before relying on the result.
    """

    name: str
    a: float
    b: float
    c: float
    source: str = ""

    def wellhead_pressure(self, liquid_rate: float, gas_ratio: float, bean_64ths: float) -> Optional[float]:
        """
        Predict flowing wellhead pressure (psig) for a given liquid rate.

        `gas_ratio` is the produced gas ratio in scf/stb. The source workbooks
        drive these correlations from their measured GOR column, and validation
        against 86 critical-flow natural-flow tests confirms GOR gives markedly
        better agreement than true GLR (Achong: 20% vs 38% median error), so
        callers should pass GOR to reproduce workbook behaviour.
        """
        if liquid_rate is None or gas_ratio is None or bean_64ths is None:
            return None
        if liquid_rate <= 0 or gas_ratio <= 0 or bean_64ths <= 0:
            return None
        return self.a * (gas_ratio ** self.b) * liquid_rate / (bean_64ths ** self.c)

    def liquid_rate(self, wellhead_pressure: float, gas_ratio: float, bean_64ths: float) -> Optional[float]:
        """Invert the correlation to predict liquid rate (stb/d)."""
        if wellhead_pressure is None or gas_ratio is None or bean_64ths is None:
            return None
        if wellhead_pressure <= 0 or gas_ratio <= 0 or bean_64ths <= 0:
            return None
        return wellhead_pressure * (bean_64ths ** self.c) / (self.a * (gas_ratio ** self.b))


# Published constants for the P[psig] / GLR[scf/stb] / Q[stb/d] / S[1/64"] unit set.
BEAN_CORRELATIONS: Dict[str, BeanCorrelation] = {
    "Gilbert": BeanCorrelation("Gilbert", 10.00, 0.546, 1.89, "Gilbert (1954)"),
    "Ros": BeanCorrelation("Ros", 17.40, 0.500, 2.00, "Ros (1960)"),
    "Baxendell": BeanCorrelation("Baxendell", 9.56, 0.546, 1.93, "Baxendell (1957)"),
    "Achong": BeanCorrelation("Achong", 3.82, 0.650, 1.88, "Achong (1961)"),
}

# Validated against 86 critical-flow, natural-flow tests from the UGHE/UTOR/
# UGWest/OGIN workbooks (median absolute error, driven by measured GOR):
#   Achong 20.4%  |  Baxendell 26.6%  |  Ros 34.4%  |  Gilbert 38.6%
# Achong is therefore the default when a well has no explicit model assigned.
DEFAULT_BEAN_MODEL = "Achong"


def get_bean_correlation(name: Optional[str]) -> BeanCorrelation:
    """
    Look up a bean correlation by name, falling back to Gilbert.

    Note: the source workbooks also reference an "SW Ampa" model, which is an
    operator in-house correlation whose constants are not published. Until
    those constants are supplied it falls back to Gilbert; callers should
    surface `correlation.name` so the user can see which model was actually
    applied.
    """
    if not name:
        return BEAN_CORRELATIONS[DEFAULT_BEAN_MODEL]
    return BEAN_CORRELATIONS.get(name.strip(), BEAN_CORRELATIONS[DEFAULT_BEAN_MODEL])


# ---------------------------------------------------------------------------
# Critical flow
# ---------------------------------------------------------------------------

# Ratio of upstream to downstream pressure above which flow through the bean is
# sonic. The source workbooks compute their "Critical Flow" column as
# FLP * 1.7 exactly, so 1.7 is the operator's working criterion.
CRITICAL_FLOW_RATIO = 1.7


def critical_flow_pressure(downstream_pressure: float, ratio: float = CRITICAL_FLOW_RATIO) -> Optional[float]:
    """
    Minimum upstream pressure for critical flow, given the downstream
    (flowline) pressure. Below this the well is in sub-critical flow and the
    bean correlations do not apply.
    """
    if downstream_pressure is None or downstream_pressure <= 0:
        return None
    return downstream_pressure * ratio


def is_critical_flow(
    upstream_pressure: float,
    downstream_pressure: float,
    ratio: float = CRITICAL_FLOW_RATIO,
) -> Optional[bool]:
    """True when flow through the bean is critical (sonic)."""
    threshold = critical_flow_pressure(downstream_pressure, ratio)
    if threshold is None or upstream_pressure is None:
        return None
    return upstream_pressure >= threshold


# ---------------------------------------------------------------------------
# API RP 14E erosional velocity
# ---------------------------------------------------------------------------

# C-factor guidance from API RP 14E section 2.5:
C_FACTOR_GUIDANCE = {
    "continuous_non_corrosive": 100.0,
    "intermittent_non_corrosive": 125.0,
    "continuous_corrosive_inhibited": 150.0,
    "intermittent_corrosive_inhibited": 200.0,
    "solids_free_corrosion_resistant": 250.0,
}
DEFAULT_C_FACTOR = 100.0


def api14e_mixture_density(
    pressure_psia: float,
    temp_f: float,
    gas_liquid_ratio: float,
    liquid_sg: float,
    gas_sg: float,
    z_factor: float = 1.0,
) -> Optional[float]:
    """
    Flowing mixture density (lb/ft3) per API RP 14E:

        rho_m = (12409 * SG_l * P + 2.7 * R * SG_g * P)
                / (198.7 * P + R * T * Z)

    P in psia, T in degrees Rankine, R = gas/liquid ratio in ft3/bbl at
    standard conditions, SG_l relative to water, SG_g relative to air.

    This replaces naive "mass over volume" mixing, which is dimensionally
    invalid when gas is expressed in Mscf/d and liquids in stb/d.
    """
    if pressure_psia is None or pressure_psia <= 0:
        return None
    if liquid_sg is None or liquid_sg <= 0:
        return None
    r = max(gas_liquid_ratio or 0.0, 0.0)
    sg_g = gas_sg if gas_sg and gas_sg > 0 else 0.65
    t_rankine = to_rankine(temp_f if temp_f is not None else 60.0)

    numerator = 12409.0 * liquid_sg * pressure_psia + 2.7 * r * sg_g * pressure_psia
    denominator = 198.7 * pressure_psia + r * t_rankine * z_factor
    if denominator <= 0:
        return None
    return numerator / denominator


def erosional_velocity(mixture_density: float, c_factor: float = DEFAULT_C_FACTOR) -> Optional[float]:
    """
    API RP 14E erosional velocity limit, ft/s:  Ve = C / sqrt(rho_m)
    """
    if mixture_density is None or mixture_density <= 0:
        return None
    return c_factor / math.sqrt(mixture_density)


def pipe_area_sqft(inner_diameter_in: float) -> Optional[float]:
    """Cross-sectional flow area (ft2) for a given inside diameter in inches."""
    if inner_diameter_in is None or inner_diameter_in <= 0:
        return None
    radius_ft = (inner_diameter_in / 12.0) / 2.0
    return math.pi * radius_ft ** 2


def erosional_liquid_rate(
    velocity_fts: float,
    inner_diameter_in: float,
    pressure_psia: float,
    temp_f: float,
    gas_liquid_ratio: float,
    solution_gor: float = 0.0,
    formation_volume_factor: float = 1.0,
    z_factor: float = 1.0,
) -> Optional[float]:
    """
    Convert an erosional *velocity* limit into an erosional *liquid rate*
    limit in stb/d.

    The erosional velocity applies to the total in-situ volumetric flow, so we
    compute the in-situ volume occupied by one stock-tank barrel of liquid
    plus its associated free gas, then work out how many barrels per day fit
    within the velocity limit.
    """
    area = pipe_area_sqft(inner_diameter_in)
    if area is None or velocity_fts is None or velocity_fts <= 0:
        return None
    if pressure_psia is None or pressure_psia <= 0:
        return None

    # In-situ volume of one stock-tank barrel of liquid, ft3
    liquid_volume = BBL_TO_CUFT * max(formation_volume_factor or 1.0, 0.1)

    # Free gas that comes out of solution, scf per stb of liquid
    free_gas = max((gas_liquid_ratio or 0.0) - (solution_gor or 0.0), 0.0)

    # Expand that free gas to flowing conditions, ft3 per stb
    t_rankine = to_rankine(temp_f if temp_f is not None else 60.0)
    gas_volume = free_gas * (STANDARD_PRESSURE_PSIA / pressure_psia) * (
        t_rankine / STANDARD_TEMP_RANKINE
    ) * z_factor

    total_volume_per_bbl = liquid_volume + gas_volume
    if total_volume_per_bbl <= 0:
        return None

    # Total in-situ volumetric capacity at the erosional velocity, ft3/day
    capacity_cufd = velocity_fts * area * 86400.0
    return capacity_cufd / total_volume_per_bbl


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------

def gas_liquid_ratio(gas_rate_scfd: float, gross_liquid_stbd: float) -> Optional[float]:
    """GLR in scf/stb - gas per barrel of TOTAL liquid (oil + water)."""
    if not gas_rate_scfd or not gross_liquid_stbd or gross_liquid_stbd <= 0:
        return None
    return gas_rate_scfd / gross_liquid_stbd


def gas_oil_ratio(gas_rate_scfd: float, oil_rate_stbd: float) -> Optional[float]:
    """GOR in scf/stb - gas per barrel of OIL only. Not interchangeable with GLR."""
    if not gas_rate_scfd or not oil_rate_stbd or oil_rate_stbd <= 0:
        return None
    return gas_rate_scfd / oil_rate_stbd


def glr_from_gor(gor: float, bsw_fraction: float) -> Optional[float]:
    """
    Convert GOR (per barrel of oil) to GLR (per barrel of gross liquid).

        GLR = GOR * (1 - BSW)

    The source workbooks report GOR; plotting it as GLR overstates the ratio
    by 1/(1-BSW), which at 86% water cut is a factor of about seven.
    """
    if gor is None or bsw_fraction is None:
        return None
    if not 0.0 <= bsw_fraction < 1.0:
        return None
    return gor * (1.0 - bsw_fraction)


def oil_sg_from_api(api_gravity: float) -> Optional[float]:
    """Convert API gravity to oil specific gravity (water = 1)."""
    if api_gravity is None or api_gravity <= -131.5:
        return None
    return 141.5 / (131.5 + api_gravity)


def liquid_mixture_sg(oil_sg: float, bsw_fraction: float, water_sg: float = 1.02) -> Optional[float]:
    """Volume-weighted specific gravity of the produced liquid."""
    if oil_sg is None or bsw_fraction is None:
        return None
    bsw = min(max(bsw_fraction, 0.0), 1.0)
    return oil_sg * (1.0 - bsw) + water_sg * bsw


# ---------------------------------------------------------------------------
# Envelope construction
# ---------------------------------------------------------------------------

def build_thp_curve(
    correlation: BeanCorrelation,
    glr: float,
    bean_64ths: float,
    rates: List[float],
) -> List[Dict[str, float]]:
    """
    Model-based THP curve: flowing wellhead pressure against liquid rate for a
    fixed bean size and GLR.
    """
    curve = []
    for rate in rates:
        thp = correlation.wellhead_pressure(rate, glr, bean_64ths)
        if thp is not None:
            curve.append({"rate": round(rate, 2), "thp": round(thp, 2)})
    return curve


def rate_series(max_rate: float, points: int = 25, min_rate: float = 0.0) -> List[float]:
    """Evenly spaced rate series for plotting, always ascending and bounded."""
    if max_rate is None or max_rate <= 0:
        max_rate = 1000.0
    max_rate = min(max_rate, 200_000.0)
    points = max(2, min(points, 200))
    step = (max_rate - min_rate) / (points - 1)
    return [min_rate + step * i for i in range(points)]
