"""Emotion diary API contracts matching the Supabase schema."""

from datetime import date, datetime

from pydantic import BaseModel, Field


class DiaryCreate(BaseModel):
    group_id: int
    situation_text: str = Field(min_length=1, max_length=20_000)
    title: str | None = Field(default=None, max_length=255)
    record_date: datetime | None = None


class DiaryUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    situation_text: str | None = Field(default=None, min_length=1, max_length=20_000)
    record_date: datetime | None = None


class DiaryAnswerCreate(BaseModel):
    question_answer_text: str = Field(min_length=1, max_length=20_000)


class EmotionTagsUpdate(BaseModel):
    emotion_tag_ids: list[int] = Field(min_length=3, max_length=3)


class AiQuestionResponse(BaseModel):
    diary_id: int
    ai_question_text: str


class Diary(BaseModel):
    id: int
    user_id: str
    group_id: int
    title: str | None = None
    situation_text: str | None = None
    ai_question_text: str | None = None
    question_answer_text: str | None = None
    final_emotion_id: int | None = None
    correct_emotion_id: int | None = None
    ai_emotion_predictions: list[dict] = Field(default_factory=list)
    emotion_logic_version: int = 1
    finalized_at: datetime | None = None
    flower_id: int | None = None
    status: str
    record_date: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class EmotionTagSuggestion(BaseModel):
    id: int
    parent_emotion_id: int
    tag_name: str
    display_order: int


class EmotionSuggestion(BaseModel):
    emotion_id: int
    emotion: str
    display_name: str
    rank: int = Field(ge=1, le=2)
    confidence: float | None = None
    tags: list[EmotionTagSuggestion]


class FlowerResponse(BaseModel):
    id: int
    emotion_id: int
    flower_name: str
    sentence: str


class DiaryDetail(Diary):
    selected_emotion_tags: list[EmotionTagSuggestion] = Field(default_factory=list)
    emotion: dict | None = None
    correct_emotion: dict | None = None
    flower: dict | None = None
    media: list[dict] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    period: str
    from_date: date
    to_date: date
    total: int
    emotions: list[dict]
