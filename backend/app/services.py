import csv, io, math
from collections import Counter
from datetime import date
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from . import models as m
from .security import encrypt_national_id, national_id_hash, validate_israeli_id

ALGORITHM_VERSION="HEMORA-CLINICAL-1.0.0"
DISCLAIMER="תוצאה חריגה לבדה אינה קובעת אבחנה. יש לבחון אותה יחד עם תסמינים, היסטוריה רפואית וממצאי מעבדה נוספים בעזרת איש מקצוע רפואי."
class DomainError(Exception):
    def __init__(self,code,message,status=400,details=None): self.code=code; self.message=message; self.status=status; self.details=details or {}
class AuditService:
    SENSITIVE={"password","token","national_id","medical_record"}
    @classmethod
    def record(cls,db,user_id,action,entity_type,entity_id=None,metadata=None):
        clean={k:v for k,v in (metadata or {}).items() if k.lower() not in cls.SENSITIVE}
        db.add(m.AuditLog(user_id=user_id,action=action,entity_type=entity_type,entity_id=str(entity_id) if entity_id else None,metadata_sanitized=clean))
class PatientService:
    @staticmethod
    def create(db:Session,data,user_id,clinic_id=None):
        if not validate_israeli_id(data.national_id): raise DomainError("INVALID_NATIONAL_ID","מספר תעודת הזהות אינו תקין")
        digest=national_id_hash(data.national_id); existing=db.scalar(select(m.Patient).where(m.Patient.national_id_hash==digest))
        if existing: raise DomainError("DUPLICATE_PATIENT","מטופל עם תעודת זהות זו כבר קיים",409,{"patient_id":existing.id})
        patient=m.Patient(first_name=data.first_name,last_name=data.last_name,national_id_encrypted=encrypt_national_id(data.national_id),national_id_hash=digest,date_of_birth=data.date_of_birth,biological_sex=data.biological_sex,phone=data.phone,email=data.email,clinic_id=clinic_id)
        db.add(patient); db.flush(); AuditService.record(db,user_id,"PATIENT_CREATED","patient",patient.id); db.commit(); return patient
class UnitConversionService:
    CONVERSIONS={("mg/dL","mmol/L","GLUCOSE"):(1/18.0182,"mmol/L"),("mmol/L","mg/dL","GLUCOSE"):(18.0182,"mg/dL"),("mg/L","mg/dL","CRP"):(0.1,"mg/dL"),("mg/dL","mg/L","CRP"):(10,"mg/L"),("g/L","g/dL","HGB"):(0.1,"g/dL"),("g/dL","g/L","HGB"):(10,"g/L")}
    @classmethod
    def convert(cls,value,from_unit,to_unit,code):
        if from_unit==to_unit: return value
        rule=cls.CONVERSIONS.get((from_unit,to_unit,code.upper()))
        return value*rule[0] if rule else None
class ReferenceRangeService:
    @staticmethod
    def resolve(db,test,result,patient):
        if result.reference_min is not None and result.reference_max is not None: return result.reference_min,result.reference_max,result.reference_source or "LAB_SUPPLIED"
        ranges=db.scalars(select(m.ReferenceRange).where(m.ReferenceRange.analyte_id==result.analyte_id,m.ReferenceRange.active.is_(True),or_(m.ReferenceRange.laboratory_id==test.laboratory_id,m.ReferenceRange.laboratory_id.is_(None))).order_by(m.ReferenceRange.laboratory_id.desc())).all()
        age=(test.test_date-patient.date_of_birth).days//365
        for rr in ranges:
            if rr.valid_from and test.test_date < rr.valid_from: continue
            if rr.valid_to and test.test_date > rr.valid_to: continue
            if rr.sex and rr.sex!=patient.biological_sex: continue
            if rr.age_min is not None and age<rr.age_min: continue
            if rr.age_max is not None and age>rr.age_max: continue
            val=UnitConversionService.convert(result.numeric_value,result.unit,rr.unit,result.analyte.code) if result.numeric_value is not None else None
            if result.unit!=rr.unit and val is None: continue
            if val is not None: result.normalized_value=val; result.normalized_unit=rr.unit
            return rr.min_value,rr.max_value,"LAB_CONFIG" if rr.laboratory_id else "DEMO_GENERAL"
        return None,None,"NONE"
