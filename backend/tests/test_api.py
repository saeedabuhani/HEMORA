from datetime import date, timedelta

import pytest
from sqlalchemy import select
from app import models as m
from app.security import hash_password


def test_authentication(client, users):
    response = client.post('/api/auth/login', json={'email': 'admin@test.local', 'password': 'Pass123!'})
    assert response.status_code == 200 and response.json()['role'] == 'ADMIN'


def test_authorization(client, users):
    token = client.post('/api/auth/login', json={'email': 'patient@test.local', 'password': 'Pass123!'}).json()['access_token']
    response = client.get('/api/audit', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 403


def test_invalid_login(client, users):
    assert client.post('/api/auth/login', json={'email': 'admin@test.local', 'password': 'wrong'}).status_code == 401


def test_request_without_a_token_is_rejected(client, users):
    assert client.get('/api/patients').status_code == 401


def test_a_tampered_token_is_rejected(client, users):
    assert client.get('/api/patients', headers={'Authorization': 'Bearer not.a.token'}).status_code == 401


def test_a_refresh_token_cannot_be_used_as_an_access_token(client, users):
    tokens = client.post('/api/auth/login', json={'email': 'admin@test.local', 'password': 'Pass123!'}).json()
    response = client.get('/api/patients', headers={'Authorization': 'Bearer ' + tokens['refresh_token']})
    assert response.status_code == 401


# ---------------------------------------------------------------- patients


@pytest.fixture
def admin(client, db):
    clinic = m.Clinic(name="מרפאה", code="API-C")
    db.add(clinic)
    db.flush()
    db.add(m.User(email="a@api.local", password_hash=hash_password("Pass123!"), role=m.Role.ADMIN))
    db.commit()
    token = client.post('/api/auth/login', json={'email': 'a@api.local', 'password': 'Pass123!'}).json()['access_token']
    return {"headers": {'Authorization': f'Bearer {token}'}, "clinic": clinic}


def new_patient_body(clinic_id, national_id="000000018"):
    return {"first_name": "נועה", "last_name": "לוי", "national_id": national_id,
            "date_of_birth": "1990-05-01", "biological_sex": "FEMALE", "clinic_id": clinic_id}


def test_creating_a_patient_stores_the_id_masked(client, admin):
    response = client.post('/api/patients', json=new_patient_body(admin["clinic"].id), headers=admin["headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["masked_national_id"].startswith("*") and body["masked_national_id"].endswith("18")
    assert "national_id" not in body


def test_an_invalid_israeli_id_is_refused(client, admin):
    body = new_patient_body(admin["clinic"].id, national_id="123456789")
    response = client.post('/api/patients', json=body, headers=admin["headers"])
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "INVALID_NATIONAL_ID"


def test_a_duplicate_patient_is_refused(client, admin):
    body = new_patient_body(admin["clinic"].id)
    assert client.post('/api/patients', json=body, headers=admin["headers"]).status_code == 200
    second = client.post('/api/patients', json=body, headers=admin["headers"])
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "DUPLICATE_PATIENT"


def test_a_patient_must_belong_to_an_existing_clinic(client, admin):
    response = client.post('/api/patients', json=new_patient_body(9999), headers=admin["headers"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_CLINIC"


# ---------------------------------------------------------------- blood tests


@pytest.fixture
def ready(client, db, admin):
    db.add_all([
        m.Laboratory(name="Lab", code="API-LAB"),
        m.Analyte(code="HGB", display_name_he="המוגלובין", display_name_en="Hemoglobin",
                  category="CBC", description_he="חלבון", typical_unit="g/dL"),
    ])
    db.commit()
    patient = client.post('/api/patients', json=new_patient_body(admin["clinic"].id), headers=admin["headers"]).json()
    lab_id = db.scalar(select(m.Laboratory.id).where(m.Laboratory.code == "API-LAB"))
    return {"headers": admin["headers"], "patient_id": patient["id"], "laboratory_id": lab_id}


def blood_test_body(ready, **overrides):
    body = {"patient_id": ready["patient_id"], "laboratory_id": ready["laboratory_id"],
            "test_date": date.today().isoformat(), "accession_number": "API-1", "panel": "CBC",
            "results": [{"analyte_code": "HGB", "numeric_value": 13.2, "unit": "g/dL",
                         "reference_min": 12, "reference_max": 16}]}
    body.update(overrides)
    return body


def test_creating_a_blood_test_runs_the_analysis(client, ready):
    response = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"])
    assert response.status_code == 200, response.text
    test_id = response.json()["id"]
    analysis = client.get(f'/api/tests/{test_id}/analysis', headers=ready["headers"])
    assert analysis.status_code == 200
    assert analysis.json()["algorithm_version"] == "HEMORA-CLINICAL-1.0.0"
    assert analysis.json()["results"][0]["status"] == "NORMAL"


def test_the_first_test_has_nothing_to_compare_against(client, ready):
    test_id = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"]).json()["id"]
    comparison = client.get(f'/api/tests/{test_id}/comparison', headers=ready["headers"]).json()
    assert comparison["previous_test"] is None
    assert "הבדיקה הראשונה" in comparison["message"]


def test_a_future_test_date_is_refused(client, ready):
    future = (date.today() + timedelta(days=1)).isoformat()
    response = client.post('/api/tests', json=blood_test_body(ready, test_date=future), headers=ready["headers"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "FUTURE_DATE"


def test_a_duplicate_accession_number_is_refused(client, ready):
    assert client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"]).status_code == 200
    second = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"])
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "DUPLICATE_TEST"


def test_an_unknown_analyte_is_refused(client, ready):
    body = blood_test_body(ready, accession_number="API-2",
                     results=[{"analyte_code": "NOPE", "numeric_value": 1.0, "unit": "x"}])
    response = client.post('/api/tests', json=body, headers=ready["headers"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNKNOWN_ANALYTE"


def test_the_same_analyte_twice_is_refused(client, ready):
    result = {"analyte_code": "HGB", "numeric_value": 13.2, "unit": "g/dL"}
    body = blood_test_body(ready, accession_number="API-3", results=[result, dict(result)])
    response = client.post('/api/tests', json=body, headers=ready["headers"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DUPLICATE_ANALYTE"


def test_an_inverted_reference_range_is_refused(client, ready):
    body = blood_test_body(ready, accession_number="API-4",
                     results=[{"analyte_code": "HGB", "numeric_value": 13.2, "unit": "g/dL",
                               "reference_min": 16, "reference_max": 12}])
    assert client.post('/api/tests', json=body, headers=ready["headers"]).status_code == 422


def test_the_explanation_endpoint_returns_the_reasoning(client, ready):
    test_id = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"]).json()["id"]
    detail = client.get(f'/api/tests/{test_id}', headers=ready["headers"]).json()
    result_id = detail["results"][0]["id"]
    explanation = client.get(f'/api/tests/{test_id}/results/{result_id}/explanation',
                             headers=ready["headers"])
    assert explanation.status_code == 200
    body = explanation.json()
    assert body["analyte"]["code"] == "HGB"
    assert body["status"] == "NORMAL"
    assert body["classification_reason"]
    assert body["limitations"]


def test_the_report_downloads_as_a_pdf(client, ready):
    test_id = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"]).json()["id"]
    response = client.get(f'/api/reports/{test_id}.pdf', headers=ready["headers"])
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


def test_downloading_a_report_is_written_to_the_audit_log(client, ready):
    test_id = client.post('/api/tests', json=blood_test_body(ready), headers=ready["headers"]).json()["id"]
    client.get(f'/api/reports/{test_id}.csv', headers=ready["headers"])
    actions = {row["action"] for row in client.get('/api/audit', headers=ready["headers"]).json()}
    assert {"LOGIN", "PATIENT_CREATED", "BLOOD_TEST_CREATED", "REPORT_DOWNLOADED"} <= actions


def test_the_audit_log_never_stores_a_national_id(client, ready):
    rows = client.get('/api/audit', headers=ready["headers"]).json()
    serialised = str(rows)
    assert "000000018" not in serialised
    assert "national_id" not in serialised


# ---------------------------------------------------------------- patient accounts


def account_body(clinic_id, email="noa@example.local"):
    body = new_patient_body(clinic_id)
    body.update({"email": email, "create_account": True})
    return body


def test_a_patient_account_is_created_and_can_sign_in(client, admin):
    response = client.post('/api/patients', json=account_body(admin["clinic"].id), headers=admin["headers"])
    assert response.status_code == 200, response.text
    account = response.json()["account"]
    assert account["email"] == "noa@example.local"

    login = client.post('/api/auth/login',
                        json={"email": account["email"], "password": account["temporary_password"]})
    assert login.status_code == 200
    assert login.json()["role"] == "PATIENT"


def test_the_new_account_sees_only_its_own_record(client, admin):
    created = client.post('/api/patients', json=account_body(admin["clinic"].id), headers=admin["headers"]).json()
    other = new_patient_body(admin["clinic"].id, national_id="000000026")
    other_id = client.post('/api/patients', json=other, headers=admin["headers"]).json()["id"]

    token = client.post('/api/auth/login', json={
        "email": created["account"]["email"],
        "password": created["account"]["temporary_password"]}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    listing = client.get('/api/patients', headers=headers).json()
    assert [p["id"] for p in listing["items"]] == [created["id"]]
    assert client.get(f'/api/patients/{other_id}', headers=headers).status_code == 403


def test_no_account_is_created_unless_asked_for(client, admin):
    body = new_patient_body(admin["clinic"].id)
    body["email"] = "quiet@example.local"
    response = client.post('/api/patients', json=body, headers=admin["headers"])
    assert response.status_code == 200
    assert "account" not in response.json()


def test_an_account_requires_an_email(client, admin):
    body = new_patient_body(admin["clinic"].id)
    body["create_account"] = True
    response = client.post('/api/patients', json=body, headers=admin["headers"])
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "EMAIL_REQUIRED"


def test_the_temporary_password_never_reaches_the_audit_log(client, admin):
    created = client.post('/api/patients', json=account_body(admin["clinic"].id), headers=admin["headers"]).json()
    password = created["account"]["temporary_password"]
    rows = str(client.get('/api/audit', headers=admin["headers"]).json())
    assert password not in rows
    assert "PATIENT_ACCOUNT_CREATED" in rows
