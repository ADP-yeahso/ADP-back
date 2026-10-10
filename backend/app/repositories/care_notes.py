"""Supabase DB access repository for Care Notebook (돌봄수첩) domain.

Only contains raw CRUD database queries without business logic or permission checks.
"""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.db.supabase import get_supabase_client


def _get_client():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase client is not configured",
        )
    return client


# ==========================================
# 0. Helper / Permission Validation Queries
# ==========================================


def get_patient_by_id(patient_id: int) -> dict[str, Any] | None:
    """환자 단건 조회 (소속 group_id 확인용)."""
    client = _get_client()
    res = client.table("patients").select("*").eq("id", patient_id).execute()
    return res.data[0] if res.data else None


def is_user_in_group(user_id: UUID, group_id: int) -> bool:
    """사용자가 특정 그룹의 멤버인지 여부 확인."""
    client = _get_client()
    res = (
        client.table("group_members")
        .select("id")
        .eq("user_id", str(user_id))
        .eq("group_id", group_id)
        .execute()
    )
    return len(res.data) > 0


# ==========================================
# 1. Daily Conditions (오늘의 환자 상태)
# ==========================================


def create_daily_condition(payload: dict[str, Any]) -> dict[str, Any]:
    """오늘 상태 생성."""
    client = _get_client()
    res = client.table("patient_daily_conditions").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create daily condition record",
        )
    return res.data[0]


def get_daily_condition_by_id(condition_id: int) -> dict[str, Any] | None:
    """오늘 상태 단건 조회."""
    client = _get_client()
    res = client.table("patient_daily_conditions").select("*").eq("id", condition_id).execute()
    return res.data[0] if res.data else None