class ClinicalAnalysisEngine:
    @staticmethod
    def classify(value,low,high,critical_low=None,critical_high=None,verified=True):
        if not verified: return m.ResultStatus.UNVERIFIED,None
        if value is None or not math.isfinite(value): return m.ResultStatus.INVALID,None
        if critical_low is not None and value<critical_low: return m.ResultStatus.CRITICAL_LOW,critical_low-value
        if critical_high is not None and value>critical_high: return m.ResultStatus.CRITICAL_HIGH,value-critical_high
        if low is None or high is None: return m.ResultStatus.UNKNOWN_REFERENCE,None
        if value<low: return m.ResultStatus.LOW,low-value
        if value>high: return m.ResultStatus.HIGH,value-high
        return m.ResultStatus.NORMAL,min(value-low,high-value)
    @classmethod
    def analyze(cls,db,test):
        for result in test.results:
            low,high,source=ReferenceRangeService.resolve(db,test,result,test.patient); result.reference_min=low; result.reference_max=high; result.reference_source=source
            result.critical_low = result.critical_high = None
            threshold = db.scalar(select(m.CriticalThreshold).where(m.CriticalThreshold.analyte_id == result.analyte_id, m.CriticalThreshold.laboratory_id == test.laboratory_id, m.CriticalThreshold.unit == (result.normalized_unit or result.unit), m.CriticalThreshold.active.is_(True)))
            if threshold and threshold.source_reference.strip():
                result.critical_low, result.critical_high = threshold.low_value, threshold.high_value
            result.status,result.distance_from_range=cls.classify(result.normalized_value if result.normalized_value is not None else result.numeric_value,low,high,result.critical_low,result.critical_high,result.data_quality_status==m.Quality.VERIFIED)
        counts=Counter(r.status.value for r in test.results); complete=PanelCompletenessService.evaluate(test.panel,[r.analyte.code for r in test.results]); units=sum(bool(r.unit) for r in test.results); refs=sum(r.reference_min is not None for r in test.results); verified=sum(r.data_quality_status==m.Quality.VERIFIED for r in test.results); score=round(100*(.3*units/max(len(test.results),1)+.4*refs/max(len(test.results),1)+.3*verified/max(len(test.results),1))-5*len(complete),1); score=max(0,score)
        summary={"counts":dict(counts),"total":len(test.results),"missing":complete,"quality_level":"HIGH" if score>=85 else "MEDIUM" if score>=60 else "LOW","quality_explanation":"איכות הנתונים מתארת עד כמה הנתונים שהוזנו מלאים ומתאימים לניתוח ואינה ציון בריאות."}
        run=m.AnalysisRun(blood_test_id=test.id,algorithm_version=ALGORITHM_VERSION,summary=summary,quality_score=score); db.add(run); db.flush()
        for r in test.results:
            if r.status!=m.ResultStatus.NORMAL: db.add(m.AnalysisFinding(analysis_run_id=run.id,analyte_id=r.analyte_id,finding_type=r.status.value,severity="URGENT" if "CRITICAL" in r.status.value else "INFO",message=f"{r.analyte.display_name_he}: {r.status.value}",rationale=f"סיווג דטרמיניסטי ביחס לטווח {r.reference_min}–{r.reference_max}. {DISCLAIMER}"))
        existing = set(db.scalars(select(m.Alert.kind).where(m.Alert.blood_test_id == test.id)).all())
        messages = []
        if complete: messages.append(("MISSING", "מידע חסר בפאנל: " + ", ".join(complete)))
        for result in test.results:
            if result.status != m.ResultStatus.NORMAL:
                messages.append((result.analyte.code + ":" + result.status.value, result.analyte.display_name_he + " - " + {"LOW":"ערך נמוך","HIGH":"ערך גבוה","UNVERIFIED":"דורש אימות","UNKNOWN_REFERENCE":"חסר טווח ייחוס","INVALID":"ערך לא תקין","CRITICAL_LOW":"חציית סף קריטי","CRITICAL_HIGH":"חציית סף קריטי"}.get(result.status.value,result.status.value)))
        for kind, message in messages:
            if kind not in existing: db.add(m.Alert(patient_id=test.patient_id,blood_test_id=test.id,kind=kind,severity="URGENT" if "CRITICAL" in kind else "INFO",title_he=message))
        db.commit(); return run
