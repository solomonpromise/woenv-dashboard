from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class BeanCalculation(Base):
    __tablename__ = "bean_calculations"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"), nullable=False)
    bean_model = Column(String(20))
    bean_size = Column(Float)
    qo_calculated = Column(Float)
    qg_calculated = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    well = relationship("Well", back_populates="bean_calculations")
