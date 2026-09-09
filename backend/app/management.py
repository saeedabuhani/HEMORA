"""Validated administration and persisted alert workflows."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from . import models as m
from .database import get_db
from .api import assert_patient_access, current_user, roles, scope_patients
from .services import AuditService
from .security import hash_password

router=APIRouter(prefix="/api")
CATALOG={
    "clinics":(m.Clinic,{"name":str,"code":str,"city":str|None,"active":bool}),
    "laboratories":(m.Laboratory,{"name":str,"code":str,"country":str,"active":bool}),
    "analytes":(m.Analyte,{"code":str,"display_name_he":str,"display_name_en":str,"category":str,"description_he":str,"typical_unit":str,"comparison_direction":str,"active":bool}),
    "reference-ranges":(m.ReferenceRange,{"analyte_id":int,"laboratory_id":int|None,"sex":str|None,"age_min":int|None,"age_max":int|None,"unit":str,"min_value":float,"max_value":float,"valid_from":date|None,"valid_to":date|None,"source_reference":str,"active":bool}),
    "critical-thresholds":(m.CriticalThreshold,{"analyte_id":int,"laboratory_id":int,"unit":str,"low_value":float|None,"high_value":float|None,"source_reference":str,"active":bool}),
    "recommendations":(m.Recommendation,{"rule_code":str,"title_he":str,"content_he":str,"severity":str,"evidence_source":str,"active":bool}),
}

@router.get("/admin/{resource}")
def list_config(resource:str,user=Depends(roles(m.Role.ADMIN)),db:Session=Depends(get_db)):
    if resource not in CATALOG: raise HTTPException(404,"לא נמצא")
    model,fields=CATALOG[resource]
    return [{"id":row.id,**{key:getattr(row,key) for key in fields}} for row in db.scalars(select(model).order_by(model.id)).all()]

def save(resource,record_id,payload,user,db):
    if resource not in CATALOG: raise HTTPException(404,"לא נמצא")
    model,fields=CATALOG[resource]
    schema=create_model("Configuration",__config__=ConfigDict(extra="forbid",allow_inf_nan=False),**{key:(kind,...) for key,kind in fields.items()})
    try: values=schema.model_validate(payload).model_dump()
    except Exception: raise HTTPException(422,detail={"message":"יש למלא את כל השדות בהתאם לסוג הנתונים"})
    if resource=="reference-ranges" and values["min_value"]>=values["max_value"]: raise HTTPException(422,"טווח לא תקין")
    if "analyte_id" in values and not db.get(m.Analyte,values["analyte_id"]): raise HTTPException(422,"מדד אינו קיים")
    if values.get("laboratory_id") and not db.get(m.Laboratory,values["laboratory_id"]): raise HTTPException(422,"מעבדה אינה קיימת")
    if resource=="critical-thresholds":
        if not values["source_reference"].strip() or values["low_value"] is None and values["high_value"] is None: raise HTTPException(422,"נדרשים מקור מאומת וסף")
        if values["low_value"] is not None and values["high_value"] is not None and values["low_value"]>=values["high_value"]: raise HTTPException(422,"ספים לא תקינים")
    row=db.get(model,record_id) if record_id else model()
    if row is None: raise HTTPException(404,"לא נמצא")
    before={key:str(getattr(row,key,None)) for key in fields} if record_id else {}
    for key,value in values.items(): setattr(row,key,value)
    db.add(row)
    try:
        db.flush(); AuditService.record(db,user.id,"ADMIN_CONFIGURATION_CHANGED",resource,row.id,{"before":before,"after":{k:str(v) for k,v in values.items()}}); db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409,"הרשומה כבר קיימת או אינה תקינה")
    return {"id":row.id}

@router.post("/admin/{resource}")
def create_config(resource:str,payload:dict,user=Depends(roles(m.Role.ADMIN)),db:Session=Depends(get_db)): return save(resource,None,payload,user,db)

@router.put("/admin/{resource}/{record_id}")
def update_config(resource:str,record_id:int,payload:dict,user=Depends(roles(m.Role.ADMIN)),db:Session=Depends(get_db)): return save(resource,record_id,payload,user,db)

class UserIn(BaseModel):
    email:str=Field(min_length=5,max_length=255)
    password:str=Field(min_length=8,max_length=128)
    role:Literal["ADMIN","DOCTOR","CLINIC","PATIENT"]
    clinic_id:int|None=None
    patient_id:str|None=None

@router.get("/admin/users")
def list_users(user=Depends(roles(m.Role.ADMIN)),db:Session=Depends(get_db)):
    rows=db.scalars(select(m.User).order_by(m.User.id)).all()
    return [{"id":u.id,"email":u.email,"role":u.role.value,"clinic_id":u.clinic_id,"patient_id":u.patient_id,"is_active":u.is_active} for u in rows]

@router.post("/admin/users")
def create_user(data:UserIn,user=Depends(roles(m.Role.ADMIN)),db:Session=Depends(get_db)):
    if db.scalar(select(m.User.id).where(m.User.email==data.email.lower())): raise HTTPException(409,detail={"code":"DUPLICATE_USER","message":"קיים כבר משתמש עם דוא\u05f4ל זה","details":{}})
    role=m.Role(data.role)
    if role in {m.Role.DOCTOR,m.Role.CLINIC}:
        if not data.clinic_id or not db.get(m.Clinic,data.clinic_id): raise HTTPException(422,detail={"code":"CLINIC_REQUIRED","message":"רופא ומרפאה חייבים להיות משויכים למרפאה קיימת","details":{}})
    if role==m.Role.PATIENT and (not data.patient_id or not db.get(m.Patient,data.patient_id)): raise HTTPException(422,detail={"code":"PATIENT_REQUIRED","message":"משתמש מטופל חייב להיות משויך למטופל קיים","details":{}})
    row=m.User(email=data.email.lower(),password_hash=hash_password(data.password),role=role,clinic_id=data.clinic_id if role in {m.Role.DOCTOR,m.Role.CLINIC} else None,patient_id=data.patient_id if role==m.Role.PATIENT else None)
    db.add(row); db.flush()
    AuditService.record(db,user.id,"USER_CREATED","user",row.id,{"email":row.email,"role":role.value}); db.commit()
    return {"id":row.id,"email":row.email,"role":row.role.value}

class AlertState(BaseModel): state:Literal["NEW","READ","RESOLVED"]
@router.get("/alerts")
def alerts(user=Depends(current_user),db:Session=Depends(get_db)):
    query=select(m.Alert).where(m.Alert.patient_id.in_(scope_patients(select(m.Patient.id),user)))
    return [{"id":a.id,"title_he":a.title_he,"kind":a.kind,"severity":a.severity,"state":a.state,"test_id":a.blood_test_id} for a in db.scalars(query.order_by(m.Alert.created_at.desc()).limit(200)).all()]

@router.patch("/alerts/{alert_id}")
def set_alert(alert_id:int,data:AlertState,user=Depends(current_user),db:Session=Depends(get_db)):
    alert=db.get(m.Alert,alert_id)
    if not alert: raise HTTPException(404,"התראה אינה קיימת")
    assert_patient_access(db,user,alert.patient_id)
    alert.state=data.state; AuditService.record(db,user.id,"ALERT_UPDATED","alert",alert.id,{"state":data.state});db.commit();return {"state":alert.state}