class PanelCompletenessService:
    PANELS={"CBC":{"WBC","RBC","HGB","HCT","MCV","MCH","MCHC","RDW","PLT","MPV"},"LIPIDS":{"CHOL","LDL","HDL","TG"}}
    @classmethod
    def evaluate(cls,panel,codes): return sorted(cls.PANELS.get((panel or "").upper(),set())-set(codes))
class TestComparisonEngine:
    @staticmethod
    def _distance(value,low,high):
        if low is None or high is None: return None
        return low-value if value<low else value-high if value>high else 0
    @classmethod
    def compare(cls,current,previous):
        now={r.analyte.code:r for r in current.results}; before={r.analyte.code:r for r in previous.results}; rows=[]
        for code in sorted(set(now)|set(before)):
            c,p=now.get(code),before.get(code)
            if not c: rows.append({"code":code,"trend":"MISSING_CURRENT","message":f"לא ניתן להעריך את השינוי ב-{code} מכיוון שאין תוצאה בבדיקה הנוכחית.","reliability":"NOT_COMPARABLE"}); continue
            if not p: rows.append({"code":code,"trend":"NEW_PARAMETER","message":"זהו מדד חדש ביחס לבדיקה הקודמת ולכן אין בסיס להשוואה היסטורית.","reliability":"LOW"}); continue
            cv = c.normalized_value if c.normalized_value is not None else c.numeric_value
            pv = p.normalized_value if p.normalized_value is not None else p.numeric_value
            unusable = {m.ResultStatus.INVALID, m.ResultStatus.UNVERIFIED, m.ResultStatus.UNKNOWN_REFERENCE}
            if c.status in unusable or p.status in unusable or c.data_quality_status != m.Quality.VERIFIED or p.data_quality_status != m.Quality.VERIFIED:
                rows.append({"code":code,"trend":"NOT_COMPARABLE","message":"אין נתונים מאומתים וטווחי ייחוס מספקים להשוואה.","reliability":"NOT_COMPARABLE"})
                continue
            if cv is None or pv is None or (c.normalized_unit or c.unit)!=(p.normalized_unit or p.unit): rows.append({"code":code,"trend":"NOT_COMPARABLE","message":"לא ניתן לבצע השוואה מהימנה עקב הבדל ביחידות המדידה.","reliability":"NOT_COMPARABLE"}); continue
            cnormal=c.status==m.ResultStatus.NORMAL; pnormal=p.status==m.ResultStatus.NORMAL
            if pnormal and not cnormal: trend="NEW_ABNORMALITY"
            elif not pnormal and cnormal: trend="RETURNED_TO_RANGE"
            elif not pnormal and not cnormal:
                cd=cls._distance(cv,c.reference_min,c.reference_max); pd=cls._distance(pv,p.reference_min,p.reference_max)
                trend="IMPROVED" if cd is not None and pd is not None and cd<pd else "WORSENED" if cd is not None and pd is not None and cd>pd else "STILL_ABNORMAL"
            else: trend="STABLE"
            delta=cv-pv; rows.append({"code":code,"name_he":c.analyte.display_name_he,"current":cv,"previous":pv,"unit":c.normalized_unit or c.unit,"delta":round(delta,3),"percent_delta":round(delta/abs(pv)*100,1) if pv else None,"previous_status":p.status.value,"current_status":c.status.value,"trend":trend,"days":(current.test_date-previous.test_date).days,"reliability":"HIGH" if c.data_quality_status==p.data_quality_status==m.Quality.VERIFIED else "LOW"})
        return rows
