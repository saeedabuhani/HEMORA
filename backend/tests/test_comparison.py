"""Comparison, trend and import rules from the clinical specification."""
from datetime import date, timedelta

import pytest
from app import models as m
from app.services import (
    ExplanationService,
    ImportService,
    LongitudinalTrendService,
    PanelCompletenessService,
    TestComparisonEngine,
    UnitConversionService,
)

HGB_MIN, HGB_MAX = 12.0, 16.0


@pytest.fixture
def bench(db):
    """A patient with two dated blood tests ready to receive results."""
    patient = m.Patient(
        first_name="דמו", last_name="השוואה",
        national_id_encrypted="x", national_id_hash="hash-compare",
        date_of_birth=date(1990, 1, 1), biological_sex="FEMALE")
    lab = m.Laboratory(name="Demo", code="CMP-LAB")
    hgb = m.Analyte(code="HGB", display_name_he="המוגלובין", display_name_en="Hemoglobin",
                    category="CBC", description_he="חלבון נושא חמצן", typical_unit="g/dL")
    db.add_all([patient, lab, hgb])
    db.flush()

    def make_test(days_ago, accession):
        row = m.BloodTest(patient_id=patient.id, laboratory_id=lab.id,
                          test_date=date.today() - timedelta(days=days_ago),
                          accession_number=accession, panel="CBC", source="TEST")
        db.add(row)
        db.flush()
        return row

    previous, current = make_test(90, "CMP-PREV"), make_test(0, "CMP-CURR")

    def add(test, value, status, unit="g/dL", quality=m.Quality.VERIFIED,
            analyte=None, low=HGB_MIN, high=HGB_MAX):
        db.add(m.TestResult(
            blood_test_id=test.id, analyte_id=(analyte or hgb).id, numeric_value=value,
            unit=unit, normalized_value=value, normalized_unit=unit,
            reference_min=low, reference_max=high, status=status,
            data_quality_status=quality, reference_source="LAB_SUPPLIED"))
        db.flush()

    return {"db": db, "patient": patient, "lab": lab, "hgb": hgb,
            "previous": previous, "current": current, "add": add, "make_test": make_test}


def trend_of(bench, code="HGB"):
    bench["db"].refresh(bench["current"])
    bench["db"].refresh(bench["previous"])
    rows = TestComparisonEngine.compare(bench["current"], bench["previous"])
    return next(r for r in rows if r["code"] == code)


# ---------------------------------------------------------------- trends


def test_value_moving_closer_to_range_is_improved(bench):
    bench["add"](bench["previous"], 10.8, m.ResultStatus.LOW)
    bench["add"](bench["current"], 11.7, m.ResultStatus.LOW)
    row = trend_of(bench)
    assert row["trend"] == "IMPROVED"
    assert row["delta"] == pytest.approx(0.9)


def test_value_moving_away_from_range_is_worsened(bench):
    bench["add"](bench["previous"], 11.5, m.ResultStatus.LOW)
    bench["add"](bench["current"], 10.2, m.ResultStatus.LOW)
    assert trend_of(bench)["trend"] == "WORSENED"


def test_normal_to_abnormal_is_a_new_abnormality(bench):
    bench["add"](bench["previous"], 13.5, m.ResultStatus.NORMAL)
    bench["add"](bench["current"], 11.0, m.ResultStatus.LOW)
    assert trend_of(bench)["trend"] == "NEW_ABNORMALITY"


def test_abnormal_to_normal_returned_to_range(bench):
    bench["add"](bench["previous"], 11.0, m.ResultStatus.LOW)
    bench["add"](bench["current"], 12.5, m.ResultStatus.NORMAL)
    assert trend_of(bench)["trend"] == "RETURNED_TO_RANGE"


def test_two_values_inside_the_range_are_stable(bench):
    bench["add"](bench["previous"], 13.0, m.ResultStatus.NORMAL)
    bench["add"](bench["current"], 13.2, m.ResultStatus.NORMAL)
    assert trend_of(bench)["trend"] == "STABLE"


def test_identical_abnormal_values_are_still_abnormal(bench):
    bench["add"](bench["previous"], 11.0, m.ResultStatus.LOW)
    bench["add"](bench["current"], 11.0, m.ResultStatus.LOW)
    assert trend_of(bench)["trend"] == "STILL_ABNORMAL"


# ------------------------------------------------- missing and incomparable


def test_result_missing_from_the_current_test(bench):
    bench["add"](bench["previous"], 13.0, m.ResultStatus.NORMAL)
    row = trend_of(bench)
    assert row["trend"] == "MISSING_CURRENT"
    assert "אין תוצאה בבדיקה הנוכחית" in row["message"]


def test_result_absent_from_the_previous_test_is_a_new_parameter(bench):
    bench["add"](bench["current"], 13.0, m.ResultStatus.NORMAL)
    row = trend_of(bench)
    assert row["trend"] == "NEW_PARAMETER"
    assert "מדד חדש" in row["message"]


