from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EnvelopeResponse(BaseModel):
    id: int
    well_id: int
    test_data_id: Optional[int] = None
    thp_curve: Optional[float] = None
    flp: Optional[float] = None
    critical_flow: Optional[float] = None
    gross_rate: Optional[float] = None
    computed_at: datetime

    class Config:
        from_attributes = True
