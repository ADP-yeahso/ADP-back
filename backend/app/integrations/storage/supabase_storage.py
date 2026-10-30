"""Supabase Storage operations for diary and memory-record attachments."""

from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, status

from app.db.supabase import get_supabase_client
from app.core.config import get_settings


def _bucket():
    client = get_supabase_client()
    if client is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Supabase is not configured")
    return client.storage.from_(get_settings().supabase_storage_bucket)


def make_diary_path(diary_id: int, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"diaries/{diary_id}/{uuid4().hex}{suffix}"


def make_memory_record_path(record_id: int, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"memory-records/{record_id}/{uuid4().hex}{suffix}"


def upload(storage_path: str, content: bytes, content_type: str) -> None:
    try:
        _bucket().upload(storage_path, content, {"content-type": content_type, "upsert": "false"})
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Media upload failed") from exc


def signed_url(storage_path: str, expires_in: int = 3600) -> str:
    try:
        result = _bucket().create_signed_url(storage_path, expires_in)
        return result["signedURL"]
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Media URL could not be created") from exc


def remove(storage_path: str) -> None:
    try:
        _bucket().remove([storage_path])
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Media deletion failed") from exc
