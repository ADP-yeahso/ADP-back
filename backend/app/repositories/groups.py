"""Supabase persistence for groups, memberships, and cheers."""

from datetime import date
from typing import Any

from fastapi import HTTPException, status

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


def ensure_user_profile(user_id: str) -> None:
    """Create the public profile row required by group_members' foreign key.

    Users are initially created in Supabase Auth. The current database migration
    has no Auth-to-public.users trigger, so create the matching profile lazily
    from the signup metadata before a group membership is inserted.
    """
    client = _client()
    existing = client.table("users").select("id").eq("id", user_id).execute()
    if existing.data:
        return

    try:
        auth_user = client.auth.admin.get_user_by_id(user_id).user
    except Exception as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "User profile could not be initialized",
        ) from exc

    metadata = getattr(auth_user, "user_metadata", None) or {}
    name = metadata.get("name")
    phone_number = metadata.get("phone_number")
    if not auth_user or not auth_user.email or not name or not phone_number:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A name and phone number are required before joining a group",
        )

    profile = {
        "id": user_id,
        "email": auth_user.email,
        "name": name,
        "phone_number": phone_number,
        "profile_image_url": metadata.get("profile_image_url"),
    }
    client.table("users").insert(profile).execute()


def create_group(data: dict) -> dict:
    return _one(_client().table("groups").insert(data).execute(), "Group was not saved")


def get_group(group_id: int) -> dict:
    result = _client().table("groups").select("*").eq("id", group_id).execute()
    return _one(result, "Group not found")


def list_groups(user_id: str) -> list[dict]:
    memberships = _client().table("group_members").select("group_id").eq("user_id", user_id)
    memberships = memberships.execute()
    group_ids = [row["group_id"] for row in (memberships.data or [])]
    if not group_ids:
        return []
    result = _client().table("groups").select("*").in_("id", group_ids)
    result = result.order("created_at", desc=True).execute()
    return result.data or []


def update_group(group_id: int, data: dict) -> dict:
    query = _client().table("groups").update(data).eq("id", group_id)
    return _one(query.execute(), "Group not found")


def is_member(group_id: int, user_id: str) -> bool:
    result = (
        _client()
        .table("group_members")
        .select("id")
        .eq("group_id", group_id)
        .eq("user_id", user_id)
        .execute()
    )
    return bool(result.data)


def create_membership(
    user_id: str, group_id: int, patients_nickname: str, patient_relation: str
) -> dict:
    data = {
        "user_id": user_id,
        "group_id": group_id,
        "patients_nickname": patients_nickname,
        "patient_relation": patient_relation,
    }
    result = _client().table("group_members").insert(data).execute()
    return _one(result, "Group membership was not saved")


def get_group_by_invite_code(invite_code: str) -> dict:
    query = _client().table("groups").select("*").eq("invite_code", invite_code)
    return _one(query.execute(), "Invite code not found")


def get_members(group_id: int) -> list[dict]:
    result = (
        _client()
        .table("group_members")
        .select("user_id, patients_nickname, patient_relation, users(name)")
        .eq("group_id", group_id)
        .execute()
    )
    members = []
    for row in result.data or []:
        user = row.pop("users", None) or {}
        members.append({**row, "name": user.get("name"), "joined_at": row.get("joined_at")})
    return members


def count_members(group_id: int) -> int:
    result = _client().table("group_members").select("id").eq("group_id", group_id).execute()
    return len(result.data or [])


def update_membership(group_id: int, user_id: str, data: dict) -> dict:
    query = _client().table("group_members").update(data).eq("group_id", group_id)
    query = query.eq("user_id", user_id)
    return _one(query.execute(), "Group membership not found")


def delete_membership(group_id: int, user_id: str) -> None:
    query = _client().table("group_members").delete().eq("group_id", group_id)
    query.eq("user_id", user_id).execute()


def has_cheered_today(group_id: int, sender_user_id: str, receiver_user_id: str) -> bool:
    result = (
        _client()
        .table("member_cheers")
        .select("id")
        .eq("group_id", group_id)
        .eq("sender_user_id", sender_user_id)
        .eq("receiver_user_id", receiver_user_id)
        .eq("cheer_date", date.today().isoformat())
        .execute()
    )
    return bool(result.data)


def create_cheer(group_id: int, sender_user_id: str, receiver_user_id: str) -> dict:
    data = {
        "group_id": group_id,
        "sender_user_id": sender_user_id,
        "receiver_user_id": receiver_user_id,
    }
    return _one(_client().table("member_cheers").insert(data).execute(), "Cheer was not saved")
