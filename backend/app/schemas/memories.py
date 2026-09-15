"""Memory record and interaction schemas."""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemoryRecordBase(BaseModel):
    title: Optional[str] = Field(None, description="기억 기록 제목")
    context: Optional[str] = Field(None, description="기억 기록 내용")
    record_date: date = Field(..., description="기록 대상 날짜")


class MemoryRecordCreate(MemoryRecordBase):
    pass


class MemoryRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, description="기억 기록 제목")
    context: Optional[str] = Field(None, description="기억 기록 내용")
    record_date: Optional[date] = Field(None, description="기록 대상 날짜")


class MemoryRecordResponse(MemoryRecordBase):
    id: int = Field(..., description="기억 기록 ID")
    patient_id: int = Field(..., description="환자 ID")
    user_id: UUID = Field(..., description="작성자(유저) ID")
    created_at: datetime = Field(..., description="생성 일시")
    media: List[Any] = Field(default_factory=list, description="첨부 미디어 목록")
    bookmarked: bool = Field(default=False, description="북마크 여부")

    model_config = ConfigDict(from_attributes=True)
