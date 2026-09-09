from datetime import date, timedelta
from sqlalchemy import select
from .config import settings
from .database import Base, SessionLocal, engine
from . import models as m
from .security import encrypt_national_id, hash_password, national_id_hash
from .services import ClinicalAnalysisEngine

ANALYTES=[
 ("WBC","תאי דם לבנים","White blood cells","CBC","מספר תאי הדם הלבנים, המשתתפים בתגובת מערכת החיסון.","10^3/uL",4,11),("RBC","תאי דם אדומים","Red blood cells","CBC","מספר תאי הדם האדומים הנושאים חמצן.","10^6/uL",4.2,5.8),("HGB","המוגלובין","Hemoglobin","CBC","החלבון בתאי הדם האדומים המסייע בהובלת חמצן.","g/dL",12,16),("HCT","המטוקריט","Hematocrit","CBC","שיעור נפח תאי הדם האדומים בדם.","%",36,48),("MCV","נפח כדורית ממוצע","MCV","CBC","הגודל הממוצע של תאי הדם האדומים.","fL",80,100),("MCH","כמות המוגלובין בכדורית","MCH","CBC","כמות ההמוגלובין הממוצעת בכל תא דם אדום.","pg",27,33),("MCHC","ריכוז המוגלובין בכדורית","MCHC","CBC","ריכוז ההמוגלובין הממוצע בתאי הדם האדומים.","g/dL",32,36),("RDW","שונות בגודל כדוריות","RDW","CBC","מידת השונות בגודל תאי הדם האדומים.","%",11.5,14.5),("PLT","טסיות","Platelets","CBC","טסיות משתתפות בתהליך קרישת הדם.","10^3/uL",150,450),("MPV","נפח טסית ממוצע","MPV","CBC","הגודל הממוצע של הטסיות.","fL",7.5,12),
 ("NEUT%","נויטרופילים אחוז","Neutrophils %","DIFF","שיעור הנויטרופילים מכלל תאי הדם הלבנים.","%",40,75),("NEUT#","נויטרופילים","Neutrophils absolute","DIFF","מספר מוחלט של נויטרופילים.","10^3/uL",1.5,7.5),("LYMPH%","לימפוציטים אחוז","Lymphocytes %","DIFF","שיעור הלימפוציטים.","%",20,45),("LYMPH#","לימפוציטים","Lymphocytes absolute","DIFF","מספר מוחלט של לימפוציטים.","10^3/uL",1,4),("MONO%","מונוציטים אחוז","Monocytes %","DIFF","שיעור המונוציטים.","%",2,10),("MONO#","מונוציטים","Monocytes absolute","DIFF","מספר מוחלט של מונוציטים.","10^3/uL",.2,1),("EOS%","אאוזינופילים אחוז","Eosinophils %","DIFF","שיעור האאוזינופילים.","%",0,6),("EOS#","אאוזינופילים","Eosinophils absolute","DIFF","מספר מוחלט של אאוזינופילים.","10^3/uL",0,.6),("BASO%","בזופילים אחוז","Basophils %","DIFF","שיעור הבזופילים.","%",0,2),("BASO#","בזופילים","Basophils absolute","DIFF","מספר מוחלט של בזופילים.","10^3/uL",0,.2),
 ("GLUCOSE","גלוקוז","Glucose","CHEMISTRY","רמת הסוכר שנמדדה בדם.","mg/dL",70,100),("CREATININE","קריאטינין","Creatinine","CHEMISTRY","תוצר פירוק הנבדק לעיתים כחלק מהערכת תפקוד כליות.","mg/dL",.6,1.2),("UREA","אוראה","Urea","CHEMISTRY","תוצר פסולת חנקני בדם.","mg/dL",17,43),("SODIUM","נתרן","Sodium","CHEMISTRY","אלקטרוליט מרכזי במאזן הנוזלים.","mmol/L",135,145),("POTASSIUM","אשלגן","Potassium","CHEMISTRY","אלקטרוליט חשוב לפעילות תאים ושרירים.","mmol/L",3.5,5.1),("CALCIUM","סידן","Calcium","CHEMISTRY","מינרל המעורב בעצם, שריר ומערכת העצבים.","mg/dL",8.6,10.2),("PROTEIN","חלבון כללי","Total protein","CHEMISTRY","סך החלבונים העיקריים בדם.","g/dL",6.4,8.3),("ALBUMIN","אלבומין","Albumin","CHEMISTRY","חלבון עיקרי המיוצר בכבד.","g/dL",3.5,5.2),("ALT","ALT","ALT","LIVER","אנזים הנמדד כחלק מבדיקות כבד.","U/L",0,35),("AST","AST","AST","LIVER","אנזים הקיים במספר רקמות.","U/L",0,35),("ALP","פוספטזה בסיסית","ALP","LIVER","אנזים הקשור בין השאר לכבד ולעצם.","U/L",35,105),("GGT","GGT","GGT","LIVER","אנזים הנמדד בהערכת דרכי מרה וכבד.","U/L",0,40),("BILIRUBIN","בילירובין כללי","Total bilirubin","LIVER","תוצר פירוק של תאי דם אדומים.","mg/dL",.2,1.2),
 ("CHOL","כולסטרול כללי","Total cholesterol","LIPIDS","שומן הנישא בדם ומשמש תהליכים שונים בגוף.","mg/dL",0,200),("LDL","כולסטרול LDL","LDL","LIPIDS","חלקיק הנושא כולסטרול בדם.","mg/dL",0,130),("HDL","כולסטרול HDL","HDL","LIPIDS","חלקיק המעורב בהובלת כולסטרול.","mg/dL",40,100),("TG","טריגליצרידים","Triglycerides","LIPIDS","סוג שומן הנישא בדם.","mg/dL",0,150),("IRON","ברזל","Iron","IRON","כמות הברזל בדם בזמן הבדיקה.","ug/dL",50,170),("FERRITIN","פריטין","Ferritin","IRON","חלבון הקשור למאגרי ברזל בגוף.","ng/mL",15,150),("TRANSFERRIN","טרנספרין","Transferrin","IRON","חלבון המוביל ברזל בדם.","mg/dL",200,360),("TIBC","קיבולת קשירת ברזל","TIBC","IRON","מדד לקיבולת נשיאת הברזל בדם.","ug/dL",250,450),("TSAT","רוויית טרנספרין","Transferrin saturation","IRON","שיעור אתרי הקשירה של טרנספרין התפוסים בברזל.","%",20,50),("B12","ויטמין B12","Vitamin B12","VITAMINS","ויטמין המעורב בתפקוד עצבי ויצירת תאי דם.","pg/mL",200,900),("FOLATE","פולאט","Folate","VITAMINS","ויטמין המעורב ביצירת תאים.","ng/mL",4,20),("VITD","ויטמין D","Vitamin D","VITAMINS","ויטמין המעורב בין השאר בבריאות העצם.","ng/mL",20,50),("TSH","TSH","TSH","ENDOCRINE","הורמון הקשור לבקרת פעילות בלוטת התריס.","mIU/L",.4,4),("FT4","T4 חופשי","Free T4","ENDOCRINE","הורמון של בלוטת התריס בצורתו החופשית.","ng/dL",.8,1.8),("HBA1C","HbA1c","HbA1c","CHEMISTRY","מדד המשקף חשיפה ממוצעת לגלוקוז לאורך זמן.","%",4,5.6),("CRP","CRP","CRP","INFLAMMATION","חלבון שעשוי להשתנות בתהליכים דלקתיים שונים.","mg/L",0,5)]

