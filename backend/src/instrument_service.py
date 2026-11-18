from sqlalchemy import select,func
from fastapi import HTTPException
from .instrument_models import Densitometer,Calibration,CalibrationSheet,ProofInstrument
from .services import get,audit,now
from .paper_service import locked
from .constants import CAL_FIT_MIN,CAL_HOLDOUT_MIN

def accepted_calibration(s,meter_id):
    return s.scalar(select(Calibration).where(Calibration.meter_id==meter_id,Calibration.state=='accepted').order_by(Calibration.version.desc()))

def pin_instrument(s,proof,meter_id):
    # 收样时锁定仪器行：启停与送验并发时，以收样这一刻生效的仪器状态与校准为准。
    meter=s.scalar(select(Densitometer).where(Densitometer.id==meter_id).with_for_update().execution_options(populate_existing=True))
    if not meter:raise HTTPException(404,'密度计不存在')
    if meter.state!='active':raise HTTPException(409,'密度计已停用，不收新样；已收样张仍按收样时生效的校准判读')
    cal_id=None
    if meter.kind=='working':
        cal=accepted_calibration(s,meter.id)
        if not cal:raise HTTPException(409,'该工作仪没有验收通过的生效校准，不能收样判读')
        cal_id=cal.id
    row=s.scalar(select(ProofInstrument).where(ProofInstrument.proof_id==proof.id))
    if row:row.meter_id=meter.id;row.calibration_id=cal_id;row.pinned_at=now()
    else:s.add(ProofInstrument(proof_id=proof.id,meter_id=meter.id,calibration_id=cal_id,pinned_at=now()))
    return meter

def require_valid_calibration(s,proof):
    # 签印/复机闸口：撤销在先则该样张不能作为放行依据，须换合格仪器重测；已放行记录不回调。
    row=s.scalar(select(ProofInstrument).where(ProofInstrument.proof_id==proof.id))
    if not row or row.calibration_id is None:return
    cal=locked(s,Calibration,row.calibration_id)
    if cal.state!='accepted':raise HTTPException(409,'该样张所用校准已被撤销，须换合格仪器重新取样判读')

def register_meter(s,p,u):
    meter=Densitometer(**p.model_dump(),state='disabled');s.add(meter);audit(s,u,'登记密度计 '+p.code);s.commit();return meter

def set_meter_state(s,key,state,u):
    meter=locked(s,Densitometer,key)
    if meter.state==state:raise HTTPException(409,'仪器已处于该状态')
    if state=='active' and meter.kind=='working' and not accepted_calibration(s,meter.id):raise HTTPException(409,'须先有验收通过的校准，主管才能启用该工作仪')
    meter.state=state;audit(s,u,('启用' if state=='active' else '停用')+'密度计 '+meter.code);s.commit();return meter

def create_calibration(s,p,u):
    meter=locked(s,Densitometer,p.meter_id)
    if meter.kind!='working':raise HTTPException(409,'基准仪定义色标尺度，不需要校准')
    if s.scalar(select(Calibration.id).where(Calibration.meter_id==meter.id,Calibration.state.in_(['draft','fitting']))):raise HTTPException(409,'该仪已有进行中的校准版本，请先完成或等待验收')
    version=int(s.scalar(select(func.coalesce(func.max(Calibration.version),0)).where(Calibration.meter_id==meter.id)))+1
    cal=Calibration(meter_id=meter.id,version=version,state='draft',created_at=now());s.add(cal);audit(s,u,f'新建校准 {meter.code} V{version}');s.commit();return cal

def add_sheet(s,key,p,u):
    cal=locked(s,Calibration,key)
    if cal.state!='draft':raise HTTPException(409,'仅配对录数中的校准可追加色标，提交拟合后冻结')
    sheet=CalibrationSheet(calibration_id=cal.id,**p.model_dump());s.add(sheet);audit(s,u,f'校准色标 {p.code} 校准{key}');s.commit();return sheet

def submit_fit(s,key,u,r):
    cal=locked(s,Calibration,key)
    if cal.state!='draft':raise HTTPException(409,'该校准已提交拟合，不能重复送验')
    n=int(s.scalar(select(func.count()).select_from(CalibrationSheet).where(CalibrationSheet.calibration_id==cal.id)))
    if n<CAL_FIT_MIN+CAL_HOLDOUT_MIN:raise HTTPException(409,f'配对色标不足{CAL_FIT_MIN+CAL_HOLDOUT_MIN}张，无法按整张分出拟合与留出')
    cal.state='fitting';audit(s,u,f'提交校准验收 校准{key} 共{n}张');s.commit()
    try:r.rpush('press-calibrate',cal.id)
    except Exception:cal.state='draft';cal.acceptance={'error':'判读队列暂不可用'};s.commit();raise HTTPException(503,'判读队列暂不可用，请重试')
    return cal

def revoke(s,key,p,u):
    cal=locked(s,Calibration,key)
    if cal.state!='accepted':raise HTTPException(409,'仅验收通过的校准可撤销')
    cal.state='revoked';cal.revoked_at=now();cal.revoked_by=u.email;cal.revoke_reason=p.reason
    audit(s,u,f'撤销校准 仪{cal.meter_id} V{cal.version}：{p.reason}');s.commit();return cal
