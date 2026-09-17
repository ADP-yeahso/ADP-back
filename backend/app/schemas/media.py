"""Media metadata and diary attachment API schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class Media(BaseModel):
    id: int
    diary_id: int | None = None
    memory_record_id: int | None = None
    file_type: str
    # Storage object path, persisted in the database.
    file_url: str
    # Temporary signed URL used by the app to render or play the attachment.
    download_url: str | None = None
    duration: int | None = None
    sort_order: int
    created_at: datetime


class MediaUploadResponse(Media):
    pass
