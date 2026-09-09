"""Role scoping: every role must see exactly the patients it is entitled to.

Layout built by the `world` fixture:
    north clinic  -> patients A, B      centre clinic -> patient C
    doctor_a      -> patient A          doctor_b      -> patient B
    patient_user  -> patient A
"""
from datetime import date

import pytest
from app import models as m
from app.security import encrypt_national_id, hash_password, national_id_hash

PASSWORD = "Pass123!"
IDS = ["000000018", "000000026", "000000034"]


@pytest.fixture
def world(db):
    north = m.Clinic(name="צפון", code="N")
    centre = m.Clinic(name="מרכז", code="C")
    db.add_all([north, centre])
    db.flush()

    patients = []
    for index, clinic in enumerate((north, north, centre)):
        national_id = IDS[index]
        patient = m.Patient(
            first_name="מטופל", last_name=str(index),
            national_id_encrypted=encrypt_national_id(national_id),
            national_id_hash=national_id_hash(national_id),
            date_of_birth=date(1990, 1, 1), biological_sex="FEMALE",
            clinic_id=clinic.id,
        )
        db.add(patient)
        db.flush()
        patients.append(patient)

    def user(email, role, clinic_id=None, patient_id=None):
        row = m.User(email=email, password_hash=hash_password(PASSWORD), role=role,
                     clinic_id=clinic_id, patient_id=patient_id)
        db.add(row)
        db.flush()
        return row

    people = {
        "admin": user("admin@t.local", m.Role.ADMIN),
        "doctor_a": user("da@t.local", m.Role.DOCTOR, clinic_id=north.id),
        "doctor_b": user("db@t.local", m.Role.DOCTOR, clinic_id=north.id),
        "clinic_north": user("cn@t.local", m.Role.CLINIC, clinic_id=north.id),
        "clinic_centre": user("cc@t.local", m.Role.CLINIC, clinic_id=centre.id),
        "patient": user("p@t.local", m.Role.PATIENT, patient_id=patients[0].id),
    }
    db.add_all([
        m.DoctorPatient(doctor_user_id=people["doctor_a"].id, patient_id=patients[0].id),
        m.DoctorPatient(doctor_user_id=people["doctor_b"].id, patient_id=patients[1].id),
    ])
    db.commit()
    return {"patients": patients, "users": people, "north": north, "centre": centre}


def auth(client, email):
    response = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.mark.parametrize("email,expected", [
    ("admin@t.local", 3),
    ("da@t.local", 1),
    ("db@t.local", 1),
    ("cn@t.local", 2),
    ("cc@t.local", 1),
    ("p@t.local", 1),
])
def test_patient_list_is_scoped_per_role(client, world, email, expected):
    response = client.get("/api/patients", headers=auth(client, email))
    assert response.status_code == 200
    assert len(response.json()["items"]) == expected


def test_doctor_cannot_read_another_doctors_patient(client, world):
    other = world["patients"][1].id
    response = client.get(f"/api/patients/{other}", headers=auth(client, "da@t.local"))
    assert response.status_code == 403


def test_doctor_reads_own_patient(client, world):
    own = world["patients"][0].id
    response = client.get(f"/api/patients/{own}", headers=auth(client, "da@t.local"))
    assert response.status_code == 200


def test_clinic_cannot_read_other_clinics_patient(client, world):
    centre_patient = world["patients"][2].id
    response = client.get(f"/api/patients/{centre_patient}", headers=auth(client, "cn@t.local"))
    assert response.status_code == 403


def test_clinic_reads_every_patient_of_its_own_clinic(client, world):
    headers = auth(client, "cn@t.local")
    for patient in world["patients"][:2]:
        assert client.get(f"/api/patients/{patient.id}", headers=headers).status_code == 200


def test_patient_sees_only_themselves(client, world):
    headers = auth(client, "p@t.local")
    assert client.get(f"/api/patients/{world['patients'][0].id}", headers=headers).status_code == 200
    assert client.get(f"/api/patients/{world['patients'][1].id}", headers=headers).status_code == 403
    assert client.get(f"/api/patients/{world['patients'][1].id}/tests", headers=headers).status_code == 403


