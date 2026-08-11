from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FieldBase(BaseModel):
    name: str
    code: str
    location: Optional[str] = None


class FieldCreate(FieldBase):
    pass


class FieldResponse(FieldBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
