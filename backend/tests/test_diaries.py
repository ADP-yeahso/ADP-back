from fastapi import HTTPException

from app.services import diaries


def test_create_diary_uses_spec_fields(monkeypatch) -> None:
    saved = {}
    monkeypatch.setattr(
        diaries.repository,
        "create_diary",
        lambda user_id, data: saved.update({"user_id": user_id, **data}) or {"id": 1, **data},
    )

    result = diaries.create_diary("user-1", 10, "오늘은 감사한 일이 있었다", None, None)

    assert result["id"] == 1
    assert saved["group_id"] == 10
    assert saved["situation_text"] == "오늘은 감사한 일이 있었다"


def test_generate_question_is_based_on_situation(monkeypatch) -> None:
    monkeypatch.setattr(
        diaries.repository,
        "get_diary",
        lambda diary_id, user_id: {"id": diary_id, "situation_text": "오늘은 불안하고 걱정됐다"},
    )
    monkeypatch.setattr(diaries.repository, "set_question", lambda *args: None)
    monkeypatch.setattr(
        diaries.QuestionGenerator,
        "generate",
        lambda self, situation: "그때 어떤 감정이 가장 크게 느껴졌나요?",
    )

    result = diaries.generate_question("user-1", 1)

    assert result["diary_id"] == 1
    assert result["ai_question_text"] == "그때 어떤 감정이 가장 크게 느껴졌나요?"


def test_answer_requires_ai_question(monkeypatch) -> None:
    monkeypatch.setattr(
        diaries.repository,
        "get_diary",
        lambda diary_id, user_id: {"id": diary_id, "situation_text": "기록", "ai_question_text": None},
    )

    try:
        diaries.save_answer("user-1", 1, "답변")
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("Expected AI question precondition failure")


def test_finalize_saves_second_answer_as_training_data(monkeypatch) -> None:
    diary = {
        "id": 1,
        "status": "draft",
        "situation_text": "오늘 힘든 일이 있었다",
        "question_answer_text": "그래도 조금 안도했다",
    }
    training_sample = {}
    monkeypatch.setattr(diaries.repository, "get_diary", lambda diary_id, user_id: diary)
    monkeypatch.setattr(
        diaries.repository,
        "get_selected_tags",
        lambda diary_id: [
            {"parent_emotion_id": 1},
            {"parent_emotion_id": 1},
            {"parent_emotion_id": 2},
        ],
    )
    monkeypatch.setattr(
        diaries.repository,
        "get_emotion",
        lambda code: {"id": 10 if code == "gratitude" else 11, "emotion": code},
    )
    monkeypatch.setattr(diaries.repository, "get_flowers", lambda emotion_id: [{"id": 20}])
    monkeypatch.setattr(diaries.repository, "finalize", lambda *args: {"id": 1, "status": "completed"})
    monkeypatch.setattr(
        diaries.repository,
        "save_training_sample",
        lambda sample, user_id, emotion_id: training_sample.update(sample),
    )

    diaries.finalize_diary("user-1", 1)

    assert training_sample["question_answer_text"] == "그래도 조금 안도했다"
    assert training_sample["final_emotion_id"] == 1
