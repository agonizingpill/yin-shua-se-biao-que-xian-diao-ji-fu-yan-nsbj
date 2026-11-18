import os,redis
from fastapi import APIRouter,Depends
from sqlalchemy import select
from .db import db_session
from .auth import current,writers,admin
from .services import pack
from .instrument_models import Densitometer,Calibration,CalibrationSheet,ProofInstrument
from .instrument_schemas import MeterInput,CalibrationInput,SheetInput,RevokeInput
from . import instrument_service
router=APIRouter();queue=redis.Redis.from_url(os.environ['REDIS_URL'],decode_responses=True)
@router.get('/densitometers')
def meters(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(Densitometer).order_by(Densitometer.id))]
@router.post('/densitometers')
def create_meter(p:MeterInput,s=Depends(db_session),u=Depends(writers)):return pack(instrument_service.register_meter(s,p,u))
@router.post('/densitometers/{key}/enable')
def enable(key:int,s=Depends(db_session),u=Depends(admin)):return pack(instrument_service.set_meter_state(s,key,'active',u))
@router.post('/densitometers/{key}/disable')
def disable(key:int,s=Depends(db_session),u=Depends(admin)):return pack(instrument_service.set_meter_state(s,key,'disabled',u))
@router.get('/calibrations')
def calibrations(s=Depends(db_session),u=Depends(current)):
    result=[]
    for x in s.scalars(select(Calibration).order_by(Calibration.id.desc())):
        row=pack(x);row['sheets']=[pack(t) for t in s.scalars(select(CalibrationSheet).where(CalibrationSheet.calibration_id==x.id).order_by(CalibrationSheet.id))];result.append(row)
    return result
@router.post('/calibrations')
def create_calibration(p:CalibrationInput,s=Depends(db_session),u=Depends(writers)):return pack(instrument_service.create_calibration(s,p,u))
@router.post('/calibrations/{key}/sheets')
def add_sheet(key:int,p:SheetInput,s=Depends(db_session),u=Depends(writers)):return pack(instrument_service.add_sheet(s,key,p,u))
@router.post('/calibrations/{key}/fit')
def fit(key:int,s=Depends(db_session),u=Depends(writers)):return pack(instrument_service.submit_fit(s,key,u,queue))
@router.post('/calibrations/{key}/revoke')
def revoke(key:int,p:RevokeInput,s=Depends(db_session),u=Depends(admin)):return pack(instrument_service.revoke(s,key,p,u))
@router.get('/proof-instruments')
def proof_instruments(s=Depends(db_session),u=Depends(current)):return [pack(x) for x in s.scalars(select(ProofInstrument).order_by(ProofInstrument.id))]
