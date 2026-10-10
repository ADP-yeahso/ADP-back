"""Patient persistence."""

from typing import Any

from fastapi import HTTPException, status
from supabase import Client

from app.db.supabase import get_supabase_client


def _client():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase is not configured")
    return client


def _one(result: Any, detail: str) -> dict:
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return result.data[0] if isinstance(result.data, list) else result.data


def check_patient_access(client: Client, patient_id: int, user_id: str) -> bool:
    """Return whether the user belongs to the group that owns the patient."""
    patient_result = (
        client.table("patients").select("group_id").eq("id", patient_id).execute()
    )
    patient_rows = patient_result.data or []
    if not patient_rows:
        return False

    group_id = patient_rows[0]["group_id"]
    member_result = (
        client.table("group_members")
        .select("id")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(member_result.data)


def get_patient(patient_id: int) -> dict:
    result = _client().table("patients").select("*").eq("id", patient_id).execute()
    return _one(result, "Patient not found")


def get_patient_by_group_id(group_id: int) -> dict | None:
    result = _client().table("patients").select("*").eq("group_id", group_id).execute()
    if not result.data:
        return None
    return result.data[0]


def create_patient(group_id: int, data: dict) -> dict:
    result = _client().table("patients").insert({"group_id": group_id, **data}).execute()
    return _one(result, "Patient was not saved")


def update_patient(patient_id: int, data: dict) -> dict:
    result = _client().table("patients").update(data).eq("id", patient_id).execute()
    return _one(result, "Patient not found")