class LongitudinalTrendService:
    @staticmethod
    def calculate(tests,code):
        points=[]; rejected=[]; target_unit=None
        for test in sorted(tests,key=lambda t:t.test_date):
            result=next((r for r in test.results if r.analyte.code==code),None)
            if not result: continue
            value=result.normalized_value if result.normalized_value is not None else result.numeric_value
            unit=result.normalized_unit or result.unit
            target_unit=target_unit or result.analyte.typical_unit
            converted=UnitConversionService.convert(value,unit,target_unit,code) if value is not None else None
            if converted is None or result.data_quality_status != m.Quality.VERIFIED:
                rejected.append(test.test_date.isoformat()); continue
            points.append({"date":test.test_date.isoformat(),"value":converted,"status":result.status.value,"unit":target_unit})
        abnormal_statuses={"LOW","HIGH","CRITICAL_LOW","CRITICAL_HIGH"}
        abnormal=[p for p in points if p["status"] in abnormal_statuses]
        consecutive=0
        for point in reversed(points):
            if point["status"] not in abnormal_statuses: break
            consecutive+=1
        return {"code":code,"points":points,"excluded_dates":rejected,"direction":"UP" if len(points)>1 and points[-1]["value"]>points[0]["value"] else "DOWN" if len(points)>1 and points[-1]["value"]<points[0]["value"] else "STABLE","consecutive_abnormal":consecutive,"first_abnormal":abnormal[0]["date"] if abnormal else None,"most_recent_normal":next((p["date"] for p in reversed(points) if p["status"]=="NORMAL"),None)}
class RecommendationEngine:
    @staticmethod
    def for_test(test):
        result=[]
        for r in test.results:
            if "CRITICAL" in r.status.value: result.append({"category":"CRITICAL","urgency":"URGENT","text":"תוצאה זו חוצה סף קריטי שהוגדר לבדיקה זו. יש לפעול לפי הנחיות המעבדה או הגורם המטפל."})
            elif r.status in {m.ResultStatus.LOW,m.ResultStatus.HIGH}: result.append({"category":"DISCUSS","urgency":"ROUTINE","text":"התוצאה מחוץ לטווח הייחוס שסופק. מומלץ לדון בה עם איש מקצוע רפואי יחד עם תוצאות נוספות, תסמינים והיסטוריה רפואית."})
            elif r.status==m.ResultStatus.UNVERIFIED: result.append({"category":"DATA_COMPLETION","urgency":"VERIFY","text":"יש לאמת תחילה את הערך מול דוח המעבדה המקורי."})
        if not result: result.append({"category":"MAINTAIN","urgency":"ROUTINE","text":"אפשר להמשיך באורח חיים מאוזן ובמעקב רפואי שגרתי בהתאם להנחיות האישיות."})
        return result
class ImportService:
    ALIASES={"HB":"HGB","HEMOGLOBIN":"HGB","המוגלובין":"HGB","GLU":"GLUCOSE"}
    @classmethod
    def preview_csv(cls,content:bytes):
        text=content.decode("utf-8-sig"); rows=[]; errors=[]
        for line,row in enumerate(csv.DictReader(io.StringIO(text)),2):
            raw=(row.get("analyte") or row.get("test") or "").strip(); code=cls.ALIASES.get(raw.upper(),raw.upper())
            try: value=float(row.get("value", ""))
            except ValueError: value=None; errors.append({"line":line,"code":"INVALID_VALUE","message":"ערך מספרי לא תקין"})
            rows.append({**row,"analyte_code":code,"numeric_value":value,"requires_verification":value is None})
        return {"rows":rows,"errors":errors,"requires_confirmation":True}

