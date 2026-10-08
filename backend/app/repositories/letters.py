"""app/repositories/letters.py

Supabase DB access repository for Family Letters (가족 편지함) domain.
Only contains raw CRUD database queries without business logic or permission checks.
"""

from datetime import datetime, timezone
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
# 0. Group & Helper Queries
# ==========================================


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


def get_group_member_user_ids(group_id: int) -> list[UUID]:
    """특정 그룹에 속한 모든 멤버의 user_id(UUID) 목록 조회."""
    client = _get_client()
    res = (
        client.table("group_members")
        .select("user_id")
        .eq("group_id", group_id)
        .execute()
    )
    return [UUID(row["user_id"]) for row in (res.data or []) if row.get("user_id")]


# ==========================================
# 1. Family Letters (가족 편지함 CRUD)
# ==========================================


def create_letter(payload: dict[str, Any]) -> dict[str, Any]:
    """편지 생성 (created_at 생략 -> PostgreSQL default now() 적용)."""
    client = _get_client()
    # created_at 명시적 생략 보장
    payload.pop("created_at", None)
    res = client.table("family_letters").insert(payload).execute()
    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create family letter",
        )
    return res.data[0]


def get_letter_by_id(letter_id: int) -> dict[str, Any] | None:
    """편지 단건 조회 (Soft Delete 된 편지 제외: deleted_at IS NULL)."""
    client = _get_client()
    res = (
        client.table("family_letters")
        .select("*")
        .eq("id", letter_id)
        .is_("deleted_at", "null")
        .execute()
    )
    return res.data[0] if res.data else None


def list_letters_by_group(
    group_id: int,
    user_id: UUID,
    box_type: str = "inbox",
) -> list[dict[str, Any]]:
    """그룹 단위 편지함 목록 조회 (수신함 / 발신함).
    
    - inbox: 해당 유저가 수신자(특정 1인 지정 OR 전체 null)이고, 본인이 발신자가 아닌 편지.
    - sent: 해당 유저가 발신자인 편지.
    - 모두 deleted_at IS NULL 인 편지만 조회.
    """
    client = _get_client()
    user_str = str(user_id)

    if box_type == "sent":
        res = (
            client.table("family_letters")
            .select("*")
            .eq("group_id", group_id)
            .eq("sender_user_id", user_str)
            .is_("deleted_at", "null")
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []

    # Inbox (수신함)
    # Postgrest or_ condition for receiver matching current user or null
    res = (
        client.table("family_letters")
        .select("*")
        .eq("group_id", group_id)
        .neq("sender_user_id", user_str)
        .or_(f"receiver_user_id.eq.{user_str},receiver_user_id.is.null")
        .is_("deleted_at", "null")
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def soft_delete_letter(letter_id: int) -> dict[str, Any] | None:
    """편지 Soft Delete (deleted_at 필드에 현재 시각 기록)."""
    client = _get_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    res = (
        client.table("family_letters")
        .update({"deleted_at": now_iso})
        .eq("id", letter_id)
        .execute()
    )
    return res.data[0] if res.data else None


# ==========================================
# 2. Letter Reads (편지 읽음 상태 CRUD)
# ==========================================


def create_letter_reads(reads_payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """편지 수신자들의 읽음 상태 행 일괄 생성 (Bulk Insert)."""
    if not reads_payload:
        return []
    client = _get_client()
    res = client.table("letter_reads").insert(reads_payload).execute()
    return res.data or []


def get_letter_read_status(letter_id: int, user_id: UUID) -> dict[str, Any] | None:
    """특정 수신자의 읽음 상태 조회."""
    client = _get_client()
    res = (
        client.table("letter_reads")
        .select("*")
        .eq("letter_id", letter_id)
        .eq("user_id", str(user_id))
        .execute()
    )
    return res.data[0] if res.data else None


def mark_letter_as_read(letter_id: int, user_id: UUID) -> dict[str, Any] | None:
    """편지 읽음 처리 (is_read=True, read_at=now())."""
    client = _get_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    res = (
        client.table("letter_reads")
        .update({"is_read": True, "read_at": now_iso})
        .eq("letter_id", letter_id)
        .eq("user_id", str(user_id))
        .execute()
    )
    return res.data[0] if res.data else None


def list_letter_reads(letter_id: int) -> list[dict[str, Any]]:
    """특정 편지의 모든 수신자 읽음 상태 목록 조회."""
    client = _get_client()
    res = (
        client.table("letter_reads")
        .select("*")
        .eq("letter_id", letter_id)
        .execute()
    )
    return res.data or []
