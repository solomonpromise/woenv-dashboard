"""
Aggregate statistics for the dashboard landing page.

Computed in SQL rather than by shipping every well to the browser, so the
overview stays correct and cheap as the dataset grows.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.erosional_rate import ErosionalRate
from app.models.field import Field
from app.models.test_data import TestData
from app.models.well import Well
from app.services.well_status import CLOSED, FLOWING

router = APIRouter(prefix="/stats", tags=["stats"])


def _latest_test_subquery(db: Session):
    """Most recent test date per well."""
    return (db.query(TestData.well_id.label("well_id"),
                     func.max(TestData.test_start).label("latest"))
            .group_by(TestData.well_id)
            .subquery())


@router.get("/overview", response_model=Dict[str, Any])
def overview(
    field_id: Optional[int] = Query(None, description="Restrict to a single field"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Headline counts and production totals, optionally scoped to one field."""
    wells_query = db.query(
        func.count(Well.id),
        func.sum(case((Well.status == FLOWING, 1), else_=0)),
        func.sum(case((Well.status == CLOSED, 1), else_=0)),
    )
    if field_id:
        wells_query = wells_query.filter(Well.field_id == field_id)
    total_wells, flowing, closed = wells_query.one()

    # Production is summed over each well's most recent test only, so a well
    # tested ten times does not count ten times toward field production.
    latest = _latest_test_subquery(db)
    latest_tests = (db.query(TestData)
                    .join(latest,
                          (TestData.well_id == latest.c.well_id) &
                          (TestData.test_start == latest.c.latest))
                    .join(Well, Well.id == TestData.well_id))
    if field_id:
        latest_tests = latest_tests.filter(Well.field_id == field_id)

    totals = latest_tests.with_entities(
        func.sum(TestData.gross_rate_stbd),
        func.sum(TestData.oil_rate_stbd),
        func.sum(TestData.water_rate_stbd),
        func.sum(TestData.gas_rate_mscfd),
        func.avg(TestData.bsw_percent),
        func.count(TestData.id),
    ).one()

    gross, oil, water, gas, avg_bsw, tested_wells = totals

    return {
        "total_wells": total_wells or 0,
        "flowing_wells": flowing or 0,
        "closed_wells": closed or 0,
        "tested_wells": tested_wells or 0,
        "gross_rate_stbd": float(gross) if gross else 0.0,
        "oil_rate_stbd": float(oil) if oil else 0.0,
        "water_rate_stbd": float(water) if water else 0.0,
        "gas_rate_mscfd": float(gas) if gas else 0.0,
        "avg_bsw_percent": float(avg_bsw) if avg_bsw is not None else None,
    }


@router.get("/fields", response_model=List[Dict[str, Any]])
def field_breakdown(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """Per-field well counts and latest-test production, for the overview table."""
    latest = _latest_test_subquery(db)

    counts = dict(
        (row[0], {"total": row[1], "flowing": row[2], "closed": row[3]})
        for row in db.query(
            Well.field_id,
            func.count(Well.id),
            func.sum(case((Well.status == FLOWING, 1), else_=0)),
            func.sum(case((Well.status == CLOSED, 1), else_=0)),
        ).group_by(Well.field_id).all()
    )

    production = dict(
        (row[0], {"gross": row[1], "oil": row[2], "bsw": row[3]})
        for row in db.query(
            Well.field_id,
            func.sum(TestData.gross_rate_stbd),
            func.sum(TestData.oil_rate_stbd),
            func.avg(TestData.bsw_percent),
        )
        .join(TestData, TestData.well_id == Well.id)
        .join(latest,
              (TestData.well_id == latest.c.well_id) &
              (TestData.test_start == latest.c.latest))
        .group_by(Well.field_id).all()
    )

    result = []
    for field in db.query(Field).order_by(Field.name).all():
        c = counts.get(field.id, {})
        p = production.get(field.id, {})
        result.append({
            "field_id": field.id,
            "name": field.name,
            "code": field.code,
            "total_wells": c.get("total", 0) or 0,
            "flowing_wells": c.get("flowing", 0) or 0,
            "closed_wells": c.get("closed", 0) or 0,
            "gross_rate_stbd": float(p["gross"]) if p.get("gross") else 0.0,
            "oil_rate_stbd": float(p["oil"]) if p.get("oil") else 0.0,
            "avg_bsw_percent": float(p["bsw"]) if p.get("bsw") is not None else None,
        })
    return result


@router.get("/envelope-alerts", response_model=List[Dict[str, Any]])
def envelope_alerts(
    field_id: Optional[int] = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Wells whose most recent test breaches an envelope bound.

    Two conditions are reported: production above the erosional rate limit, and
    sub-critical flow across the bean (FTHP below 1.7x separator pressure).
    """
    latest = _latest_test_subquery(db)
    rows = (db.query(Well, TestData, ErosionalRate)
            .join(TestData, TestData.well_id == Well.id)
            .join(latest,
                  (TestData.well_id == latest.c.well_id) &
                  (TestData.test_start == latest.c.latest))
            .outerjoin(ErosionalRate, ErosionalRate.well_id == Well.id))
    if field_id:
        rows = rows.filter(Well.field_id == field_id)

    alerts = []
    for well, test, erosional in rows.all():
        reasons = []
        limit_value = erosional.q_erosion if erosional else None
        utilisation = None

        if limit_value and test.gross_rate_stbd:
            utilisation = test.gross_rate_stbd / limit_value
            if test.gross_rate_stbd > limit_value:
                reasons.append("above_erosional_limit")

        if test.fthp_psig and test.sep_pressure:
            if test.fthp_psig < test.sep_pressure * 1.7:
                reasons.append("sub_critical_flow")

        if not reasons:
            continue

        alerts.append({
            "well_id": well.id,
            "well_name": well.name,
            "field_id": well.field_id,
            "status": well.status,
            "test_start": test.test_start.isoformat() if test.test_start else None,
            "gross_rate_stbd": test.gross_rate_stbd,
            "erosional_limit": limit_value,
            "utilisation": utilisation,
            "fthp_psig": test.fthp_psig,
            "sep_pressure": test.sep_pressure,
            "reasons": reasons,
        })

    alerts.sort(key=lambda a: (a["utilisation"] or 0), reverse=True)
    return alerts[:limit]