STATUS_HE = {
    "NORMAL": "בתוך טווח הייחוס",
    "LOW": "נמוך מטווח הייחוס",
    "HIGH": "גבוה מטווח הייחוס",
    "CRITICAL_LOW": "חוצה סף קריטי תחתון",
    "CRITICAL_HIGH": "חוצה סף קריטי עליון",
    "UNKNOWN_REFERENCE": "לא סווג - לא התקבל טווח ייחוס",
    "UNVERIFIED": "דורש אימות",
    "INVALID": "ערך לא תקין",
}
REFERENCE_SOURCE_HE = {
    "LAB_SUPPLIED": "טווח שסופק ישירות עם תוצאת המעבדה",
    "LAB_CONFIG": "טווח שהוגדר במערכת עבור המעבדה המבצעת",
    "DEMO_GENERAL": "טווח כללי לצורכי הדגמה בלבד",
    "NONE": "לא נמצא טווח ייחוס",
}
TREND_HE = {
    "IMPROVED": "השתפר",
    "WORSENED": "הורע",
    "STABLE": "יציב",
    "NEW_ABNORMALITY": "חריגה חדשה",
    "RETURNED_TO_RANGE": "חזר לטווח",
    "STILL_ABNORMAL": "עדיין חריג",
    "NEW_PARAMETER": "מדד חדש",
    "MISSING_CURRENT": "חסר בבדיקה הנוכחית",
    "NOT_COMPARABLE": "לא ניתן להשוואה",
}
DEMO_RANGE_NOTICE = "הטווח המוצג הוא טווח ייחוס כללי למטרות מידע בלבד. יש להעדיף את טווח הייחוס שסופק על ידי המעבדה המבצעת."


