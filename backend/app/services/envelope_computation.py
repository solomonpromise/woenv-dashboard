"""
Assembly of a well's operating envelope for the dashboard.

The envelope has three independent bounds:

  * an upper rate limit from erosion (Qerosion, computed in Prosper by the
    asset engineers and carried in the workbook's Erosional Rates sheet, with
    an API RP 14E fallback when that is absent),
  * a minimum tubing head pressure for critical flow through the bean, and
  * a THP-versus-rate curve.

Workbook-supplied envelope points are preferred over modelled ones; the
`thp_curve_source` field tells the caller which was used.
"""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.envelope_data import EnvelopeData
from app.models.erosional_rate import ErosionalRate
from app.models.test_data import TestData
from app.models.well import Well
from app.services import calculations as calc

# Nominal completion when the workbook does not give a casing/tubing ID.
DEFAULT_TUBING_ID_IN = 3.958


def _latest_tests(db: Session, well_id: int, limit: int = 10) -> List[TestData]:
    return (db.query(TestData)
            .filter(TestData.well_id == well_id)
            .order_by(TestData.test_start.desc())
            .limit(limit)
            .all())


def _erosional_limit(
    erosional: Optional[ErosionalRate],
    latest: Optional[TestData],
) -> Dict[str, Any]:
    """
    Governing erosional rate limit in stb/d, with its provenance.

    Prefers the engineer-computed Qerosion from the workbook. Falls back to an
    API RP 14E calculation from the recorded fluid properties.
    """
    if erosional is not None and erosional.q_erosion and erosional.q_erosion < 99999:
        return {
            "rate_limit": erosional.q_erosion,
            "source": "workbook",
            "c_factor": erosional.c_factor,
            "mixture_density": None,
            "velocity": None,
        }

    if latest is None or not latest.fthp_psig:
        return {"rate_limit": None, "source": "unavailable",
                "c_factor": None, "mixture_density": None, "velocity": None}

    oil_sg = (erosional.oil_sg_60 or erosional.sg_oil) if erosional else None
    gas_sg = (erosional.gas_sg if erosional else None) or 0.65
    bsw_fraction = (latest.bsw_percent or 0.0) / 100.0
    liquid_sg = calc.liquid_mixture_sg(oil_sg or 0.85, bsw_fraction)

    pressure_psia = calc.psig_to_psia(latest.fthp_psig)
    temp_f = latest.sep_temp if latest.sep_temp and latest.sep_temp > 32 else 100.0
    glr = latest.glr_scfstb or 0.0
    c_factor = (erosional.c_factor if erosional and erosional.c_factor
                else calc.DEFAULT_C_FACTOR)

    density = calc.api14e_mixture_density(
        pressure_psia=pressure_psia,
        temp_f=temp_f,
        gas_liquid_ratio=glr,
        liquid_sg=liquid_sg,
        gas_sg=gas_sg,
    )
    velocity = calc.erosional_velocity(density, c_factor)
    tubing_id = (erosional.casing_id_in if erosional and erosional.casing_id_in
                 else DEFAULT_TUBING_ID_IN)
    rate_limit = calc.erosional_liquid_rate(
        velocity_fts=velocity,
        inner_diameter_in=tubing_id,
        pressure_psia=pressure_psia,
        temp_f=temp_f,
        gas_liquid_ratio=glr,
        solution_gor=(erosional.rsi_scfb if erosional else 0.0) or 0.0,
        formation_volume_factor=(erosional.boi_vv if erosional else 1.0) or 1.0,
    ) if velocity else None

    return {
        "rate_limit": rate_limit,
        "source": "api_rp_14e",
        "c_factor": c_factor,
        "mixture_density": density,
        "velocity": velocity,
    }


