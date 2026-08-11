from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, String, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ErosionalRate(Base):
    """
    Per-well erosional-rate limits and fluid properties, sourced from the
    'Erosional Rates' sheet of the field workbooks.

    The sheet carries two header blocks: a fluid-property summary and a block
    of Prosper-computed erosion results. Both are captured here.
    """

    __tablename__ = "erosional_rates"

    id = Column(Integer, primary_key=True, index=True)
    well_id = Column(Integer, ForeignKey("wells.id"), nullable=False)
    block = Column(String(50))

    # --- reservoir / fluid properties --------------------------------------
    reservoir_press_psia = Column(Float)
    reservoir_pb_psia = Column(Float)   # bubble point
    rsi_scfb = Column(Float)            # solution GOR at initial conditions
    boi_vv = Column(Float)              # oil formation volume factor
    tr_deg_f = Column(Float)            # reservoir temperature
    sg_oil = Column(Float)              # oil specific gravity at reservoir
    oil_cp = Column(Float)
    water_cp = Column(Float)
    gor_scfb = Column(Float)            # surface GOR
    oil_sg_60 = Column(Float)           # oil SG at 60/60 F
    gas_sg = Column(Float)              # gas gravity, air = 1

    # --- completion --------------------------------------------------------
    casing_id_in = Column(Float)
    screen = Column(String(50))

    # --- computed erosion results ------------------------------------------
    c_factor = Column(Float)
    vc = Column(Float)                  # critical velocity
    vs = Column(Float)
    q_max_vcm = Column(Float)
    q_max_vsm = Column(Float)
    dd_press = Column(Float)            # drawdown pressure
    prosper_pi = Column(Float)
    prosper_erosion = Column(Float)
    gross_rate_stbd = Column(Float)
    q_erosion_wellbore = Column(Float)
    q_erosion_screen = Column(Float)
    q_erosion_ann_destab = Column(Float)
    q_erosion = Column(Float)           # governing erosional rate limit, stb/d

    # --- material / sand ---------------------------------------------------
    material_type = Column(String(50))
    sand_presence = Column(Boolean)
    sand_rate_pptb = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    well = relationship("Well", back_populates="erosional_rates")
