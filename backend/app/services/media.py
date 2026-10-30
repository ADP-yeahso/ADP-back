"""Diary and memory-record media upload, retrieval, and deletion use cases."""

from fastapi import HTTPException, status

from app.integrations.storage import supabase_storage as storage
from app.db.supabase import get_supabase_client
from app.repositories import diaries, media as repository, memories
from app.repositories.patients import check_patient_access

MAX_FILE_SIZE = 50 * 1024 * 1024
ALLOWED_PREFIXES = {"image": "image/", "audio": "audio/", "video": "video/"}


def _owned_diary(diary_id: int, user_id: str) -> dict:
    return diaries.get_diary(diary_id, user_id)


def _accessible_memory_record(record_id: int, user_id: str) -> dict:
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase is not configured")
    record = memories.get_memory_record_by_id(client, record_id)
    if not record:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory record not found")
    if not check_patient_access(client, record["patient_id"], user_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You cannot access this memory record")
    return record


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


def upload_memory_record_media(
    record_id: int,
    user_id: str,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    duration: int | None,
    sort_order: int,
) -> dict:
    _accessible_memory_record(record_id, user_id)
    if not filename:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A file name is required")
    if not content:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "An empty file cannot be uploaded")
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Media file must be 50 MB or smaller")
    if duration is not None and duration < 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duration must be zero or greater")

    file_type = _media_type(content_type)
    storage_path = storage.make_memory_record_path(record_id, filename)
    storage.upload(storage_path, content, content_type)
    try:
        item = repository.create_memory_record_media(
            record_id, file_type, storage_path, duration, sort_order
        )
    except Exception:
        storage.remove(storage_path)
        raise
    return _with_url(item)


def list_memory_record_media(record_id: int, user_id: str) -> list[dict]:
    _accessible_memory_record(record_id, user_id)
    return [_with_url(item) for item in repository.list_memory_record_media(record_id)]


def list_memory_records_media(record_ids: list[int]) -> dict[int, list[dict]]:
    grouped = {record_id: [] for record_id in record_ids}
    for item in repository.list_memory_records_media(record_ids):
        record_id = item.get("memory_record_id")
        if record_id in grouped:
            grouped[record_id].append(_with_url(item))
    return grouped


def delete_memory_record_media(record_id: int, media_id: int, user_id: str) -> None:
    _accessible_memory_record(record_id, user_id)
    item = repository.get_memory_record_media(media_id, record_id)
    storage.remove(item["file_url"])
    repository.delete_memory_record_media(media_id, record_id)
