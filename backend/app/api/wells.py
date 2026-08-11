from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.well import Well
from app.models.test_data import TestData
from app.schemas.well import WellCreate, WellResponse
from app.schemas.test_data import TestDataResponse
from app.api.dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/wells", tags=["wells"])


@router.get("/", response_model=List[WellResponse])
def get_wells(
    field_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    query = db.query(Well)
    if field_id:
        query = query.filter(Well.field_id == field_id)
    if status:
        query = query.filter(Well.status == status)
    wells = query.offset(skip).limit(limit).all()
    return wells


@router.get("/{well_id}", response_model=WellResponse)
def get_well(
    well_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    return well


@router.get("/{well_id}/history", response_model=List[TestDataResponse])
def get_well_history(
    well_id: int,
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    test_data = (
        db.query(TestData)
        .filter(TestData.well_id == well_id)
        .order_by(TestData.test_start.desc())
        .limit(limit)
        .all()
    )
    return test_data


@router.post("/", response_model=WellResponse)
def create_well(
    well_data: WellCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "engineer"]))
):
    existing = db.query(Well).filter(
        Well.field_id == well_data.field_id,
        Well.name == well_data.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Well already exists in this field")
    well = Well(**well_data.model_dump())
    db.add(well)
    db.commit()
    db.refresh(well)
    return well


@router.put("/{well_id}", response_model=WellResponse)
def update_well(
    well_id: int,
    well_data: WellCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin", "engineer"]))
):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    for key, value in well_data.model_dump(exclude_unset=True).items():
        setattr(well, key, value)
    db.commit()
    db.refresh(well)
    return well


@router.delete("/{well_id}")
def delete_well(
    well_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    well = db.query(Well).filter(Well.id == well_id).first()
    if not well:
        raise HTTPException(status_code=404, detail="Well not found")
    db.delete(well)
    db.commit()
    return {"message": "Well deleted successfully"}
