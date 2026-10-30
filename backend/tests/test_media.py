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


def _stored_memory_media() -> dict:
    return {
        **_stored_media(),
        "diary_id": None,
        "memory_record_id": 7,
        "file_url": "memory-records/7/voice.m4a",
        "file_type": "audio",
        "duration": 12,
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


def test_upload_memory_record_media_stores_audio(monkeypatch) -> None:
    uploaded = {}
    monkeypatch.setattr(media, "_accessible_memory_record", lambda record_id, user_id: {"id": record_id})
    monkeypatch.setattr(
        media.storage, "make_memory_record_path",
        lambda record_id, filename: "memory-records/7/voice.m4a",
    )
    monkeypatch.setattr(
        media.storage, "upload",
        lambda path, content, content_type: uploaded.update(
            {"path": path, "content": content, "content_type": content_type}
        ),
    )
    monkeypatch.setattr(media.repository, "create_memory_record_media", lambda *args: _stored_memory_media())
    monkeypatch.setattr(media.storage, "signed_url", lambda path: f"https://signed.example/{path}")

    result = media.upload_memory_record_media(
        7, "user-1", "voice.m4a", "audio/mp4", b"audio", 12, 0
    )

    assert uploaded["path"] == "memory-records/7/voice.m4a"
    assert result["file_type"] == "audio"
    assert result["download_url"].endswith("memory-records/7/voice.m4a")


def test_list_memory_record_media_adds_signed_urls(monkeypatch) -> None:
    monkeypatch.setattr(media, "_accessible_memory_record", lambda record_id, user_id: {"id": record_id})
    monkeypatch.setattr(media.repository, "list_memory_record_media", lambda record_id: [_stored_memory_media()])
    monkeypatch.setattr(media.storage, "signed_url", lambda path: f"https://signed.example/{path}")

    result = media.list_memory_record_media(7, "user-1")

    assert result[0]["memory_record_id"] == 7
    assert result[0]["download_url"].startswith("https://signed.example/")


def test_list_memory_records_media_groups_signed_urls(monkeypatch) -> None:
    second = {**_stored_memory_media(), "id": 11, "memory_record_id": 8}
    monkeypatch.setattr(
        media.repository,
        "list_memory_records_media",
        lambda record_ids: [_stored_memory_media(), second],
    )
    monkeypatch.setattr(media.storage, "signed_url", lambda path: f"https://signed.example/{path}")

    result = media.list_memory_records_media([7, 8, 9])

    assert result[7][0]["download_url"].startswith("https://signed.example/")
    assert result[8][0]["id"] == 11
    assert result[9] == []


def test_delete_memory_record_media_removes_storage_and_metadata(monkeypatch) -> None:
    removed = []
    deleted = []
    monkeypatch.setattr(media, "_accessible_memory_record", lambda record_id, user_id: {"id": record_id})
    monkeypatch.setattr(media.repository, "get_memory_record_media", lambda media_id, record_id: _stored_memory_media())
    monkeypatch.setattr(media.storage, "remove", lambda path: removed.append(path))
    monkeypatch.setattr(
        media.repository, "delete_memory_record_media",
        lambda media_id, record_id: deleted.append((media_id, record_id)),
    )

    media.delete_memory_record_media(7, 10, "user-1")

    assert removed == ["memory-records/7/voice.m4a"]
    assert deleted == [(10, 7)]
