from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class TestDataBase(BaseModel):
    test_start: datetime
    duration_hours: Optional[int] = 24
    status: Optional[str] = None
    result_status: Optional[str] = None
    fthp_psig: Optional[float] = None
    choke_size: Optional[float] = None
    gross_rate_stbd: Optional[float] = None
    oil_rate_stbd: Optional[float] = None
    water_rate_stbd: Optional[float] = None
    gas_rate_mscfd: Optional[float] = None
    gas_lift_rate_mscfd: Optional[float] = None
    bsw_percent: Optional[float] = None
    sand_pptb: Optional[float] = None
    fgor_scfstb: Optional[float] = None
    glr_scfstb: Optional[float] = None
    sep_pressure: Optional[float] = None
    sep_temp: Optional[float] = None


class TestDataCreate(TestDataBase):
    well_id: int


class TestDataResponse(TestDataBase):
    id: int
    well_id: int
    created_at: datetime

    class Config:
        from_attributes = True
