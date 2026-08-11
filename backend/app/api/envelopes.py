from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_role
from app.core.database import get_db
from app.models.envelope_data import EnvelopeData
from app.schemas.envelope import EnvelopeResponse
from app.services.envelope_computation import (compute_well_envelope,
                                               store_envelope_snapshot)

router = APIRouter(prefix="/envelopes", tags=["envelopes"])


@router.get("/", response_model=List[EnvelopeResponse])
def get_envelopes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    return (db.query(EnvelopeData)
            .order_by(EnvelopeData.well_id, EnvelopeData.gross_rate)
            .offset(skip).limit(limit).all())


@router.get("/{well_id}", response_model=Dict[str, Any])
def get_well_envelope(
    well_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Operating envelope for a well.

    Read-only: computing an envelope no longer writes to the database, so this
    can safely be called on every page view.
    """
    try:
        return compute_well_envelope(db, well_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/compute/{well_id}", response_model=Dict[str, Any])
def trigger_envelope_computation(
    well_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_role(["admin", "engineer"])),
):
    """
    Recompute a well's envelope and persist the modelled curve.

    Runs synchronously - the computation is a handful of queries and closed-form
    correlations, so dispatching it to Celery only added a broker dependency and
    a task id the UI had no way to resolve.
    """
    try:
        return store_envelope_snapshot(db, well_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
