from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TestData(Base):
    __tablename__ = "test_data"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"), nullable=False)
    test_start = Column(DateTime, nullable=False)
    duration_hours = Column(Integer, default=24)
    status = Column(String(20))
    result_status = Column(String(30))
    fthp_psig = Column(Float)
    choke_size = Column(Float)
    gross_rate_stbd = Column(Float)
    oil_rate_stbd = Column(Float)
    water_rate_stbd = Column(Float)
    gas_rate_mscfd = Column(Float)
    gas_lift_rate_mscfd = Column(Float)
    bsw_percent = Column(Float)
    sand_pptb = Column(Float)
    fgor_scfstb = Column(Float)
    glr_scfstb = Column(Float)
    sep_pressure = Column(Float)
    sep_temp = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    well = relationship("Well", back_populates="test_data")
