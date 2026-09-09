import enum, uuid
from datetime import date, datetime, timezone
from sqlalchemy import Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def utcnow(): return datetime.now(timezone.utc)
def uid(): return str(uuid.uuid4())
class Role(str, enum.Enum): PATIENT="PATIENT"; DOCTOR="DOCTOR"; CLINIC="CLINIC"; ADMIN="ADMIN"
class ResultStatus(str, enum.Enum): NORMAL="NORMAL"; LOW="LOW"; HIGH="HIGH"; CRITICAL_LOW="CRITICAL_LOW"; CRITICAL_HIGH="CRITICAL_HIGH"; UNKNOWN_REFERENCE="UNKNOWN_REFERENCE"; UNVERIFIED="UNVERIFIED"; INVALID="INVALID"
class Quality(str, enum.Enum): VERIFIED="VERIFIED"; REQUIRES_VERIFICATION="REQUIRES_VERIFICATION"; INVALID="INVALID"

class User(Base):
    __tablename__="users"; id: Mapped[int]=mapped_column(primary_key=True); email: Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash: Mapped[str]; role: Mapped[Role]=mapped_column(Enum(Role)); is_active: Mapped[bool]=mapped_column(Boolean,default=True); patient_id: Mapped[str|None]=mapped_column(ForeignKey("patients.id")); clinic_id: Mapped[int|None]=mapped_column(ForeignKey("clinics.id"),index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)
class Patient(Base):
    __tablename__="patients"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); first_name: Mapped[str]; last_name: Mapped[str]; national_id_encrypted: Mapped[str]; national_id_hash: Mapped[str]=mapped_column(unique=True,index=True); date_of_birth: Mapped[date]=mapped_column(Date); biological_sex: Mapped[str]; phone: Mapped[str|None]; email: Mapped[str|None]; clinic_id: Mapped[int|None]=mapped_column(ForeignKey("clinics.id"),index=True); demo: Mapped[bool]=mapped_column(Boolean,default=False); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow); tests=relationship("BloodTest",back_populates="patient",cascade="all, delete-orphan")
class Clinic(Base):
    __tablename__="clinics"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]; code: Mapped[str]=mapped_column(unique=True,index=True); city: Mapped[str|None]; active: Mapped[bool]=mapped_column(default=True)
class DoctorPatient(Base):
    """Assignment of a patient to a treating doctor. A doctor sees only these patients."""
    __tablename__="doctor_patients"; id: Mapped[int]=mapped_column(primary_key=True); doctor_user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True); patient_id: Mapped[str]=mapped_column(ForeignKey("patients.id"),index=True); assigned_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); assigned_by: Mapped[int|None]=mapped_column(ForeignKey("users.id")); __table_args__=(UniqueConstraint("doctor_user_id","patient_id",name="uq_doctor_patient"),)
class Laboratory(Base):
    __tablename__="laboratories"; id: Mapped[int]=mapped_column(primary_key=True); name: Mapped[str]; code: Mapped[str]=mapped_column(unique=True); country: Mapped[str]=mapped_column(default="IL"); active: Mapped[bool]=mapped_column(default=True)
class Analyte(Base):
    __tablename__="analytes"; id: Mapped[int]=mapped_column(primary_key=True); code: Mapped[str]=mapped_column(unique=True,index=True); display_name_he: Mapped[str]; display_name_en: Mapped[str]; category: Mapped[str]; description_he: Mapped[str]=mapped_column(Text); typical_unit: Mapped[str]; comparison_direction: Mapped[str]=mapped_column(default="RANGE"); active: Mapped[bool]=mapped_column(default=True); aliases: Mapped[list["AnalyteAlias"]]=relationship(cascade="all, delete-orphan")
class AnalyteAlias(Base):
    __tablename__="analyte_aliases"; id: Mapped[int]=mapped_column(primary_key=True); analyte_id: Mapped[int]=mapped_column(ForeignKey("analytes.id")); alias: Mapped[str]=mapped_column(index=True); __table_args__=(UniqueConstraint("alias",name="uq_alias"),)
class BloodTest(Base):
    __tablename__="blood_tests"; id: Mapped[str]=mapped_column(String(36),primary_key=True,default=uid); patient_id: Mapped[str]=mapped_column(ForeignKey("patients.id"),index=True); laboratory_id: Mapped[int]=mapped_column(ForeignKey("laboratories.id")); test_date: Mapped[date]=mapped_column(Date,index=True); accession_number: Mapped[str]=mapped_column(unique=True,index=True); source: Mapped[str]=mapped_column(default="MANUAL"); status: Mapped[str]=mapped_column(default="FINAL"); panel: Mapped[str|None]; notes: Mapped[str|None]=mapped_column(Text); fasting: Mapped[bool|None]; reason: Mapped[str|None]; created_by: Mapped[int|None]=mapped_column(ForeignKey("users.id")); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); patient=relationship("Patient",back_populates="tests"); results=relationship("TestResult",cascade="all, delete-orphan",lazy="selectin")
