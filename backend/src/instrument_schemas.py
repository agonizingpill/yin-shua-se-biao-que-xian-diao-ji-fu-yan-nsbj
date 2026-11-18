from pydantic import BaseModel,Field,ConfigDict,field_validator
from .constants import METER_KINDS
class Inputs(BaseModel):
    model_config=ConfigDict(allow_inf_nan=False)
class MeterInput(Inputs):
    code:str=Field(min_length=1,max_length=40)
    kind:str='working'
    note:str=Field(default='',max_length=200)
    @field_validator('code')
    @classmethod
    def required(cls,v):
        if not v.strip():raise ValueError('不能为空')
        return v.strip()
    @field_validator('kind')
    @classmethod
    def kind_known(cls,v):
        if v not in METER_KINDS:raise ValueError('仪器类型须为 reference 或 working')
        return v
class CalibrationInput(Inputs):
    meter_id:int
class SheetInput(Inputs):
    code:str=Field(min_length=1,max_length=40)
    ref_c:float=Field(ge=0,le=3)
    ref_m:float=Field(ge=0,le=3)
    ref_y:float=Field(ge=0,le=3)
    ref_k:float=Field(ge=0,le=3)
    ref_gain:float=Field(ge=0,le=50)
    new_c:float=Field(ge=0,le=3)
    new_m:float=Field(ge=0,le=3)
    new_y:float=Field(ge=0,le=3)
    new_k:float=Field(ge=0,le=3)
    new_gain:float=Field(ge=0,le=50)
    @field_validator('code')
    @classmethod
    def sheet_code(cls,v):
        if not v.strip():raise ValueError('不能为空')
        return v.strip()
class RevokeInput(Inputs):
    reason:str=Field(min_length=5,max_length=300)
    @field_validator('reason')
    @classmethod
    def reason_text(cls,v):
        if len(v.strip())<5:raise ValueError('撤销依据至少5字')
        return v.strip()