def seed_demo_data():
    Base.metadata.create_all(engine); db=SessionLocal()
    if db.scalar(select(m.User.id).limit(1)): db.close(); return
    lab=m.Laboratory(name="מעבדת HEMORA להדגמה",code="DEMO-LAB"); db.add(lab)
    north=m.Clinic(name="מרפאת הצפון",code="CLINIC-N",city="חיפה"); centre=m.Clinic(name="מרפאת המרכז",code="CLINIC-C",city="תל אביב")
    db.add_all([north,centre]); db.flush()
    analytes={}
    for code,he,en,cat,desc,unit,low,high in ANALYTES:
        a=m.Analyte(code=code,display_name_he=he,display_name_en=en,category=cat,description_he=desc,typical_unit=unit); db.add(a); db.flush(); analytes[code]=a; db.add(m.ReferenceRange(analyte_id=a.id,laboratory_id=None,unit=unit,min_value=low,max_value=high,source_reference="טווח כללי לצורכי הדגמה בלבד",active=True))
    for alias,code in [("HB","HGB"),("HEMOGLOBIN","HGB"),("המוגלובין","HGB"),("GLU","GLUCOSE")]: db.add(m.AnalyteAlias(analyte_id=analytes[code].id,alias=alias))
    ids=["311111118","322222226","333333334","344444442","355555559","366666667"]
    patients=[]
    names=[("נועה","לוי"),("דניאל","כהן"),("מיה","ישראלי"),("יואב","שלום"),("תמר","אור"),("אדם","גל")]
    for i,(first,last) in enumerate(names):
        p=m.Patient(first_name=first,last_name=last,national_id_encrypted=encrypt_national_id(ids[i]),national_id_hash=national_id_hash(ids[i]),date_of_birth=date(1985+i,2,12),biological_sex="FEMALE" if i%2==0 else "MALE",email=f"demo{i+1}@hemora.local",clinic_id=(north.id if i<3 else centre.id),demo=True); db.add(p); db.flush(); patients.append(p)
    def user(email,role,clinic_id=None,patient_id=None):
        row=m.User(email=email,password_hash=hash_password(settings.default_user_password),role=role,clinic_id=clinic_id,patient_id=patient_id); db.add(row); db.flush(); return row
    user("admin@hemora.local",m.Role.ADMIN)
    doctor1=user("doctor1@hemora.local",m.Role.DOCTOR,clinic_id=north.id)
    doctor2=user("doctor2@hemora.local",m.Role.DOCTOR,clinic_id=north.id)
    doctor3=user("doctor3@hemora.local",m.Role.DOCTOR,clinic_id=centre.id)
    user("clinic@hemora.local",m.Role.CLINIC,clinic_id=north.id)
    user("clinic2@hemora.local",m.Role.CLINIC,clinic_id=centre.id)
    user("patient@hemora.local",m.Role.PATIENT,patient_id=patients[1].id)
    # Deliberately uneven so the demo shows each scope at a glance:
    # doctor1 -> 2 patients, doctor2 -> 1, the north clinic -> all 3 of its own, admin -> all 6.
    for doctor,owned in ((doctor1,(1,2)),(doctor2,(0,)),(doctor3,(3,4,5))):
        for index in owned: db.add(m.DoctorPatient(doctor_user_id=doctor.id,patient_id=patients[index].id))
    db.flush()
    def add_test(pi,days,access,hgb=13.5,missing=False,unit="g/dL",extra=None):
        t=m.BloodTest(patient_id=patients[pi].id,laboratory_id=lab.id,test_date=date.today()-timedelta(days=days),accession_number=access,panel="CBC",source="DEMO"); db.add(t); db.flush()
        values={"WBC":6.2,"RBC":4.7,"HCT":41,"MCV":88,"MCH":29,"MCHC":34,"RDW":12.7,"PLT":265,"MPV":9.5}
        if not missing: values["HGB"]=hgb
        if extra: values.update(extra)
        for code,value in values.items():
            a=analytes[code]; val=value*10 if code=="HGB" and unit=="g/L" else value; db.add(m.TestResult(blood_test_id=t.id,analyte_id=a.id,numeric_value=val,unit=unit if code=="HGB" else a.typical_unit,data_quality_status=m.Quality.VERIFIED,reference_source="DEMO_GENERAL"))
        db.commit(); db.refresh(t); ClinicalAnalysisEngine.analyze(db,t)
    add_test(0,5,"DEMO-001"); add_test(1,180,"DEMO-002-A",10.8); add_test(1,90,"DEMO-002-B",11.3); add_test(1,4,"DEMO-002-C",11.7); add_test(2,100,"DEMO-003-A",13.4); add_test(2,3,"DEMO-003-B",10.9); add_test(3,2,"DEMO-004",missing=True); add_test(4,70,"DEMO-005-A",12.2,unit="g/L"); add_test(4,1,"DEMO-005-B",12.8); add_test(5,60,"DEMO-006-A",13.1,unit="mmol/L"); add_test(5,2,"DEMO-006-B",13.2)
    db.close()
if __name__=="__main__": seed_demo_data()
