"""Supabase persistence for emotion diaries."""

from datetime import date, datetime
from typing import Any

from fastapi import HTTPException, status

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


def set_question(diary_id: int, user_id: str, question: str) -> dict:
    return update_diary(diary_id, user_id, {"ai_question_text": question})


def set_answer(diary_id: int, user_id: str, answer: str) -> dict:
    return update_diary(diary_id, user_id, {"question_answer_text": answer})


def replace_tags(diary_id: int, tag_ids: list[int]) -> None:
    client = _client()
    client.table("diary_selected_emotion_tags").delete().eq("diary_id", diary_id).execute()
    client.table("diary_selected_emotion_tags").insert([{"diary_id": diary_id, "emotion_tag_id": tag_id} for tag_id in tag_ids]).execute()


def get_selected_tags(diary_id: int) -> list[dict]:
    result = _client().table("diary_selected_emotion_tags").select("emotion_tags(*)").eq("diary_id", diary_id).execute()
    return [row.get("emotion_tags", {}) for row in (result.data or [])]


def get_detail_parts(diary: dict) -> dict:
    client = _client()
    detail = {"selected_emotion_tags": get_selected_tags(diary["id"]), "media": []}
    if diary.get("final_emotion_id"):
        detail["emotion"] = client.table("emotions").select("*").eq("id", diary["final_emotion_id"]).maybe_single().execute().data
    if diary.get("flower_id"):
        detail["flower"] = client.table("flowers").select("*").eq("id", diary["flower_id"]).maybe_single().execute().data
    media = client.table("media").select("*").eq("diary_id", diary["id"]).order("sort_order").execute()
    detail["media"] = media.data or []
    return detail


def list_analysis(user_id: str, from_date: date, to_date: date, group_id: int | None) -> list[dict]:
    query = _client().table("diaries").select("final_emotion_id, record_date").eq("user_id", user_id)
    query = query.gte("record_date", from_date.isoformat()).lt("record_date", to_date.isoformat())
    query = query.eq("status", "completed").is_("deleted_at", "null")
    if group_id is not None:
        query = query.eq("group_id", group_id)
    result = query.execute()
    return result.data or []


def finalize(diary_id: int, user_id: str, emotion_id: int, flower_id: int) -> dict:
    return update_diary(diary_id, user_id, {"final_emotion_id": emotion_id, "flower_id": flower_id, "status": "completed"})


def get_flowers(emotion_id: int) -> list[dict]:
    result = _client().table("flowers").select("*").eq("emotion_id", emotion_id).execute()
    return result.data or []


def save_training_sample(diary: dict, user_id: str, emotion_id: int) -> None:
    _client().table("emotion_training_samples").insert({
        "diary_id": diary["id"],
        "user_id": user_id,
        "situation_text": diary["situation_text"],
        "question_answer_text": diary["question_answer_text"],
        "final_emotion_id": emotion_id,
    }).execute()
