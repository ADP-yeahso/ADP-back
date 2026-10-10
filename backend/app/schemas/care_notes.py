"""Schemas for Care Notebook (돌봄수첩) domain.

Covers Daily Conditions, Behavior Logs, Medications, Medication Intake Logs, and Hospital Visits.
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ==========================================
# 1. Enums (Validation & 422 Defense Line)
# ==========================================


class MealStatus(str, Enum):
    """식사 상태."""

    GREAT = "좋음"
    NORMAL = "보통"
    LOW = "적음"
    POOR = "거의 못함"


class SleepStatus(str, Enum):
    """수면 상태."""

    GREAT = "좋음"
    NORMAL = "보통"
    POOR = "나쁨"


class BowelStatus(str, Enum):
    """배변 상태."""

    NORMAL = "정상"
    CHANGED = "변화 있음"
    NONE = "없음"


class ActivityStatus(str, Enum):
    """활동·운동 상태."""

    NORMAL = "평소와 비슷"
    LOW = "적음"
    HIGH = "많음"


class CognitiveStatus(str, Enum):
    """인지 상태."""

    NORMAL = "평소와 비슷"
    CONFUSED = "혼란 증가"
    MEMORY_DECLINE = "기억력 저하 체감"


class MedicationStatus(str, Enum):
    """복약 여부 및 상태."""

    COMPLETED = "완료"
    PARTIAL = "일부 누락"
    NOT_TAKEN = "미복용"


# ==========================================
# 2. Daily Conditions (오늘의 환자 상태)
# ==========================================


class DailyConditionCreate(BaseModel):
    """오늘 상태 생성 요청 (user_id 등 시스템 필드 제외)."""

    patient_id: int = Field(..., description="환자 ID")
    record_date: date = Field(..., description="기록 날짜")
    meal_status: MealStatus = Field(..., description="식사 상태")
    sleep_status: SleepStatus = Field(..., description="수면 상태")
    bowel_status: BowelStatus = Field(..., description="배변 상태")
    activity_status: ActivityStatus = Field(..., description="활동·운동 상태")
    mood_status: str = Field(..., description="기분·정서 상태 (문자열)")
    cognitive_status: CognitiveStatus = Field(..., description="인지 상태")
    behavior_change: bool = Field(False, description="행동 변화 유무")
    medication_status: MedicationStatus = Field(..., description="복약 상태")
    note: str | None = Field(None, description="오늘의 특이사항 메모")


class DailyConditionUpdate(BaseModel):
    """오늘 상태 수정 요청."""

    meal_status: MealStatus | None = None
    sleep_status: SleepStatus | None = None
    bowel_status: BowelStatus | None = None
    activity_status: ActivityStatus | None = None
    mood_status: str | None = None
    cognitive_status: CognitiveStatus | None = None
    behavior_change: bool | None = None
    medication_status: MedicationStatus | None = None
    note: str | None = None


class DailyConditionResponse(BaseModel):
    """오늘 상태 응답 스키마."""

    id: int
    patient_id: int
    user_id: UUID
    record_date: date
    meal_status: str
    sleep_status: str
    bowel_status: str
    activity_status: str
    mood_status: str
    cognitive_status: str
    behavior_change: bool
    medication_status: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 3. Behavior Logs (행동 및 증상 기록)
# ==========================================


class BehaviorLogCreate(BaseModel):
    """행동/증상 기록 생성 요청."""

    patient_id: int = Field(..., description="환자 ID")
    behavior_type: str = Field(..., description="행동 유형")
    occurred_at: datetime = Field(..., description="발생 시각 (timestamptz)")
    memo: str | None = Field(None, description="상세 메모")


class BehaviorLogUpdate(BaseModel):
    """행동/증상 기록 수정 요청."""

    behavior_type: str | None = None
    occurred_at: datetime | None = None
    memo: str | None = None


class BehaviorLogResponse(BaseModel):
    """행동/증상 기록 응답 스키마."""

    id: int
    patient_id: int
    user_id: UUID
    behavior_type: str
    memo: str | None = None
    occurred_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 4. Medications (복약 목록)
# ==========================================


class MedicationCreate(BaseModel):
    """복약 항목 생성 요청."""

    patient_id: int = Field(..., description="환자 ID")
    medication_name: str = Field(..., description="약 이름")
    dosage: str = Field(..., description="복용량")
    time_of_day: str = Field(..., description="복용 시간 (예: 아침/저녁, 08:00)")
    start_date: date = Field(..., description="복용 시작일")
    end_date: date | None = Field(None, description="복용 종료/변경일")
    note: str | None = Field(None, description="특이사항 메모")
    is_active: bool = Field(True, description="현재 복용 중 여부")


class MedicationUpdate(BaseModel):
    """복약 항목 수정 요청."""

    medication_name: str | None = None
    dosage: str | None = None
    time_of_day: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = None
    is_active: bool | None = None


class MedicationResponse(BaseModel):
    """복약 항목 응답 스키마."""

    id: int
    patient_id: int
    medication_name: str
    dosage: str
    time_of_day: str
    start_date: date
    end_date: date | None = None
    note: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 5. Medication Intake Logs (일별 복용 여부)
# ==========================================


class MedicationIntakeLogCreate(BaseModel):
    """일별 복용 여부 기록 생성/등록 요청."""

    medication_id: int = Field(..., description="복약 항목 ID")
    log_date: date = Field(..., description="복용 확인 날짜")
    status: MedicationStatus = Field(..., description="복용 여부")
    taken_at: datetime | None = Field(None, description="실제 복용 시각")


class MedicationIntakeLogUpdate(BaseModel):
    """일별 복용 여부 수정 요청."""

    status: MedicationStatus | None = None
    taken_at: datetime | None = None


class MedicationIntakeLogResponse(BaseModel):
    """일별 복용 여부 응답 스키마."""

    id: int
    medication_id: int
    log_date: date
    status: str
    taken_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 6. Hospital Visits (병원 및 진료 기록)
# ==========================================


class HospitalVisitCreate(BaseModel):
    """병원 진료 기록 생성 요청."""

    patient_id: int = Field(..., description="환자 ID")
    visit_date: date = Field(..., description="방문 날짜")
    hospital_name: str = Field(..., description="병원명")
    department: str | None = Field(None, description="진료과")
    visit_reason: str | None = Field(None, description="방문 이유")
    message_to_doctor: str | None = Field(None, description="의료진에게 전달한 내용")
    doctor_instructions: str | None = Field(None, description="의료진 안내사항")
    medication_changed: bool = Field(False, description="약 변경 여부")
    next_visit_date: date | None = Field(None, description="다음 진료일")
    guardian_memo: str | None = Field(None, description="보호자 메모")


class HospitalVisitUpdate(BaseModel):
    """병원 진료 기록 수정 요청."""

    visit_date: date | None = None
    hospital_name: str | None = None
    department: str | None = None
    visit_reason: str | None = None
    message_to_doctor: str | None = None
    doctor_instructions: str | None = None
    medication_changed: bool | None = None
    next_visit_date: date | None = None
    guardian_memo: str | None = None


class HospitalVisitResponse(BaseModel):
    """병원 진료 기록 응답 스키마."""

    id: int
    patient_id: int
    user_id: UUID
    visit_date: date
    hospital_name: str
    department: str | None = None
    visit_reason: str | None = None
    message_to_doctor: str | None = None
    doctor_instructions: str | None = None
    medication_changed: bool
    next_visit_date: date | None = None
    guardian_memo: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
