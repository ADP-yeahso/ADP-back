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
    "anger": ("억울함", "짜증", "무력감", "원망스러운", "분함"),
    "anxiety": ("막막함", "예민함", "압박감", "당혹감", "초조함"),
    "sadness": ("상실감", "탈진", "서러움", "허무함", "외로움"),
    "guilt": ("자책감", "미안함", "부족함", "후회스러움", "부끄러움"),
    "gratitude": ("다행스러움", "따뜻함", "편안함", "고마움", "후련함"),
    "tenderness": ("그리움", "뭉클함", "사랑스러움", "소중함", "애틋함"),
    "neutral": ("담담함", "무탈함", "여유로움", "무심함", "평온함"),
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
    if not diary.get("situation_text"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Situation text is required")
    try:
        question = QuestionGenerator().generate(diary["situation_text"])
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Custom question generator is unavailable") from exc
    repository.set_question(diary_id, user_id, question)
    return {"diary_id": diary_id, "ai_question_text": question}


def save_answer(user_id: str, diary_id: int, answer: str) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if not diary.get("ai_question_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "AI question has not been generated")
    return repository.set_answer(diary_id, user_id, answer)


def emotion_suggestions(user_id: str, diary_id: int) -> list[dict]:
    diary = repository.get_diary(diary_id, user_id)
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    analysis = _analysis(diary["question_answer_text"])
    suggestions = []
    for rank, code in enumerate((analysis.primary, analysis.secondary)):
        emotion = repository.get_emotion(code)
        tags = repository.get_emotion_tags([emotion["id"]])
        if len(tags) != len(SUB_EMOTION_NAMES[code]):
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Each emotion must have exactly five active tags")
        suggestions.append({
            "emotion_id": emotion["id"], "emotion": code,
            "display_name": emotion["display_name"],
            "confidence": 1.0 if rank == 0 else 0.5,
            "tags": tags,
        })
    return suggestions


def save_tags(user_id: str, diary_id: int, tag_ids: list[int]) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    if len(tag_ids) != 3 or len(set(tag_ids)) != 3:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Exactly three unique emotion tags are required")
    suggestions = emotion_suggestions(user_id, diary_id)
    allowed_ids = {tag["id"] for suggestion in suggestions for tag in suggestion["tags"]}
    if not set(tag_ids).issubset(allowed_ids):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tags must come from the two suggested emotions")
    repository.replace_tags(diary_id, tag_ids)
    return repository.get_diary(diary_id, user_id)


def finalize_diary(user_id: str, diary_id: int) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if diary.get("status") == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Diary is already finalized")
    if not diary.get("question_answer_text"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Answer has not been saved")
    tags = repository.get_selected_tags(diary_id)
    if len(tags) != 3:
        raise HTTPException(status.HTTP_409_CONFLICT, "Exactly three emotion tags must be selected")
    counts: dict[int, int] = {}
    for tag in tags:
        parent_id = tag["parent_emotion_id"]
        counts[parent_id] = counts.get(parent_id, 0) + 1
    final_emotion_id = max(counts, key=counts.get)
    primary_emotion = repository.get_emotion(_analysis(diary["question_answer_text"]).primary)
    flowers = repository.get_flowers(primary_emotion["id"])
    if not flowers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flower not found")
    result = repository.finalize(diary_id, user_id, final_emotion_id, random.choice(flowers)["id"])
    repository.save_training_sample(
        result | {
            "situation_text": diary["situation_text"],
            "question_answer_text": diary["question_answer_text"],
            "final_emotion_id": final_emotion_id,
        },
        user_id,
        final_emotion_id,
    )
    return result


def update_diary(user_id: str, diary_id: int, data: dict) -> dict:
    diary = repository.get_diary(diary_id, user_id)
    if diary["status"] == "completed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Finalized diary cannot be edited")
    return repository.update_diary(diary_id, user_id, {key: value for key, value in data.items() if value is not None})


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
