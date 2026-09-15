"""Patient use cases."""

from fastapi import HTTPException, status

from app.repositories import patients as repository
from app.services import groups


def create_patient(user_id: str, group_id: int, data: dict) -> dict:
    groups.require_member(user_id, group_id)
    if repository.get_patient_by_group_id(group_id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A patient is already registered for this group")
    return repository.create_patient(group_id, data)


def get_patient(user_id: str, patient_id: int) -> dict:
    patient = repository.get_patient(patient_id)
    groups.require_member(user_id, patient["group_id"])
    return patient


def update_patient(user_id: str, patient_id: int, data: dict) -> dict:
    patient = repository.get_patient(patient_id)
    groups.require_member(user_id, patient["group_id"])
    return repository.update_patient(patient_id, data)
