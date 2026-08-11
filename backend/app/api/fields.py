from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.models.field import Field
from app.schemas.field import FieldCreate, FieldResponse
from app.api.dependencies import get_current_active_user, require_role

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("/", response_model=List[FieldResponse])
def get_fields(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    fields = db.query(Field).offset(skip).limit(limit).all()
    return fields


@router.get("/{field_id}", response_model=FieldResponse)
def get_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


@router.post("/", response_model=FieldResponse)
def create_field(
    field_data: FieldCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    existing = db.query(Field).filter(
        (Field.name == field_data.name) | (Field.code == field_data.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Field already exists")
    field = Field(**field_data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.put("/{field_id}", response_model=FieldResponse)
def update_field(
    field_id: int,
    field_data: FieldCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    for key, value in field_data.model_dump(exclude_unset=True).items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field


@router.delete("/{field_id}")
def delete_field(
    field_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role(["admin"]))
):
    field = db.query(Field).filter(Field.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()
    return {"message": "Field deleted successfully"}
