from datetime import datetime, timezone

from app.services import media


def _stored_media() -> dict:
    return {
        "id": 10,
        "diary_id": 1,
        "memory_record_id": None,
        "file_type": "image",
        "file_url": "diaries/1/file.jpg",
        "duration": None,
        "sort_order": 0,
        "created_at": datetime.now(timezone.utc),
    }


def test_upload_diary_media_stores_file_then_metadata(monkeypatch) -> None:
    uploaded = {}
    monkeypatch.setattr(media.diaries, "get_diary", lambda diary_id, user_id: {"id": diary_id})
    monkeypatch.setattr(media.storage, "make_diary_path", lambda diary_id, filename: "diaries/1/file.jpg")
    monkeypatch.setattr(
        media.storage,
        "upload",
        lambda path, content, content_type: uploaded.update({"path": path, "content": content, "content_type": content_type}),
    )
    monkeypatch.setattr(media.repository, "create_diary_media", lambda *args: _stored_media())
    monkeypatch.setattr(media.storage, "signed_url", lambda path: f"https://signed.example/{path}")

    result = media.upload_diary_media(1, "user-1", "photo.jpg", "image/jpeg", b"image", None, 0)

    assert uploaded == {"path": "diaries/1/file.jpg", "content": b"image", "content_type": "image/jpeg"}
    assert result["file_type"] == "image"
    assert result["download_url"] == "https://signed.example/diaries/1/file.jpg"


def test_list_diary_media_adds_signed_urls(monkeypatch) -> None:
    monkeypatch.setattr(media.diaries, "get_diary", lambda diary_id, user_id: {"id": diary_id})
    monkeypatch.setattr(media.repository, "list_diary_media", lambda diary_id: [_stored_media()])
    monkeypatch.setattr(media.storage, "signed_url", lambda path: f"https://signed.example/{path}")

    result = media.list_diary_media(1, "user-1")

    assert result[0]["download_url"] == "https://signed.example/diaries/1/file.jpg"


def test_delete_diary_media_removes_storage_object_and_metadata(monkeypatch) -> None:
    removed = []
    deleted = []
    monkeypatch.setattr(media.diaries, "get_diary", lambda diary_id, user_id: {"id": diary_id})
    monkeypatch.setattr(media.repository, "get_diary_media", lambda media_id, diary_id: _stored_media())
    monkeypatch.setattr(media.storage, "remove", lambda path: removed.append(path))
    monkeypatch.setattr(media.repository, "delete_diary_media", lambda media_id, diary_id: deleted.append((media_id, diary_id)))

    media.delete_diary_media(1, 10, "user-1")

    assert removed == ["diaries/1/file.jpg"]
    assert deleted == [(10, 1)]
