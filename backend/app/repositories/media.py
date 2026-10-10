"""Media metadata persistence."""

from typing import Any

from fastapi import HTTPException, status

from app.db.supabase import get_supabase_client


def _client():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase is not configured")
    return client


def _one(result: Any, detail: str = "Media not found") -> dict:
    if not result.data:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return result.data[0] if isinstance(result.data, list) else result.data


def create_diary_media(diary_id: int, file_type: str, storage_path: str, duration: int | None, sort_order: int) -> dict:
    result = _client().table("media").insert({
        "diary_id": diary_id,
        "file_type": file_type,
        "file_url": storage_path,
        "duration": duration,
        "sort_order": sort_order,
    }).execute()
    return _one(result, "Media metadata was not saved")


def list_diary_media(diary_id: int) -> list[dict]:
    result = _client().table("media").select("*").eq("diary_id", diary_id).order("sort_order").execute()
    return result.data or []


def get_diary_media(media_id: int, diary_id: int) -> dict:
    result = _client().table("media").select("*").eq("id", media_id).eq("diary_id", diary_id).execute()
    return _one(result)


def delete_diary_media(media_id: int, diary_id: int) -> None:
    _client().table("media").delete().eq("id", media_id).eq("diary_id", diary_id).execute()