class ExplanationService:
    """Builds, from stored data only, the answer to 'why is HEMORA showing this?'.

    Every sentence is derived from the values actually saved for the result and
    for the matching result in the previous test. Nothing here is hard-coded per
    analyte, so the explanation stays true if the data or the ranges change.
    """

    @staticmethod
    def _previous(db, test, result):
        previous_test = db.scalar(
            select(m.BloodTest)
            .where(m.BloodTest.patient_id == test.patient_id, m.BloodTest.test_date < test.test_date)
            .order_by(m.BloodTest.test_date.desc()))
        if not previous_test:
            return None, None
        match = next((r for r in previous_test.results if r.analyte_id == result.analyte_id), None)
        return previous_test, match

    @classmethod
    def _classification_sentence(cls, result, value, unit):
        status = result.status.value
        low, high = result.reference_min, result.reference_max
        if status == "UNKNOWN_REFERENCE":
            return "לא התקבל טווח ייחוס עבור מדד זה, ולכן המערכת אינה מסווגת את התוצאה כתקינה או כחריגה."
        if status == "UNVERIFIED":
            return "הערך סומן כדורש אימות מול דוח המעבדה המקורי, ולכן הוא אינו משמש לפרשנות רפואית."
        if status == "INVALID":
            return "הערך שהוזן אינו ערך מספרי תקין ולכן לא ניתן לסווג אותו."
        if status == "CRITICAL_LOW":
            return f"הערך {value} {unit} נמוך מהסף הקריטי {result.critical_low} {unit} שהוגדר במערכת עבור בדיקה זו."
        if status == "CRITICAL_HIGH":
            return f"הערך {value} {unit} גבוה מהסף הקריטי {result.critical_high} {unit} שהוגדר במערכת עבור בדיקה זו."
        if status == "LOW":
            return f"הערך הנוכחי הוא {value} {unit}. טווח הייחוס מתחיל ב-{low} {unit}, ולכן התוצאה סווגה כנמוכה."
        if status == "HIGH":
            return f"הערך הנוכחי הוא {value} {unit}. טווח הייחוס מסתיים ב-{high} {unit}, ולכן התוצאה סווגה כגבוהה."
        return f"הערך הנוכחי הוא {value} {unit} ונמצא בתוך טווח הייחוס {low}–{high} {unit}, ולכן סווג כתקין."

    @classmethod
    def build(cls, db, test, result):
        value = result.normalized_value if result.normalized_value is not None else result.numeric_value
        unit = result.normalized_unit or result.unit
        previous_test, previous_result = cls._previous(db, test, result)

        comparison = None
        if previous_result is not None:
            row = next((r for r in TestComparisonEngine.compare(test, previous_test)
                        if r["code"] == result.analyte.code), None)
            if row:
                trend = row.get("trend")
                comparison = {
                    "previous_value": row.get("previous"),
                    "previous_unit": row.get("unit"),
                    "previous_date": previous_test.test_date.isoformat(),
                    "previous_status": row.get("previous_status"),
                    "delta": row.get("delta"),
                    "percent_delta": row.get("percent_delta"),
                    "days_between": row.get("days"),
                    "trend": trend,
                    "trend_he": TREND_HE.get(trend, trend),
                    "reliability": row.get("reliability"),
                    "rule_he": cls._comparison_rule(row, unit),
                }
        elif previous_test is not None:
            comparison = {"trend": "NEW_PARAMETER", "trend_he": TREND_HE["NEW_PARAMETER"],
                          "previous_date": previous_test.test_date.isoformat(),
                          "rule_he": "זהו מדד חדש ביחס לבדיקה הקודמת ולכן אין בסיס להשוואה היסטורית."}

        limitations = [DISCLAIMER]
        if result.reference_source == "DEMO_GENERAL":
            limitations.append(DEMO_RANGE_NOTICE)
        if result.data_quality_status != m.Quality.VERIFIED:
            limitations.append("הערך טרם אומת מול דוח המעבדה המקורי.")
        if comparison and comparison.get("trend") == "NOT_COMPARABLE":
            limitations.append("ההשוואה לבדיקה הקודמת אינה מהימנה ולכן לא בוצעה.")

        return {
            "analyte": {"code": result.analyte.code, "name_he": result.analyte.display_name_he,
                        "description_he": result.analyte.description_he},
            "measured": {"value": result.numeric_value, "unit": result.unit,
                         "normalized_value": result.normalized_value, "normalized_unit": result.normalized_unit},
            "reference": {"min": result.reference_min, "max": result.reference_max,
                          "source": result.reference_source,
                          "source_he": REFERENCE_SOURCE_HE.get(result.reference_source, result.reference_source),
                          "critical_low": result.critical_low, "critical_high": result.critical_high},
            "status": result.status.value,
            "status_he": STATUS_HE.get(result.status.value, result.status.value),
            "classification_reason": cls._classification_sentence(result, value, unit),
            "test_date": test.test_date.isoformat(),
            "comparison": comparison,
            "data_quality": result.data_quality_status.value,
            "limitations": limitations,
            "algorithm_version": ALGORITHM_VERSION,
        }

    @staticmethod
    def _comparison_rule(row, unit):
        trend = row.get("trend")
        if trend in {"NOT_COMPARABLE", "MISSING_CURRENT", "NEW_PARAMETER"}:
            return row.get("message", "")
        previous, current, delta = row.get("previous"), row.get("current"), row.get("delta")
        direction = "עלה" if (delta or 0) > 0 else "ירד" if (delta or 0) < 0 else "לא השתנה"
        base = (f"התוצאה הקודמת הייתה {previous} {unit} והנוכחית {current} {unit}, "
                f"כלומר הערך {direction} ב-{abs(delta) if delta is not None else 0} {unit}.")
        if trend == "IMPROVED":
            return base + " ההשוואה מבוססת על המרחק מטווח הייחוס: הערך התקרב לטווח אך טרם חזר אליו."
        if trend == "WORSENED":
            return base + " ההשוואה מבוססת על המרחק מטווח הייחוס: הערך התרחק מהטווח."
        if trend == "RETURNED_TO_RANGE":
            return base + " הערך עבר ממצב חריג אל תוך טווח הייחוס."
        if trend == "NEW_ABNORMALITY":
            return base + " הערך עבר מתוך טווח הייחוס אל מחוץ לו ולכן דורש תשומת לב."
        if trend == "STILL_ABNORMAL":
            return base + " הערך נותר מחוץ לטווח הייחוס במרחק דומה."
        return base + " שני הערכים נמצאים בתוך טווח הייחוס."
