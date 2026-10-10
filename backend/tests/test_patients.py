from datetime import date

import pytest
from fastapi import HTTPException

from app.services import patients
from app.schemas.patients import PatientCreate, PatientUpdate


def test_patient_payloads_serialize_dates_for_supabase() -> None:
    created = PatientCreate(
        patient_name="김환자", patient_birth_date=date(1940, 1, 1), gender="female"
    )
    updated = PatientUpdate(diagnosis_date=date(2020, 1, 1))

    assert created.model_dump(mode="json")["patient_birth_date"] == "1940-01-01"
    assert updated.model_dump(exclude_unset=True, mode="json")["diagnosis_date"] == "2020-01-01"


def test_create_patient_requires_group_membership(monkeypatch) -> None:
    monkeypatch.setattr(
        patients.groups.repository, "get_group", lambda group_id: {"id": group_id}
    )
    monkeypatch.setattr(patients.groups.repository, "is_member", lambda group_id, user_id: False)

    with pytest.raises(HTTPException) as exc_info:
        patients.create_patient("user-1", 7, {})

    assert exc_info.value.status_code == 403


def test_create_patient_rejects_second_patient(monkeypatch) -> None:
    monkeypatch.setattr(
        patients.groups.repository, "get_group", lambda group_id: {"id": group_id}
    )
    monkeypatch.setattr(patients.groups.repository, "is_member", lambda group_id, user_id: True)
    monkeypatch.setattr(
        patients.repository, "get_patient_by_group_id", lambda group_id: {"id": 3}
    )

    with pytest.raises(HTTPException) as exc_info:
        patients.create_patient("user-1", 7, {})

    assert exc_info.value.status_code == 409


def test_patient_read_and_update_require_membership(monkeypatch) -> None:
    patient = {
        "id": 3,
        "group_id": 7,
        "patient_name": "김환자",
        "patient_birth_date": date(1940, 1, 1),
        "gender": "female",
    }
    monkeypatch.setattr(patients.repository, "get_patient", lambda patient_id: patient)
    monkeypatch.setattr(
        patients.groups.repository, "get_group", lambda group_id: {"id": group_id}
    )
    monkeypatch.setattr(patients.groups.repository, "is_member", lambda group_id, user_id: True)
    monkeypatch.setattr(
        patients.repository,
        "update_patient",
        lambda patient_id, data: {**patient, **data},
    )

    assert patients.get_patient("user-1", 3) == patient
    assert patients.update_patient("user-1", 3, {"memo": "주의"})["memo"] == "주의"
