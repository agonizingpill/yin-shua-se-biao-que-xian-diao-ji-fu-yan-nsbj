import numpy as np
from sqlalchemy import select
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix,accuracy_score
from .models import ReferenceSheet,PrintJob
from .constants import DEFECTS,CAL_CHANNELS

def features(values,target=1.4):return [values[0]/target,values[1]/target,values[2]/target,values[3]/target,values[4]/100]
def vector(p,target=1.4):return features([p.density_c,p.density_m,p.density_y,p.density_k,p.dot_gain],target)
def train_model(s):
    refs=s.scalars(select(ReferenceSheet).order_by(ReferenceSheet.id)).all()
    if len(refs)<60:raise ValueError('带标签参考色标不足60张')
    x=np.array([vector(r)for r in refs]);y=np.array([r.label for r in refs]);ids=np.arange(len(refs))
    train,test=train_test_split(ids,test_size=.2,stratify=y,random_state=42)
    model=make_pipeline(StandardScaler(),SVC(kernel='rbf',C=2,probability=True,random_state=42));model.fit(x[train],y[train])
    return model,refs,train,test,x,y
def applied_readings(s,p):
    # 按收样时钉住的校准把新仪读数折算到基准尺度；基准仪与历史样张原样使用。
    from .instrument_models import ProofInstrument,Calibration,Densitometer
    raw=[p.density_c,p.density_m,p.density_y,p.density_k,p.dot_gain]
    row=s.scalar(select(ProofInstrument).where(ProofInstrument.proof_id==p.id))
    if not row:return raw,None
    meter=s.get(Densitometer,row.meter_id)
    info={'meter_code':meter.code if meter else None,'meter_kind':meter.kind if meter else None,'pinned_at':row.pinned_at}
    if not row.calibration_id:
        info['calibration_version']=None;return raw,info
    cal=s.get(Calibration,row.calibration_id)
    fit=cal.fit or {}
    corrected=[fit[ch][0]*raw[i]+fit[ch][1] for i,ch in enumerate(CAL_CHANNELS)]
    info.update({'calibration_id':cal.id,'calibration_version':cal.version,'calibration_state':cal.state,'raw_readings':[round(v,4) for v in raw],'corrected_readings':[round(v,4) for v in corrected]})
    return corrected,info
def classify(s,p):
    model,refs,train,test,x,y=train_model(s)
    target=s.get(PrintJob,p.job_id).target_density
    readings,instrument=applied_readings(s,p)
    query=[features(readings,target)];label=str(model.predict(query)[0]);prob=model.predict_proba(query)[0];pred=model.predict(x[test])
    evidence={'probabilities':{str(c):round(float(v),5)for c,v in zip(model[-1].classes_,prob)},'labels':list(DEFECTS),'confusion_matrix':confusion_matrix(y[test],pred,labels=list(DEFECTS)).tolist(),'accuracy':round(float(accuracy_score(y[test],pred)),4),'train_rows':len(train),'holdout_rows':len(test),'seed':42,'reference_codes':[refs[i].code for i in train],'holdout_codes':[refs[i].code for i in test],'current_proof_code':p.code,'feature_names':['青密度比','品红密度比','黄密度比','黑密度比','网点扩大率'],'features':[round(v,5) for v in query[0]]}
    if instrument:evidence['instrument']=instrument
    return label,evidence