class TestResult(Base):
    __tablename__="test_results"; id: Mapped[int]=mapped_column(primary_key=True); blood_test_id: Mapped[str]=mapped_column(ForeignKey("blood_tests.id"),index=True); analyte_id: Mapped[int]=mapped_column(ForeignKey("analytes.id")); numeric_value: Mapped[float|None]; text_value: Mapped[str|None]; unit: Mapped[str]; reference_min: Mapped[float|None]; reference_max: Mapped[float|None]; critical_low: Mapped[float|None]; critical_high: Mapped[float|None]; lab_flag: Mapped[str|None]; normalized_value: Mapped[float|None]; normalized_unit: Mapped[str|None]; status: Mapped[ResultStatus]=mapped_column(Enum(ResultStatus),default=ResultStatus.UNKNOWN_REFERENCE); data_quality_status: Mapped[Quality]=mapped_column(Enum(Quality),default=Quality.VERIFIED); reference_source: Mapped[str]=mapped_column(default="LAB_SUPPLIED"); distance_from_range: Mapped[float|None]; analyte=relationship("Analyte"); __table_args__=(UniqueConstraint("blood_test_id","analyte_id",name="uq_test_analyte"),)
class ReferenceRange(Base):
    __tablename__="reference_ranges"; id: Mapped[int]=mapped_column(primary_key=True); analyte_id: Mapped[int]=mapped_column(ForeignKey("analytes.id")); laboratory_id: Mapped[int|None]=mapped_column(ForeignKey("laboratories.id")); sex: Mapped[str|None]; age_min: Mapped[int|None]; age_max: Mapped[int|None]; unit: Mapped[str]; min_value: Mapped[float]; max_value: Mapped[float]; valid_from: Mapped[date|None]; valid_to: Mapped[date|None]; source_reference: Mapped[str]; active: Mapped[bool]=mapped_column(default=True)
class CriticalThreshold(Base):
    __tablename__="critical_thresholds"; id: Mapped[int]=mapped_column(primary_key=True); analyte_id: Mapped[int]=mapped_column(ForeignKey("analytes.id")); laboratory_id: Mapped[int|None]=mapped_column(ForeignKey("laboratories.id")); unit: Mapped[str]; low_value: Mapped[float|None]; high_value: Mapped[float|None]; source_reference: Mapped[str]; active: Mapped[bool]=mapped_column(default=True)
class AnalysisRun(Base):
    __tablename__="analysis_runs"; id: Mapped[int]=mapped_column(primary_key=True); blood_test_id: Mapped[str]=mapped_column(ForeignKey("blood_tests.id"),index=True); algorithm_version: Mapped[str]; created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); summary: Mapped[dict]=mapped_column(JSON); quality_score: Mapped[float]
class AnalysisFinding(Base):
    __tablename__="analysis_findings"; id: Mapped[int]=mapped_column(primary_key=True); analysis_run_id: Mapped[int]=mapped_column(ForeignKey("analysis_runs.id")); analyte_id: Mapped[int|None]=mapped_column(ForeignKey("analytes.id")); finding_type: Mapped[str]; severity: Mapped[str]; message: Mapped[str]=mapped_column(Text); rationale: Mapped[str]=mapped_column(Text); previous_result_id: Mapped[int|None]=mapped_column(ForeignKey("test_results.id"))
class Recommendation(Base):
    __tablename__="recommendations"; id: Mapped[int]=mapped_column(primary_key=True); rule_code: Mapped[str]=mapped_column(unique=True); title_he: Mapped[str]; content_he: Mapped[str]=mapped_column(Text); severity: Mapped[str]; evidence_source: Mapped[str]; active: Mapped[bool]=mapped_column(default=True)
class AuditLog(Base):
    __tablename__="audit_logs"; id: Mapped[int]=mapped_column(primary_key=True); user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),index=True); action: Mapped[str]=mapped_column(index=True); entity_type: Mapped[str]; entity_id: Mapped[str|None]; timestamp: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True); metadata_sanitized: Mapped[dict]=mapped_column(JSON,default=dict)
class Alert(Base):
    __tablename__="alerts"; id: Mapped[int]=mapped_column(primary_key=True); patient_id: Mapped[str]=mapped_column(ForeignKey("patients.id"),index=True); blood_test_id: Mapped[str|None]=mapped_column(ForeignKey("blood_tests.id")); kind: Mapped[str]; severity: Mapped[str]; title_he: Mapped[str]; state: Mapped[str]=mapped_column(default="NEW"); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

Index("ix_results_test_status",TestResult.blood_test_id,TestResult.status)
