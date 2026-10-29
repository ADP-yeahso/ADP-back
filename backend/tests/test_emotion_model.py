import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import emotion_model
from app.core.config import Settings
from app.integrations.ai.emotion_analyzer import _resolve_class_codes
from app.main import app

LABEL_MAP = {
    "LABEL_0": "neutral", "LABEL_1": "anger", "LABEL_2": "anxiety", "LABEL_3": "sadness",
    "LABEL_4": "guilt", "LABEL_5": "gratitude", "LABEL_6": "tenderness",
}
CODES = ("neutral", "anger", "anxiety", "sadness", "guilt", "gratitude", "tenderness")


def test_generic_labels_map_directly() -> None:
    id2label = {i: f"LABEL_{i}" for i in range(7)}
    assert _resolve_class_codes(id2label, 7, LABEL_MAP) == CODES


def test_mlops_korean_labels_fall_back_to_class_index() -> None:
    names = ["중립/일상", "분노/답답함", "불안/초조", "슬픔/소진", "죄책감/자책", "감사/안도", "애틋함/수용"]
    id2label = {str(i): name for i, name in enumerate(names)}
    assert _resolve_class_codes(id2label, 7, LABEL_MAP) == CODES


def test_missing_label_is_rejected() -> None:
    with pytest.raises(RuntimeError):
        _resolve_class_codes({i: f"LABEL_{i}" for i in range(7)}, 7, {"LABEL_0": "neutral"})


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_reload_is_disabled_without_token(monkeypatch) -> None:
    monkeypatch.setattr(emotion_model, "get_settings", lambda: _settings())
    response = TestClient(app).post("/reload-model", json={"revision": "v2"})
    assert response.status_code == 503


def test_reload_rejects_wrong_token(monkeypatch) -> None:
    monkeypatch.setattr(emotion_model, "get_settings", lambda: _settings(emotion_model_reload_token="secret"))
    response = TestClient(app).post(
        "/reload-model", json={"revision": "v2"}, headers={"X-Reload-Token": "wrong"}
    )
    assert response.status_code == 401


def test_reload_swaps_in_background(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(emotion_model, "get_settings", lambda: _settings(emotion_model_reload_token="secret"))
    monkeypatch.setattr(emotion_model, "reload_classifier", lambda revision: calls.append(revision))
    response = TestClient(app).post(
        "/reload-model", json={"revision": "v2"}, headers={"X-Reload-Token": "secret"}
    )
    assert response.status_code == 202
    assert calls == ["v2"]


def test_reload_rejects_unsafe_revision(monkeypatch) -> None:
    monkeypatch.setattr(emotion_model, "get_settings", lambda: _settings(emotion_model_reload_token="secret"))
    response = TestClient(app).post(
        "/reload-model", json={"revision": "../etc"}, headers={"X-Reload-Token": "secret"}
    )
    assert response.status_code == 422
