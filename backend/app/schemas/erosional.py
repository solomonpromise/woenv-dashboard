from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ErosionalRateResponse(BaseModel):
    id: int
    well_id: int
    block: Optional[str] = None
    reservoir_pb_psia: Optional[float] = None
    rsi_scfb: Optional[float] = None
    boi_vv: Optional[float] = None
    tr_deg_f: Optional[float] = None
    sg_oil: Optional[float] = None
    c_factor: Optional[float] = None
    q_max_vcm: Optional[float] = None
    q_erosion_wellbore: Optional[float] = None
    q_erosion_screen: Optional[float] = None
    q_erosion: Optional[float] = None
    material_type: Optional[str] = None
    sand_presence: Optional[bool] = None
    created_at: datetime

    class Config:
        from_attributes = True
