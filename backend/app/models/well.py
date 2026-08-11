from sqlalchemy import (Column, Integer, String, Float, ForeignKey, DateTime,
                        JSON, Boolean, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Well(Base):
    __tablename__ = "wells"

    id = Column(Integer, primary_key=True, index=True)
    field_id = Column(Integer, ForeignKey("fields.id"), nullable=False)
    reservoir_id = Column(Integer, ForeignKey("reservoirs.id"))
    name = Column(String(50), nullable=False, index=True)
    well_type = Column(String(20))  # Tubing, Gas Lift, Subsea
    prod_method = Column(String(30))  # Natural Flow, Gas Lift, ESP
    status = Column(String(20))  # Flowing, Closed-in, Suspended, Unknown
    bean_model = Column(String(20))  # Gilbert, Achong, SW Ampa, Ros
    completion_details = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    field = relationship("Field", back_populates="wells")
    reservoir = relationship("Reservoir", back_populates="wells")
    test_data = relationship("TestData", back_populates="well")
    erosional_rates = relationship("ErosionalRate", back_populates="well")
    envelope_data = relationship("EnvelopeData", back_populates="well")
    bean_calculations = relationship("BeanCalculation", back_populates="well")

    # A well name is unique within its field. Without this, repeated uploads
    # could create duplicate wells that silently split a well's test history.
    __table_args__ = (
        UniqueConstraint("field_id", "name", name="uq_wells_field_name"),
    )
