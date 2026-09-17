"""Diary media upload, retrieval, and deletion use cases."""

from fastapi import HTTPException, status

from app.integrations.storage import supabase_storage as storage
from app.repositories import diaries, media as repository

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_PREFIXES = {"image": "image/", "audio": "audio/", "video": "video/"}


def _owned_diary(diary_id: int, user_id: str) -> dict:
    return diaries.get_diary(diary_id, user_id)


def _media_type(content_type: str | None) -> str:
    if not content_type:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A media content type is required")
    for media_type, prefix in ALLOWED_PREFIXES.items():
        if content_type.startswith(prefix):
            return media_type
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Only image, audio, and video files are allowed")


def _with_url(item: dict) -> dict:
    return {**item, "download_url": storage.signed_url(item["file_url"])}


def upload_diary_media(
    diary_id: int,
    user_id: str,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    duration: int | None,
    sort_order: int,
) -> dict:
    _owned_diary(diary_id, user_id)
    if not filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A file name is required")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "An empty file cannot be uploaded")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Media file must be 50 MB or smaller")
    if duration is not None and duration < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duration must be zero or greater")

    file_type = _media_type(content_type)
    storage_path = storage.make_diary_path(diary_id, filename)
    storage.upload(storage_path, content, content_type)
    try:
        item = repository.create_diary_media(diary_id, file_type, storage_path, duration, sort_order)
    except Exception:
        storage.remove(storage_path)
        raise
    return _with_url(item)


def list_diary_media(diary_id: int, user_id: str) -> list[dict]:
    _owned_diary(diary_id, user_id)
    return [_with_url(item) for item in repository.list_diary_media(diary_id)]


def delete_diary_media(diary_id: int, media_id: int, user_id: str) -> None:
    _owned_diary(diary_id, user_id)
    item = repository.get_diary_media(media_id, diary_id)
    storage.remove(item["file_url"])
    repository.delete_diary_media(media_id, diary_id)
