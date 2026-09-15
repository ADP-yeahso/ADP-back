from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security import AuthenticatedUser, get_current_user
from app.repositories import diaries as repository
from app.schemas.diaries import (
    AiQuestionResponse,
    AnalysisResponse,
    Diary,
    DiaryAnswerCreate,
    DiaryCreate,
    DiaryDetail,
    DiaryUpdate,
    EmotionSuggestion,
    EmotionTagsUpdate,
)
from app.services import diaries as service

router = APIRouter()


def user_id(current_user: AuthenticatedUser) -> str:
    return str(current_user.id)


@router.post("", response_model=Diary, status_code=status.HTTP_201_CREATED)
def create_diary(payload: DiaryCreate, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.create_diary(user_id(current_user), payload.group_id, payload.situation_text, payload.title, payload.record_date)


@router.get("", response_model=list[Diary])
def list_diaries(group_id: int | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), current_user: AuthenticatedUser = Depends(get_current_user)):
    return repository.list_diaries(user_id(current_user), group_id, page, size)


@router.get("/analysis", response_model=AnalysisResponse)
def diary_analysis(period: str = Query("week", pattern="^(week|month|six_months|year)$"), group_id: int | None = None, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.analysis(user_id(current_user), period, group_id)


@router.get("/{diary_id}", response_model=DiaryDetail)
def get_diary(diary_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    diary = repository.get_diary(diary_id, user_id(current_user))
    diary.update(repository.get_detail_parts(diary))
    return diary


@router.patch("/{diary_id}", response_model=Diary)
def update_diary(diary_id: int, payload: DiaryUpdate, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.update_diary(user_id(current_user), diary_id, payload.model_dump(mode="json", exclude_unset=True))


@router.delete("/{diary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_diary(diary_id: int, current_user: AuthenticatedUser = Depends(get_current_user)) -> Response:
    repository.soft_delete_diary(diary_id, user_id(current_user))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{diary_id}/ai-question", response_model=AiQuestionResponse)
def generate_question(diary_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.generate_question(user_id(current_user), diary_id)


@router.patch("/{diary_id}/answer", response_model=Diary)
def save_answer(diary_id: int, payload: DiaryAnswerCreate, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.save_answer(user_id(current_user), diary_id, payload.question_answer_text)


@router.get("/{diary_id}/emotion-tag-suggestions", response_model=list[EmotionSuggestion])
def emotion_tag_suggestions(diary_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.emotion_suggestions(user_id(current_user), diary_id)


@router.put("/{diary_id}/emotion-tags", response_model=Diary)
def save_emotion_tags(diary_id: int, payload: EmotionTagsUpdate, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.save_tags(user_id(current_user), diary_id, payload.emotion_tag_ids)


@router.post("/{diary_id}/finalize", response_model=DiaryDetail)
def finalize_diary(diary_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.finalize_diary(user_id(current_user), diary_id)