def test_incompatible_units_are_never_compared(bench):
    bench["add"](bench["previous"], 130.0, m.ResultStatus.NORMAL, unit="g/L")
    bench["add"](bench["current"], 13.0, m.ResultStatus.NORMAL, unit="g/dL")
    row = trend_of(bench)
    assert row["trend"] == "NOT_COMPARABLE"
    assert "יחידות המדידה" in row["message"]


def test_unverified_data_is_not_compared(bench):
    bench["add"](bench["previous"], 13.0, m.ResultStatus.NORMAL)
    bench["add"](bench["current"], 11.0, m.ResultStatus.UNVERIFIED,
                 quality=m.Quality.REQUIRES_VERIFICATION)
    assert trend_of(bench)["trend"] == "NOT_COMPARABLE"


def test_missing_reference_range_is_not_compared(bench):
    bench["add"](bench["previous"], 13.0, m.ResultStatus.NORMAL)
    bench["add"](bench["current"], 11.0, m.ResultStatus.UNKNOWN_REFERENCE, low=None, high=None)
    assert trend_of(bench)["trend"] == "NOT_COMPARABLE"


# ---------------------------------------------------------------- longitudinal


def test_longitudinal_trend_counts_consecutive_abnormal_results(bench):
    db = bench["db"]
    third = bench["make_test"](180, "CMP-OLD")
    bench["add"](third, 10.5, m.ResultStatus.LOW)
    bench["add"](bench["previous"], 11.0, m.ResultStatus.LOW)
    bench["add"](bench["current"], 11.5, m.ResultStatus.LOW)
    for row in (third, bench["previous"], bench["current"]):
        db.refresh(row)
    trend = LongitudinalTrendService.calculate([third, bench["previous"], bench["current"]], "HGB")
    assert len(trend["points"]) == 3
    assert trend["direction"] == "UP"
    assert trend["consecutive_abnormal"] == 3
    assert trend["most_recent_normal"] is None


# ---------------------------------------------------------------- explanation


def test_explanation_is_built_from_the_stored_values(bench):
    db = bench["db"]
    bench["add"](bench["previous"], 10.8, m.ResultStatus.LOW)
    bench["add"](bench["current"], 11.7, m.ResultStatus.LOW)
    db.refresh(bench["current"])
    result = bench["current"].results[0]

    explanation = ExplanationService.build(db, bench["current"], result)

    assert explanation["status"] == "LOW"
    assert "11.7" in explanation["classification_reason"]
    assert "12.0" in explanation["classification_reason"]
    assert explanation["comparison"]["trend"] == "IMPROVED"
    assert explanation["comparison"]["previous_value"] == pytest.approx(10.8)
    assert "התקרב לטווח" in explanation["comparison"]["rule_he"]
    assert explanation["algorithm_version"] == "HEMORA-CLINICAL-1.0.0"
    # the disclaimer must always travel with the finding
    assert any("אינה קובעת אבחנה" in line for line in explanation["limitations"])


def test_explanation_flags_a_general_demo_range(bench):
    db = bench["db"]
    bench["add"](bench["current"], 11.7, m.ResultStatus.LOW)
    db.refresh(bench["current"])
    result = bench["current"].results[0]
    result.reference_source = "DEMO_GENERAL"
    db.flush()

    explanation = ExplanationService.build(db, bench["current"], result)
    assert explanation["reference"]["source_he"] == "טווח כללי לצורכי הדגמה בלבד"
    assert any("להעדיף את טווח הייחוס" in line for line in explanation["limitations"])


# ---------------------------------------------------------------- other rules


def test_unsupported_unit_conversion_returns_nothing():
    assert UnitConversionService.convert(13.0, "g/dL", "mmol/L", "HGB") is None
    assert UnitConversionService.convert(130.0, "g/L", "g/dL", "HGB") == pytest.approx(13.0)


def test_panel_completeness_separates_missing_from_abnormal():
    missing = PanelCompletenessService.evaluate("CBC", ["WBC", "RBC", "HCT", "MCV", "PLT"])
    assert "HGB" in missing
    assert PanelCompletenessService.evaluate("CBC", []) != []
    # an analyte that was reported is never listed as missing
    assert "WBC" not in missing


def test_import_marks_an_invalid_value_for_verification():
    csv = "analyte,value,unit\nHGB,13.2,g/dL\nWBC,not-a-number,10^3/uL\n".encode("utf-8")
    preview = ImportService.preview_csv(csv)
    assert preview["requires_confirmation"] is True
    assert preview["errors"][0]["code"] == "INVALID_VALUE"
    bad = next(r for r in preview["rows"] if r["analyte_code"] == "WBC")
    assert bad["numeric_value"] is None and bad["requires_verification"] is True


def test_import_resolves_analyte_aliases():
    csv = "analyte,value,unit\nHemoglobin,13.2,g/dL\nהמוגלובין,13.4,g/dL\n".encode("utf-8")
    rows = ImportService.preview_csv(csv)["rows"]
    assert [r["analyte_code"] for r in rows] == ["HGB", "HGB"]
