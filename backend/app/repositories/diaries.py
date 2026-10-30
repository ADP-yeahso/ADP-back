"""Supabase persistence for emotion diaries."""

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status
from postgrest.exceptions import APIError

from app.db.supabase import get_supabase_client


def _client():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase is not configured")
    return client


def _one(result: Any, detail: str = "Diary not found") -> dict:
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return result.data[0] if isinstance(result.data, list) else result.data


def get_diary(diary_id: int, user_id: str) -> dict:
    query = _client().table("diaries").select("*").eq("id", diary_id).eq("user_id", user_id)
    return _one(query.is_("deleted_at", "null").execute())


def create_diary(user_id: str, data: dict) -> dict:
    return _one(_client().table("diaries").insert({"user_id": user_id, **data}).execute(), "Diary was not saved")


def list_diaries(user_id: str, group_id: int | None, page: int, size: int) -> list[dict]:
    query = _client().table("diaries").select("*").eq("user_id", user_id).is_("deleted_at", "null")
    if group_id is not None:
        query = query.eq("group_id", group_id)
    result = query.order("record_date", desc=True).range((page - 1) * size, page * size - 1).execute()
    return result.data or []


def update_diary(diary_id: int, user_id: str, data: dict) -> dict:
    query = _client().table("diaries").update(data).eq("id", diary_id).eq("user_id", user_id)
    return _one(query.is_("deleted_at", "null").execute())


def soft_delete_diary(diary_id: int, user_id: str) -> None:
    data = {"deleted_at": datetime.now().astimezone().isoformat()}
    query = _client().table("diaries").update(data).eq("id", diary_id).eq("user_id", user_id)
    _one(query.is_("deleted_at", "null").execute())


def get_emotion(code: str) -> dict:
    return _one(_client().table("emotions").select("*").eq("emotion", code).execute(), "Emotion not found")


def get_emotion_by_id(emotion_id: int) -> dict:
    return _one(_client().table("emotions").select("*").eq("id", emotion_id).execute(), "Emotion not found")


def get_emotion_tags(emotion_ids: list[int]) -> list[dict]:
    result = _client().table("emotion_tags").select("*").in_("parent_emotion_id", emotion_ids).eq("is_active", True).order("display_order").execute()
    return result.data or []


def get_selected_tags(diary_id: int) -> list[dict]:
    result = _client().table("diary_selected_emotion_tags").select("emotion_tags(*)").eq("diary_id", diary_id).execute()
    return [row.get("emotion_tags", {}) for row in (result.data or [])]


def get_detail_parts(diary: dict) -> dict:
    client = _client()
    detail = {"selected_emotion_tags": get_selected_tags(diary["id"]), "media": []}
    if diary.get("final_emotion_id") is not None:
        detail["emotion"] = client.table("emotions").select("*").eq("id", diary["final_emotion_id"]).maybe_single().execute().data
    if diary.get("correct_emotion_id") is not None:
        detail["correct_emotion"] = get_emotion_by_id(diary["correct_emotion_id"])
    if diary.get("flower_id"):
        detail["flower"] = client.table("flowers").select("*").eq("id", diary["flower_id"]).maybe_single().execute().data
    media = client.table("media").select("*").eq("diary_id", diary["id"]).order("sort_order").execute()
    detail["media"] = media.data or []
    return detail


def transition(diary_id: int, user_id: str, action: str, payload: dict) -> dict:
    """Serialize diary transitions and training-sample writes in one DB transaction."""
    try:
        result = _client().rpc("apply_diary_emotion_transition", {
            "p_diary_id": diary_id, "p_user_id": user_id,
            "p_action": action, "p_payload": payload,
        }).execute()
    except APIError as exc:
        codes = {"PT404": 404, "PT409": 409, "PT422": 422}
        if exc.code in codes:
            raise HTTPException(codes[exc.code], exc.message) from exc
        raise
    return _one(result)


def list_analysis(user_id: str, from_date: date, to_date: date, group_id: int | None) -> list[dict]:
    query = _client().table("diaries").select("final_emotion_id, record_date").eq("user_id", user_id)
    query = query.gte("record_date", from_date.isoformat()).lt("record_date", to_date.isoformat())
    query = query.eq("status", "completed").is_("deleted_at", "null")
    if group_id is not None:
        query = query.eq("group_id", group_id)
    result = query.execute()
    return result.data or []


def get_flowers(emotion_id: int) -> list[dict]:
    result = _client().table("flowers").select("*").eq("emotion_id", emotion_id).execute()
    return result.data or []