def compute_well_envelope(db: Session, well_id: int) -> Dict[str, Any]:
    """
    Build the full operating-envelope payload for a well.

    This function is read-only: it performs no writes, so the dashboard can
    call it on every page view.
    """
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise ValueError(f"Well {well_id} not found")

    tests = _latest_tests(db, well_id)
    erosional = (db.query(ErosionalRate)
                 .filter(ErosionalRate.well_id == well_id)
                 .first())

    correlation = calc.get_bean_correlation(well.bean_model)
    erosion = _erosional_limit(erosional, tests[0] if tests else None)

    envelope: Dict[str, Any] = {
        "well_id": well.id,
        "well_name": well.name,
        "field_id": well.field_id,
        "status": well.status,
        "bean_model": well.bean_model or correlation.name,
        "bean_model_applied": correlation.name,
        "erosional_rate_limit": erosion["rate_limit"],
        "erosional_limit_source": erosion["source"],
        "erosional_velocity": erosion["velocity"],
        "mixture_density": erosion["mixture_density"],
        "c_factor": erosion["c_factor"],
        "thp_curve": [],
        "thp_curve_source": "unavailable",
        "critical_flow_pressure": None,
        "is_critical_flow": None,
        "predicted_rate": None,
        "latest_test": None,
        "warnings": [],
    }

    if well.bean_model and well.bean_model != correlation.name:
        envelope["warnings"].append(
            f"No published constants for bean model {well.bean_model!r}; "
            f"used {correlation.name} instead."
        )

    if not tests:
        envelope["warnings"].append("No test data available for this well.")
        return envelope

    latest = tests[0]
    envelope["latest_test"] = {
        "date": latest.test_start.isoformat() if latest.test_start else None,
        "fthp": latest.fthp_psig,
        "gross_rate": latest.gross_rate_stbd,
        "oil_rate": latest.oil_rate_stbd,
        "water_rate": latest.water_rate_stbd,
        "bsw_percent": latest.bsw_percent,
        "gor": latest.fgor_scfstb,
        "glr": latest.glr_scfstb,
        "choke_size": latest.choke_size,
        "sep_pressure": latest.sep_pressure,
    }

    # Critical-flow bound
    if latest.sep_pressure:
        threshold = calc.critical_flow_pressure(latest.sep_pressure)
        envelope["critical_flow_pressure"] = threshold
        envelope["is_critical_flow"] = calc.is_critical_flow(
            latest.fthp_psig, latest.sep_pressure) if latest.fthp_psig else None
        if envelope["is_critical_flow"] is False:
            envelope["warnings"].append(
                "Well is in sub-critical flow; bean correlations do not apply.")

    # Prefer the workbook's own envelope curve.
    stored = (db.query(EnvelopeData)
              .filter(EnvelopeData.well_id == well_id,
                      EnvelopeData.source == EnvelopeData.SOURCE_WORKBOOK)
              .order_by(EnvelopeData.gross_rate.asc())
              .all())
    if stored:
        envelope["thp_curve"] = [
            {"rate": p.gross_rate, "thp": p.thp_curve,
             "flp": p.flp, "critical_flow": p.critical_flow}
            for p in stored if p.gross_rate is not None and p.thp_curve is not None
        ]
        envelope["thp_curve_source"] = "workbook"
    else:
        gas_ratio = latest.fgor_scfstb or latest.glr_scfstb
        if gas_ratio and latest.choke_size:
            upper = erosion["rate_limit"] or (latest.gross_rate_stbd or 1000) * 1.5
            rates = calc.rate_series(upper, points=25, min_rate=max(upper * 0.02, 10))
            envelope["thp_curve"] = calc.build_thp_curve(
                correlation, gas_ratio, latest.choke_size, rates)
            envelope["thp_curve_source"] = f"model:{correlation.name}"
        else:
            envelope["warnings"].append(
                "Insufficient data (GOR or choke size) to model a THP curve.")

    # Model-predicted rate at the measured THP, for comparison with the test.
    if latest.fthp_psig and latest.choke_size:
        gas_ratio = latest.fgor_scfstb or latest.glr_scfstb
        envelope["predicted_rate"] = correlation.liquid_rate(
            latest.fthp_psig, gas_ratio, latest.choke_size)

    # Is the well currently operating inside its envelope?
    limit = erosion["rate_limit"]
    if limit and latest.gross_rate_stbd:
        envelope["within_erosional_limit"] = latest.gross_rate_stbd <= limit
        envelope["erosional_utilisation"] = latest.gross_rate_stbd / limit
        if not envelope["within_erosional_limit"]:
            envelope["warnings"].append(
                f"Gross rate {latest.gross_rate_stbd:,.0f} stb/d exceeds the "
                f"erosional limit of {limit:,.0f} stb/d.")

    return envelope


def store_envelope_snapshot(db: Session, well_id: int) -> Dict[str, Any]:
    """
    Compute the envelope and persist the modelled curve.

    Kept separate from `compute_well_envelope` so that reads stay side-effect
    free; only the explicit compute endpoint and the Celery task write.
    """
    envelope = compute_well_envelope(db, well_id)
    if envelope.get("thp_curve_source", "").startswith("model"):
        (db.query(EnvelopeData)
         .filter(EnvelopeData.well_id == well_id,
                 EnvelopeData.source == EnvelopeData.SOURCE_MODEL)
         .delete(synchronize_session=False))
        for point in envelope["thp_curve"]:
            db.add(EnvelopeData(
                well_id=well_id,
                gross_rate=point.get("rate"),
                thp_curve=point.get("thp"),
                critical_flow=envelope.get("critical_flow_pressure"),
                source=EnvelopeData.SOURCE_MODEL,
            ))
        db.commit()
    return envelope
