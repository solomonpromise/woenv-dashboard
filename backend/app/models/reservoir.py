from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Reservoir(Base):
    __tablename__ = "reservoirs"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    block = Column(String(50), nullable=False)
    pressure_psia = Column(Float)
    oil_sg = Column(Float)
    gas_sg = Column(Float)
    bubble_point = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    field = relationship("Field", back_populates="reservoirs")
    wells = relationship("Well", back_populates="reservoir")
