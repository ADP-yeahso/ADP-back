"""app/schemas/letters.py

Pydantic V2 schemas for Family Letters (가족 편지함) domain.
Includes validation rules (max 500 chars limit) and request/response models.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LetterBoxType(str, Enum):
    """편지함 구분 (수신함 / 발신함)."""

    INBOX = "inbox"
    SENT = "sent"


class LetterCreate(BaseModel):
    """편지 작성 요청 스키마.
    
    sender_user_id는 보안을 위해 Body에 포함하지 않고
    Endpoint의 Depends(get_current_user_id)에서 추출하여 처리합니다.
    """

    group_id: int = Field(..., description="편지를 전송할 그룹 ID")
    receiver_user_id: UUID | None = Field(
        default=None,
        description="수신자 사용자 UUID (특정 1인 지정 시 UUID, '가족 모두에게' 발송 시 null)",
    )
    content: str = Field(
        ...,
        max_length=500,
        description="편지 본문 (최대 500자 제한, 초과 시 422 Unprocessable Entity 에러 발생)",
    )


class LetterReadStatusResponse(BaseModel):
    """편지 수신자별 읽음 상태 응답 스키마."""

    user_id: UUID = Field(..., description="수신 대상 사용자 UUID")
    is_read: bool = Field(..., description="읽음 여부")
    read_at: datetime | None = Field(default=None, description="읽은 일시")

    model_config = ConfigDict(from_attributes=True)


class LetterResponse(BaseModel):
    """편지 기본 목록 및 단건 응답 스키마."""

    id: int = Field(..., description="편지 ID")
    group_id: int = Field(..., description="그룹 ID")
    sender_user_id: UUID = Field(..., description="발신자 사용자 UUID")
    receiver_user_id: UUID | None = Field(
        default=None,
        description="수신자 사용자 UUID (전체 발송 시 null)",
    )
    content: str = Field(..., description="편지 본문")
    created_at: datetime = Field(..., description="작성 일시")
    is_read: bool | None = Field(
        default=None,
        description="현재 요청자(수신자) 시점에서의 읽음 여부 (발신함/해당없음 시 null 가능)",
    )
    read_at: datetime | None = Field(
        default=None,
        description="현재 요청자 시점에서의 읽은 일시",
    )

    model_config = ConfigDict(from_attributes=True)


class LetterDetailResponse(LetterResponse):
    """편지 상세 응답 스키마 (전체 수신자 읽음 상태 목록 포함)."""

    reads: list[LetterReadStatusResponse] = Field(
        default_factory=list,
        description="수신 대상자별 읽음 상태 목록",
    )

    model_config = ConfigDict(from_attributes=True)
