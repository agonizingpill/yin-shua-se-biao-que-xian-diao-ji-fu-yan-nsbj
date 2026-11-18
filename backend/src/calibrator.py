import numpy as np
from sqlalchemy import select
from .instrument_models import CalibrationSheet
from .classifier import train_model,features
from .services import now
from .constants import CAL_CHANNELS,CAL_FIT_MIN,CAL_HOLDOUT_MIN,CAL_AGREEMENT_MIN,CAL_RESIDUAL_DENSITY,CAL_RESIDUAL_GAIN

def values(sheet,prefix):return [getattr(sheet,prefix+'_'+ch) for ch in CAL_CHANNELS]
def evaluate(s,cal):
    sheets=s.scalars(select(CalibrationSheet).where(CalibrationSheet.calibration_id==cal.id).order_by(CalibrationSheet.id)).all()
    n=len(sheets)
    if n<CAL_FIT_MIN+CAL_HOLDOUT_MIN:
        cal.state='failed';cal.acceptance={'error':f'配对色标不足{CAL_FIT_MIN+CAL_HOLDOUT_MIN}张，无法按整张分出拟合与留出'};return
    # 按整张固定seed分出拟合与留出，同一张色标的十项读数不跨界。
    order=np.random.RandomState(42).permutation(n);n_hold=max(CAL_HOLDOUT_MIN,int(round(n/3)))
    hold=[sheets[i] for i in order[:n_hold]];fit_rows=[sheets[i] for i in order[n_hold:]]
    fit={}
    for i,ch in enumerate(CAL_CHANNELS):
        a,b=np.polyfit([values(x,'new')[i] for x in fit_rows],[values(x,'ref')[i] for x in fit_rows],1)
        fit[ch]=[round(float(a),6),round(float(b),6)]
    def corrected(sheet):return [fit[ch][0]*v+fit[ch][1] for ch,v in zip(CAL_CHANNELS,values(sheet,'new'))]
    model,*_=train_model(s)
    def defect(vals):return str(model.predict([features(vals)])[0])
    per=[];matches=0;max_res={ch:0.0 for ch in CAL_CHANNELS}
    for sheet in hold:
        corr=corrected(sheet);ref=values(sheet,'ref')
        for i,ch in enumerate(CAL_CHANNELS):max_res[ch]=max(max_res[ch],abs(corr[i]-ref[i]))
        ref_defect=defect(ref);raw_defect=defect(values(sheet,'new'));corr_defect=defect(corr)
        match=corr_defect==ref_defect;matches+=match
        per.append({'code':sheet.code,'ref_defect':ref_defect,'raw_defect':raw_defect,'corrected_defect':corr_defect,'match':match})
    agreement=round(matches/len(hold),4)
    res_density=max(max_res[ch] for ch in CAL_CHANNELS[:4]);res_gain=max_res['gain']
    passed=agreement>=CAL_AGREEMENT_MIN and res_density<=CAL_RESIDUAL_DENSITY and res_gain<=CAL_RESIDUAL_GAIN
    cal.fit=fit
    cal.acceptance={'fit_codes':[x.code for x in fit_rows],'holdout_codes':[x.code for x in hold],'fit_rows':len(fit_rows),'holdout_rows':len(hold),'agreement':agreement,'agreement_required':CAL_AGREEMENT_MIN,'max_residual_density':round(res_density,4),'max_residual_gain':round(res_gain,4),'residual_limit_density':CAL_RESIDUAL_DENSITY,'residual_limit_gain':CAL_RESIDUAL_GAIN,'per_sheet':per,'passed':passed,'seed':42,'evaluated_at':now()}
    cal.state='accepted' if passed else 'failed'
    if passed:cal.accepted_at=now()
