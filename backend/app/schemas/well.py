from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class WellBase(BaseModel):
    name: str
    well_type: Optional[str] = None
    status: Optional[str] = None
    bean_model: Optional[str] = None
    completion_details: Optional[Dict[str, Any]] = None


class WellCreate(WellBase):
    field_id: int
    reservoir_id: Optional[int] = None


class WellResponse(WellBase):
    id: int
    field_id: int
    reservoir_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