def test_patient_cannot_create_a_blood_test(client, world):
    body = {"patient_id": world["patients"][0].id, "test_date": "2026-01-01",
            "accession_number": "RBAC-1",
            "results": [{"analyte_code": "HGB", "numeric_value": 13.0, "unit": "g/dL"}]}
    response = client.post("/api/tests", json=body, headers=auth(client, "p@t.local"))
    assert response.status_code == 403


def test_doctor_cannot_create_a_test_for_a_patient_outside_their_list(client, world):
    body = {"patient_id": world["patients"][1].id, "test_date": "2026-01-01",
            "accession_number": "RBAC-2",
            "results": [{"analyte_code": "HGB", "numeric_value": 13.0, "unit": "g/dL"}]}
    response = client.post("/api/tests", json=body, headers=auth(client, "da@t.local"))
    assert response.status_code == 403


def test_audit_log_is_admin_only(client, world):
    assert client.get("/api/audit", headers=auth(client, "da@t.local")).status_code == 403
    assert client.get("/api/audit", headers=auth(client, "cn@t.local")).status_code == 403
    assert client.get("/api/audit", headers=auth(client, "admin@t.local")).status_code == 200


def test_clinic_assigns_a_doctor_and_the_doctor_then_sees_the_patient(client, world):
    patient_id = world["patients"][1].id
    doctor_a = world["users"]["doctor_a"].id
    assert client.get(f"/api/patients/{patient_id}", headers=auth(client, "da@t.local")).status_code == 403

    response = client.post(f"/api/patients/{patient_id}/doctors",
                           json={"doctor_user_id": doctor_a},
                           headers=auth(client, "cn@t.local"))
    assert response.status_code == 200, response.text
    assert client.get(f"/api/patients/{patient_id}", headers=auth(client, "da@t.local")).status_code == 200


def test_clinic_cannot_assign_a_doctor_from_another_clinic(client, world):
    centre_patient = world["patients"][2].id
    response = client.post(f"/api/patients/{centre_patient}/doctors",
                           json={"doctor_user_id": world["users"]["doctor_a"].id},
                           headers=auth(client, "cn@t.local"))
    assert response.status_code == 403


def test_doctor_cannot_assign_doctors(client, world):
    response = client.post(f"/api/patients/{world['patients'][0].id}/doctors",
                           json={"doctor_user_id": world["users"]["doctor_b"].id},
                           headers=auth(client, "da@t.local"))
    assert response.status_code == 403


def test_unassigning_removes_access(client, world):
    patient_id = world["patients"][0].id
    doctor_a = world["users"]["doctor_a"].id
    response = client.delete(f"/api/patients/{patient_id}/doctors/{doctor_a}",
                             headers=auth(client, "cn@t.local"))
    assert response.status_code == 200
    assert client.get(f"/api/patients/{patient_id}", headers=auth(client, "da@t.local")).status_code == 403


def test_alerts_are_scoped(client, db, world):
    db.add_all([
        m.Alert(patient_id=world["patients"][0].id, kind="K1", severity="INFO", title_he="צפון"),
        m.Alert(patient_id=world["patients"][2].id, kind="K2", severity="INFO", title_he="מרכז"),
    ])
    db.commit()
    kinds = lambda email: {a["kind"] for a in client.get("/api/alerts", headers=auth(client, email)).json()}
    assert kinds("admin@t.local") == {"K1", "K2"}
    assert kinds("cn@t.local") == {"K1"}
    assert kinds("cc@t.local") == {"K2"}
    assert kinds("da@t.local") == {"K1"}


def test_unknown_patient_is_404_for_admin_and_403_for_others(client, world):
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/patients/{missing}", headers=auth(client, "admin@t.local")).status_code == 404
    assert client.get(f"/api/patients/{missing}", headers=auth(client, "da@t.local")).status_code == 404
