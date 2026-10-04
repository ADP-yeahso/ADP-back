"""Emotion diary use cases."""

from datetime import date, timedelta
import random

from fastapi import HTTPException, status

from app.integrations.ai.emotion_analyzer import EmotionAnalyzer
from app.integrations.ai.question_generator import QuestionGenerator
from app.repositories import diaries as repository

QUESTION_BANK = {
    "anger": ("무엇이 가장 답답하고 화가 났나요?", "그때 정말 원했던 것은 무엇이었나요?"),
    "anxiety": ("무엇이 가장 걱정되었나요?", "불안을 조금 덜어준 순간이 있었나요?"),
    "sadness": ("무엇이 마음을 무겁게 했나요?", "오늘 나를 돌보기 위해 필요한 것은 무엇인가요?"),
    "guilt": ("스스로에게 어떤 말을 해주고 싶나요?", "그 상황을 조금 다르게 바라볼 수 있을까요?"),
    "gratitude": ("무엇이 고맙고 다행스러웠나요?", "그 안도감을 누구와 나누고 싶나요?"),
    "tenderness": ("무엇을 소중하게 받아들이고 있나요?", "그 마음을 어떻게 표현하고 싶나요?"),
    "neutral": ("오늘 기억에 남는 장면은 무엇인가요?", "평범했지만 좋았던 순간이 있었나요?"),
}

SUB_EMOTION_NAMES = {
    "anger": ("분노", "답답함", "억울함", "짜증", "무력감"),
    "anxiety": ("불안", "초조함", "걱정", "두려움", "긴장"),
    "sadness": ("슬픔", "허무함", "외로움", "지침", "소진"),
    "guilt": ("죄책감", "자책", "미안함", "후회", "부담감"),
    "gratitude": ("감사", "안도감", "고마움", "다행스러움", "든든함"),
    "tenderness": ("애틋함", "사랑", "소중함", "이해", "수용"),
    "neutral": ("평온함", "담담함", "일상", "편안함", "무덤덤함"),
}


def _analysis(text: str):
    try:
        return EmotionAnalyzer().analyze(text)
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Custom emotion classifier is unavailable") from exc


def create_diary(user_id: str, group_id: int, situation_text: str, title: str | None, record_date):
    data = {"group_id": group_id, "situation_text": situation_text, "title": title}
    if record_date is not None:
        data["record_date"] = record_date.isoformat()
    return repository.create_diary(user_id, data)


def generate_question(user_id: str, diary_id: int) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    _require_draft(diary)
    if not diary.get("situation_text"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Situation text is required")
    try:
        question = QuestionGenerator().generate(diary["situation_text"])
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Custom question generator is unavailable") from exc
    repository.transition(diary_id, user_id, "question", {
        "question": question, "situation_text": diary["situation_text"],
    })
    return {"diary_id": diary_id, "ai_question_text": question}


def save_answer(user_id: str, diary_id: int, answer: str) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    _require_draft(diary)
    if not diary.get("ai_question_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "AI question has not been generated")
    return repository.transition(diary_id, user_id, "answer", {"answer": answer})


def _require_draft(diary: dict) -> None:
    if diary.get("status") == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Finalized diary cannot be edited")


def emotion_suggestions(user_id: str, diary_id: int) -> list[dict]:
    diary = repository.get_diary(diary_id, user_id)
    if diary.get("ai_emotion_predictions"):
        return diary["ai_emotion_predictions"]
    _require_draft(diary)
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    analysis = _analysis(diary["question_answer_text"])
    if analysis.primary == analysis.secondary:
        raise HTTPException(503, "Emotion classifier must return two distinct emotions")
    suggestions = []
    for rank, code in enumerate((analysis.primary, analysis.secondary)):
        emotion = repository.get_emotion(code)
        tags = repository.get_emotion_tags([emotion["id"]])
        if len(tags) != 5 or len({tag["id"] for tag in tags}) != 5:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Each emotion must have exactly five active tags")
        suggestions.append({
            "emotion_id": emotion["id"], "emotion": code,
            "display_name": emotion["display_name"],
            "rank": rank + 1,
            "confidence": analysis.primary_confidence if rank == 0 else analysis.secondary_confidence,
            "tags": tags,
        })
    saved = repository.transition(diary_id, user_id, "predictions", {
        "answer": diary["question_answer_text"], "predictions": suggestions,
    })
    return saved["ai_emotion_predictions"]


def save_tags(user_id: str, diary_id: int, tag_ids: list[int]) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    _require_draft(diary)
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    if len(tag_ids) != 3 or len(set(tag_ids)) != 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Exactly three unique emotion tags are required")
    suggestions = diary.get("ai_emotion_predictions")
    if not suggestions:
        raise HTTPException(409, "Request emotion suggestions before selecting tags")
    allowed_ids = {tag["id"] for suggestion in suggestions for tag in suggestion["tags"]}
    if not set(tag_ids).issubset(allowed_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tags must come from the two suggested emotions")
    return repository.transition(diary_id, user_id, "tags", {"tag_ids": tag_ids})


def finalize_diary(user_id: str, diary_id: int) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if diary.get("status") == "completed":
        return diary | repository.get_detail_parts(diary)
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    predictions = diary.get("ai_emotion_predictions")
    if not predictions:
        raise HTTPException(409, "Request emotion suggestions before finalizing")
    flowers = repository.get_flowers(predictions[0]["emotion_id"])
    if not flowers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flower not found")
    result = repository.transition(diary_id, user_id, "finalize", {
        "flower_id": random.choice(flowers)["id"],
    })
    return result | repository.get_detail_parts(result)


def update_diary(user_id: str, diary_id: int, data: dict) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if diary["status"] == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Finalized diary cannot be edited")
    return repository.transition(diary_id, user_id, "update", data)


def analysis(user_id: str, period: str, group_id: int | None) -> dict:
    today = date.today()
    days = {"week": 7, "month": 30, "six_months": 182, "year": 365}[period]
    from_date = today - timedelta(days=days - 1)
    to_date = today + timedelta(days=1)
    rows = repository.list_analysis(user_id, from_date, to_date, group_id)
    counts: dict[int, int] = {}
    for row in rows:
        emotion_id = row.get("final_emotion_id")
        if emotion_id is not None:
            counts[emotion_id] = counts.get(emotion_id, 0) + 1
    total = sum(counts.values())
    emotions = []
    for emotion_id, count in counts.items():
        emotion = repository.get_emotion_by_id(emotion_id)
        emotions.append({
            "emotion_id": emotion["id"],
            "emotion": emotion["emotion"],
            "display_name": emotion["display_name"],
            "count": count,
            "ratio": count / total if total else 0,
        })
    return {"period": period, "from_date": from_date, "to_date": today, "total": total, "emotions": emotions}