def list_daily_conditions(
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """오늘 상태 목록 조회 (날짜 범위 필터 지원)."""
    client = _get_client()
    query = client.table("patient_daily_conditions").select("*").eq("patient_id", patient_id)
    if start_date:
        query = query.gte("record_date", start_date.isoformat())
    if end_date:
        query = query.lte("record_date", end_date.isoformat())
    res = query.order("record_date", desc=True).execute()
    return res.data or []


def update_daily_condition(condition_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """오늘 상태 수정."""
    client = _get_client()
    res = client.table("patient_daily_conditions").update(payload).eq("id", condition_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update daily condition record",
        )
    return res.data[0]


def delete_daily_condition(condition_id: int) -> None:
    """오늘 상태 삭제."""
    client = _get_client()
    client.table("patient_daily_conditions").delete().eq("id", condition_id).execute()


# ==========================================
# 2. Behavior Logs (행동 및 증상 기록)
# ==========================================


def create_behavior_log(payload: dict[str, Any]) -> dict[str, Any]:
    """행동/증상 기록 생성."""
    client = _get_client()
    res = client.table("patient_behavior_logs").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create behavior log",
        )
    return res.data[0]


def get_behavior_log_by_id(log_id: int) -> dict[str, Any] | None:
    """행동/증상 기록 단건 조회."""
    client = _get_client()
    res = client.table("patient_behavior_logs").select("*").eq("id", log_id).execute()
    return res.data[0] if res.data else None


def list_behavior_logs(
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """행동/증상 기록 목록 조회."""
    client = _get_client()
    query = client.table("patient_behavior_logs").select("*").eq("patient_id", patient_id)
    if start_date:
        query = query.gte("occurred_at", start_date.isoformat())
    if end_date:
        query = query.lte("occurred_at", f"{end_date.isoformat()}T23:59:59")
    res = query.order("occurred_at", desc=True).execute()
    return res.data or []


def update_behavior_log(log_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """행동/증상 기록 수정."""
    client = _get_client()
    res = client.table("patient_behavior_logs").update(payload).eq("id", log_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update behavior log",
        )
    return res.data[0]


def delete_behavior_log(log_id: int) -> None:
    """행동/증상 기록 삭제."""
    client = _get_client()
    client.table("patient_behavior_logs").delete().eq("id", log_id).execute()


# ==========================================
# 3. Medications (복약 목록)
# ==========================================


def create_medication(payload: dict[str, Any]) -> dict[str, Any]:
    """복약 항목 생성."""
    client = _get_client()
    res = client.table("medications").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create medication",
        )
    return res.data[0]


def get_medication_by_id(medication_id: int) -> dict[str, Any] | None:
    """복약 항목 단건 조회."""
    client = _get_client()
    res = client.table("medications").select("*").eq("id", medication_id).execute()
    return res.data[0] if res.data else None


def list_medications(patient_id: int, is_active: bool | None = None) -> list[dict[str, Any]]:
    """복약 항목 목록 조회 (is_active 필터 지원)."""
    client = _get_client()
    query = client.table("medications").select("*").eq("patient_id", patient_id)
    if is_active is not None:
        query = query.eq("is_active", is_active)
    res = query.order("created_at", desc=True).execute()
    return res.data or []


def update_medication(medication_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """복약 항목 수정."""
    client = _get_client()
    res = client.table("medications").update(payload).eq("id", medication_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update medication",
        )
    return res.data[0]


def delete_medication(medication_id: int) -> None:
    """복약 항목 삭제."""
    client = _get_client()
    client.table("medications").delete().eq("id", medication_id).execute()


# ==========================================
# 4. Medication Intake Logs (일별 복용 여부)
# ==========================================


def create_medication_intake_log(payload: dict[str, Any]) -> dict[str, Any]:
    """일별 복용 여부 기록 생성."""
    client = _get_client()
    res = client.table("medication_intake_logs").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create medication intake log",
        )
    return res.data[0]


def get_medication_intake_log_by_id(log_id: int) -> dict[str, Any] | None:
    """일별 복용 여부 단건 조회."""
    client = _get_client()
    res = client.table("medication_intake_logs").select("*").eq("id", log_id).execute()
    return res.data[0] if res.data else None


def get_medication_intake_log_by_medication_and_date(
    medication_id: int, log_date: date
) -> dict[str, Any] | None:
    """(medication_id, log_date) 기준 조회."""
    client = _get_client()
    res = (
        client.table("medication_intake_logs")
        .select("*")
        .eq("medication_id", medication_id)
        .eq("log_date", log_date.isoformat())
        .execute()
    )
    return res.data[0] if res.data else None


def list_medication_intake_logs(
    medication_ids: list[int],
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """여러 복약 항목에 대한 일별 복용 기록 목록 조회."""
    if not medication_ids:
        return []
    client = _get_client()
    query = client.table("medication_intake_logs").select("*").in_("medication_id", medication_ids)
    if start_date:
        query = query.gte("log_date", start_date.isoformat())
    if end_date:
        query = query.lte("log_date", end_date.isoformat())
    res = query.order("log_date", desc=True).execute()
    return res.data or []


def update_medication_intake_log(log_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """일별 복용 여부 수정."""
    client = _get_client()
    res = client.table("medication_intake_logs").update(payload).eq("id", log_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update medication intake log",
        )
    return res.data[0]


def delete_medication_intake_log(log_id: int) -> None:
    """일별 복용 여부 삭제."""
    client = _get_client()
    client.table("medication_intake_logs").delete().eq("id", log_id).execute()


# ==========================================
# 5. Hospital Visits (병원 및 진료 기록)
# ==========================================


def create_hospital_visit(payload: dict[str, Any]) -> dict[str, Any]:
    """병원 진료 기록 생성."""
    client = _get_client()
    res = client.table("hospital_visits").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create hospital visit record",
        )
    return res.data[0]


def get_hospital_visit_by_id(visit_id: int) -> dict[str, Any] | None:
    """병원 진료 기록 단건 조회."""
    client = _get_client()
    res = client.table("hospital_visits").select("*").eq("id", visit_id).execute()
    return res.data[0] if res.data else None


def list_hospital_visits(
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """병원 진료 기록 목록 조회."""
    client = _get_client()
    query = client.table("hospital_visits").select("*").eq("patient_id", patient_id)
    if start_date:
        query = query.gte("visit_date", start_date.isoformat())
    if end_date:
        query = query.lte("visit_date", end_date.isoformat())
    res = query.order("visit_date", desc=True).execute()
    return res.data or []


def update_hospital_visit(visit_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """병원 진료 기록 수정."""
    client = _get_client()
    res = client.table("hospital_visits").update(payload).eq("id", visit_id).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update hospital visit record",
        )
    return res.data[0]


def delete_hospital_visit(visit_id: int) -> None:
    """병원 진료 기록 삭제."""
    client = _get_client()
    client.table("hospital_visits").delete().eq("id", visit_id).execute()
