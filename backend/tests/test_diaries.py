import pytest
from fastapi import HTTPException
from app.integrations.ai.emotion_analyzer import EmotionAnalysis

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
    monkeypatch.setattr(diaries.repository, "transition", lambda *args: {})
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


def test_finalize_uses_saved_ai_primary_and_returns_detail(monkeypatch) -> None:
    diary = {
        "id": 1,
        "status": "draft",
        "situation_text": "오늘 힘든 일이 있었다",
        "question_answer_text": "그래도 조금 안도했다",
        "ai_emotion_predictions": [{"emotion_id": 10}, {"emotion_id": 11}],
    }
    monkeypatch.setattr(diaries.repository, "get_diary", lambda diary_id, user_id: diary)
    def flowers(emotion_id):
        assert emotion_id == 10
        return [{"id": 20}]
    def transition(diary_id, user_id, action, payload):
        assert (diary_id, user_id, action, payload) == (1, "user-1", "finalize", {"flower_id": 20})
        return {"id": 1, "status": "completed", "final_emotion_id": 10, "correct_emotion_id": 11}
    monkeypatch.setattr(diaries.repository, "get_flowers", flowers)
    monkeypatch.setattr(diaries.repository, "transition", transition)
    monkeypatch.setattr(diaries.repository, "get_detail_parts", lambda d: {"emotion": {"id": 10}})
    monkeypatch.setattr(diaries, "_analysis", lambda *a, **k: pytest.fail("Must not rerun AI"))
    result = diaries.finalize_diary("user-1", 1)
    assert result["final_emotion_id"] == 10
    assert result["correct_emotion_id"] == 11
    assert result["emotion"]["id"] == 10


def test_finalize_persists_selected_tags_before_finalizing(monkeypatch) -> None:
    diary = {
        "id": 1,
        "status": "draft",
        "question_answer_text": "답변",
        "ai_emotion_predictions": [{"emotion_id": 10}],
    }
    calls = []
    monkeypatch.setattr(diaries.repository, "get_diary", lambda diary_id, user_id: diary)
    monkeypatch.setattr(
        diaries,
        "save_tags",
        lambda user_id, diary_id, tag_ids: calls.append((user_id, diary_id, tag_ids)) or diary,
    )
    monkeypatch.setattr(diaries.repository, "get_flowers", lambda emotion_id: [{"id": 20}])
    monkeypatch.setattr(
        diaries.repository,
        "transition",
        lambda diary_id, user_id, action, payload: {"id": 1, "status": "completed"},
    )
    monkeypatch.setattr(diaries.repository, "get_detail_parts", lambda diary: {})

    diaries.finalize_diary("user-1", 1, [101, 102, 103])

    assert calls == [("user-1", 1, [101, 102, 103])]


def test_recommendations_persist_two_ranked_groups_of_five(monkeypatch):
    monkeypatch.setattr(diaries.repository, "get_diary", lambda *a: {"question_answer_text": "답변"})
    monkeypatch.setattr(
        diaries, "_analysis",
        lambda text, situation_text=None: EmotionAnalysis("guilt", "sadness", .7, .2, "v1"),
    )
    monkeypatch.setattr(diaries.repository, "get_emotion", lambda c: {
        "id": 1 if c == "guilt" else 2, "emotion": c, "display_name": c,
    })
    monkeypatch.setattr(diaries.repository, "get_emotion_tags", lambda ids: [
        {"id": ids[0] * 10 + i, "parent_emotion_id": ids[0]} for i in range(5)
    ])
    def transition(did, uid, action, payload):
        assert action == "predictions" and payload["answer"] == "답변"
        return {"ai_emotion_predictions": payload["predictions"]}
    monkeypatch.setattr(diaries.repository, "transition", transition)
    result = diaries.emotion_suggestions("user", 1)
    assert [s["rank"] for s in result] == [1, 2]
    assert [s["confidence"] for s in result] == [.7, .2]
    assert [len(s["tags"]) for s in result] == [5, 5]
    assert [s["model_version"] for s in result] == ["v1", "v1"]


def test_cached_predictions_do_not_run_ai(monkeypatch):
    predictions = [{"emotion_id": 1}, {"emotion_id": 2}]
    monkeypatch.setattr(diaries.repository, "get_diary", lambda *a: {"ai_emotion_predictions": predictions})
    monkeypatch.setattr(diaries, "_analysis", lambda *a, **k: pytest.fail("Must reuse predictions"))
    assert diaries.emotion_suggestions("user", 1) == predictions


@pytest.mark.parametrize("ids", [[1, 1, 2], [1, 2], [1, 2, 99]])
def test_invalid_tag_selection_is_rejected(monkeypatch, ids):
    monkeypatch.setattr(diaries.repository, "get_diary", lambda *a: {
        "question_answer_text": "answer",
        "ai_emotion_predictions": [{"tags": [{"id": i} for i in range(1, 11)]}],
    })
    with pytest.raises(HTTPException) as err:
        diaries.save_tags("user", 1, ids)
    assert err.value.status_code == 422


@pytest.mark.parametrize("operation,args", [
    (diaries.save_answer, ("answer",)), (diaries.save_tags, ([1, 2, 3],)),
    (diaries.generate_question, ()),
])
def test_completed_diaries_are_immutable(monkeypatch, operation, args):
    monkeypatch.setattr(diaries.repository, "get_diary", lambda *a: {"status": "completed"})
    with pytest.raises(HTTPException) as err:
        operation("user", 1, *args)
    assert err.value.status_code == 409
