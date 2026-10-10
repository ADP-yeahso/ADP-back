"""app/api/v1/endpoints/letters.py

FastAPI Router Endpoints for Family Letters (가족 편지함) domain.
Handles authorization header validation via get_current_user_id dependency,
payload parsing, and delegation to the service layer.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user_id
from app.schemas.letters import (
    LetterBoxType,
    LetterCreate,
    LetterDetailResponse,
    LetterReadStatusResponse,
    LetterResponse,
)
from app.services import letters as service

router = APIRouter()


@router.post(
    "",
    response_model=LetterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="가족 편지 작성 및 전송",
)
def send_letter(
    payload: LetterCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> LetterResponse:
    """새로운 가족 편지를 작성하고 전송합니다.
    
    - 특정 1인 지정 수신: `receiver_user_id`에 수신 대상 유저 UUID 지정
    - '가족 모두에게' 수신: `receiver_user_id`를 `null`로 설정
    - `content`는 최대 500자까지 작성할 수 있으며, 초과 시 422 에러가 발생합니다.
    - 발신자 ID는 Request Body가 아닌 인증 토큰에서 추출됩니다.
    """
    return service.send_letter(current_user_id, payload)


@router.get(
    "",
    response_model=list[LetterResponse],
    summary="가족 편지함 목록 조회",
)
def list_letters(
    group_id: int = Query(..., description="조회할 그룹 ID"),
    box_type: LetterBoxType = Query(
        LetterBoxType.INBOX,
        description="편지함 구분 (inbox: 수신함, sent: 발신함)",
    ),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[LetterResponse]:
    """속한 그룹의 수신함(inbox) 또는 발신함(sent) 편지 목록을 최신순으로 조회합니다."""
    return service.list_letters(current_user_id, group_id, box_type)


@router.get(
    "/{letter_id}",
    response_model=LetterDetailResponse,
    summary="가족 편지 단건 상세 조회 (자동 읽음 처리)",
)
def get_letter_detail(
    letter_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> LetterDetailResponse:
    """ID로 편지 상세 정보를 조회합니다.
    
    수신자(본인)가 조회하는 경우 자동으로 읽음 처리(is_read=True)됩니다.
    """
    return service.get_letter_detail(current_user_id, letter_id)


@router.delete(
    "/{letter_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="가족 편지 삭제 (Soft Delete)",
)
def delete_letter(
    letter_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """작성한 편지를 소프트 삭제(Soft Delete)합니다. 작성자 본인만 삭제 가능합니다."""
    service.delete_letter(current_user_id, letter_id)


@router.get(
    "/{letter_id}/reads",
    response_model=list[LetterReadStatusResponse],
    summary="편지 수신자별 읽음 현황 조회",
)
def get_letter_reads(
    letter_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[LetterReadStatusResponse]:
    """특정 편지에 대한 수신 대상자별 읽음 여부 및 읽은 시각 목록을 조회합니다."""
    return service.get_letter_reads(current_user_id, letter_id)
