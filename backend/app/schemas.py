from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from .models import Role
class LoginIn(BaseModel): email: str; password: str
class TokenPair(BaseModel): access_token:str; refresh_token:str; token_type:str="bearer"; role:Role
class PatientIn(BaseModel):
    first_name:str=Field(min_length=1,max_length=80); last_name:str=Field(min_length=1,max_length=80); national_id:str; date_of_birth:date; biological_sex:str; phone:str|None=None; email:str|None=None; clinic_id:int|None=None
    @model_validator(mode="after")
    def validate_profile(self):
        if self.date_of_birth > date.today(): raise ValueError("תאריך לידה עתידי אינו תקין")
        if self.biological_sex not in {"MALE","FEMALE","UNKNOWN"}: raise ValueError("מין ביולוגי אינו תקין")
        self.first_name=self.first_name.strip(); self.last_name=self.last_name.strip()
        if not self.first_name or not self.last_name: raise ValueError("נדרש שם מלא")
        return self
class PatientOut(BaseModel):
    id:str; first_name:str; last_name:str; masked_national_id:str; date_of_birth:date; biological_sex:str; phone:str|None; email:str|None; demo:bool; clinic_id:int|None=None; clinic_name:str|None=None; test_count:int=0; last_test_date:date|None=None
class ResultIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    analyte_code:str; numeric_value:float|None=None; text_value:str|None=None; unit:str; reference_min:float|None=None; reference_max:float|None=None; critical_low:float|None=None; critical_high:float|None=None; lab_flag:str|None=None; verified:bool=True
    @model_validator(mode="after")
    def ranges(self):
        if self.reference_min is not None and self.reference_max is not None and self.reference_min>=self.reference_max: raise ValueError("טווח הייחוס אינו תקין")
        if self.numeric_value is None and not self.text_value: raise ValueError("נדרש ערך")
        return self
class DoctorAssignment(BaseModel): doctor_user_id:int
class BloodTestIn(BaseModel):
    patient_id:str; laboratory_id:int=1; test_date:date; accession_number:str; source:str="MANUAL"; panel:str|None=None; notes:str|None=None; fasting:bool|None=None; reason:str|None=None; results:list[ResultIn]
    @model_validator(mode="after")
    def nonempty(self):
        if not self.results or not self.accession_number.strip(): raise ValueError("נדרשים מספר בדיקה ומדד אחד לפחות")
        return self
class Config:
    from_attributes=True
