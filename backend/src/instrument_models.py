from sqlalchemy import String,Float,Integer,ForeignKey,JSON,UniqueConstraint,CheckConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class Densitometer(Base):
    __tablename__='densitometers'
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True)
    kind:Mapped[str]=mapped_column(String(20),default='working')
    state:Mapped[str]=mapped_column(String(20),default='disabled')
    note:Mapped[str]=mapped_column(String(200),default='')
class Calibration(Base):
    __tablename__='calibrations'
    __table_args__=(UniqueConstraint('meter_id','version'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    meter_id:Mapped[int]=mapped_column(ForeignKey('densitometers.id'))
    version:Mapped[int]=mapped_column(Integer)
    state:Mapped[str]=mapped_column(String(20),default='draft')
    fit:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    acceptance:Mapped[dict|None]=mapped_column(JSON,nullable=True)
    created_at:Mapped[str]=mapped_column(String(40))
    accepted_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    revoked_at:Mapped[str|None]=mapped_column(String(40),nullable=True)
    revoked_by:Mapped[str]=mapped_column(String(100),default='')
    revoke_reason:Mapped[str]=mapped_column(String(300),default='')
class CalibrationSheet(Base):
    __tablename__='calibration_sheets'
    __table_args__=(UniqueConstraint('calibration_id','code'),CheckConstraint('ref_c >= 0 AND ref_m >= 0 AND ref_y >= 0 AND ref_k >= 0 AND ref_gain >= 0 AND new_c >= 0 AND new_m >= 0 AND new_y >= 0 AND new_k >= 0 AND new_gain >= 0'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    calibration_id:Mapped[int]=mapped_column(ForeignKey('calibrations.id'))
    code:Mapped[str]=mapped_column(String(40))
    ref_c:Mapped[float]=mapped_column(Float)
    ref_m:Mapped[float]=mapped_column(Float)
    ref_y:Mapped[float]=mapped_column(Float)
    ref_k:Mapped[float]=mapped_column(Float)
    ref_gain:Mapped[float]=mapped_column(Float)
    new_c:Mapped[float]=mapped_column(Float)
    new_m:Mapped[float]=mapped_column(Float)
    new_y:Mapped[float]=mapped_column(Float)
    new_k:Mapped[float]=mapped_column(Float)
    new_gain:Mapped[float]=mapped_column(Float)
class ProofInstrument(Base):
    __tablename__='proof_instruments'
    id:Mapped[int]=mapped_column(primary_key=True)
    proof_id:Mapped[int]=mapped_column(ForeignKey('proof_sheets.id'),unique=True)
    meter_id:Mapped[int]=mapped_column(ForeignKey('densitometers.id'))
    calibration_id:Mapped[int|None]=mapped_column(ForeignKey('calibrations.id'),nullable=True)
    pinned_at:Mapped[str]=mapped_column(String(40))
