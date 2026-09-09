from datetime import date
from types import SimpleNamespace
import pytest
from sqlalchemy import select
from app import models as m
from app.security import validate_israeli_id
from app.services import AuditService,ClinicalAnalysisEngine,PanelCompletenessService,TestComparisonEngine,UnitConversionService
from app.security import encrypt_national_id,national_id_hash
from app.reporting import ReportService

def test_israeli_id_validation(): assert validate_israeli_id("000000018"); assert not validate_israeli_id("123456789")
@pytest.mark.parametrize("value,expected",[(14,m.ResultStatus.NORMAL),(11,m.ResultStatus.LOW),(17,m.ResultStatus.HIGH)])
def test_classification(value,expected): assert ClinicalAnalysisEngine.classify(value,12,16)[0]==expected
def test_missing_reference_and_critical():
    assert ClinicalAnalysisEngine.classify(10,None,None)[0]==m.ResultStatus.UNKNOWN_REFERENCE
    assert ClinicalAnalysisEngine.classify(4,5,10,critical_low=4.5)[0]==m.ResultStatus.CRITICAL_LOW
def test_unit_conversion():
    assert UnitConversionService.convert(90,"mg/dL","mmol/L","GLUCOSE")==pytest.approx(4.995,abs=.001)
    assert UnitConversionService.convert(1,"mg/dL","x","GLUCOSE") is None
def test_panel_completeness(): assert "HGB" in PanelCompletenessService.evaluate("CBC",["WBC","RBC","HCT","MCV","MCH","MCHC","RDW","PLT","MPV"])
def test_audit_sanitizes(db,users):
    AuditService.record(db,users[0].id,"TEST","entity","1",{"password":"x","safe":"yes"});db.commit();log=db.scalar(select(m.AuditLog));assert "password" not in log.metadata_sanitized and log.metadata_sanitized["safe"]=="yes"

def test_pdf_report_is_valid(db):
    patient=m.Patient(first_name="דמו",last_name="בדיקה",national_id_encrypted=encrypt_national_id("000000018"),national_id_hash=national_id_hash("000000018"),date_of_birth=date(1990,1,1),biological_sex="FEMALE",demo=True)
    lab=m.Laboratory(name="Demo",code="PDF-LAB"); analyte=m.Analyte(code="HGB",display_name_he="המוגלובין",display_name_en="Hemoglobin",category="CBC",description_he="בדיקת הדגמה",typical_unit="g/dL")
    db.add_all([patient,lab,analyte]); db.flush(); test=m.BloodTest(patient_id=patient.id,laboratory_id=lab.id,test_date=date.today(),accession_number="PDF-TEST",panel="CBC",source="DEMO"); db.add(test); db.flush(); db.add(m.TestResult(blood_test_id=test.id,analyte_id=analyte.id,numeric_value=13.2,unit="g/dL",reference_min=12,reference_max=16,status=m.ResultStatus.NORMAL,data_quality_status=m.Quality.VERIFIED,reference_source="LAB_SUPPLIED")); db.add(m.AnalysisRun(blood_test_id=test.id,algorithm_version="HEMORA-CLINICAL-1.0.0",summary={},quality_score=100)); db.commit(); db.refresh(test)
    content=ReportService.generate_pdf(db,test)
    assert content.startswith(b"%PDF") and len(content)>5000
