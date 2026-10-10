"""FastAPI Router Endpoints for Care Notebook (돌봄수첩) domain.

Covers endpoints for Daily Conditions, Behavior Logs, Medications, Medication Intake Logs, and Hospital Visits.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.core.security import get_current_user_id
from app.schemas.care_notes import (
    BehaviorLogCreate,
    BehaviorLogResponse,
    BehaviorLogUpdate,
    DailyConditionCreate,
    DailyConditionResponse,
    DailyConditionUpdate,
    HospitalVisitCreate,
    HospitalVisitResponse,
    HospitalVisitUpdate,
    MedicationCreate,
    MedicationIntakeLogCreate,
    MedicationIntakeLogResponse,
    MedicationIntakeLogUpdate,
    MedicationResponse,
    MedicationUpdate,
)
from app.services import care_notes as service

router = APIRouter()


# ==========================================
# 1. Daily Conditions (오늘의 환자 상태)
# ==========================================


@router.post(
    "/daily-conditions",
    response_model=DailyConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="오늘 상태 작성",
)
def create_daily_condition(
    payload: DailyConditionCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> DailyConditionResponse:
    """오늘의 환자 상태 기록을 생성합니다."""
    return service.create_daily_condition(current_user_id, payload)


@router.get(
    "/daily-conditions/{condition_id}",
    response_model=DailyConditionResponse,
    summary="오늘 상태 단건 조회",
)
def get_daily_condition(
    condition_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> DailyConditionResponse:
    """ID로 오늘의 환자 상태 기록을 조회합니다."""
    return service.get_daily_condition(current_user_id, condition_id)


@router.get(
    "/daily-conditions",
    response_model=list[DailyConditionResponse],
    summary="오늘 상태 목록 조회",
)
def list_daily_conditions(
    patient_id: int = Query(..., description="환자 ID"),
    start_date: date | None = Query(None, description="조회 시작 날짜"),
    end_date: date | None = Query(None, description="조회 종료 날짜"),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[DailyConditionResponse]:
    """환자의 오늘의 상태 기록 목록을 날짜 범위별로 조회합니다."""
    return service.list_daily_conditions(current_user_id, patient_id, start_date, end_date)


@router.patch(
    "/daily-conditions/{condition_id}",
    response_model=DailyConditionResponse,
    summary="오늘 상태 수정",
)
def update_daily_condition(
    condition_id: int,
    payload: DailyConditionUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> DailyConditionResponse:
    """오늘의 환자 상태 기록을 수정합니다 (작성자 본인만 가능)."""
    return service.update_daily_condition(current_user_id, condition_id, payload)


@router.delete(
    "/daily-conditions/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="오늘 상태 삭제",
)
def delete_daily_condition(
    condition_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """오늘의 환자 상태 기록을 삭제합니다 (작성자 본인만 가능)."""
    service.delete_daily_condition(current_user_id, condition_id)


# ==========================================
# 2. Behavior Logs (행동 및 증상 기록)
# ==========================================


@router.post(
    "/behavior-logs",
    response_model=BehaviorLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="행동/증상 기록 작성",
)
def create_behavior_log(
    payload: BehaviorLogCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> BehaviorLogResponse:
    """행동 및 증상 기록을 생성합니다."""
    return service.create_behavior_log(current_user_id, payload)


@router.get(
    "/behavior-logs/{log_id}",
    response_model=BehaviorLogResponse,
    summary="행동/증상 기록 단건 조회",
)
def get_behavior_log(
    log_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> BehaviorLogResponse:
    """ID로 행동 및 증상 기록을 조회합니다."""
    return service.get_behavior_log(current_user_id, log_id)


@router.get(
    "/behavior-logs",
    response_model=list[BehaviorLogResponse],
    summary="행동/증상 기록 목록 조회",
)
def list_behavior_logs(
    patient_id: int = Query(..., description="환자 ID"),
    start_date: date | None = Query(None, description="조회 시작 날짜"),
    end_date: date | None = Query(None, description="조회 종료 날짜"),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[BehaviorLogResponse]:
    """환자의 행동 및 증상 기록 목록을 조회합니다."""
    return service.list_behavior_logs(current_user_id, patient_id, start_date, end_date)


@router.patch(
    "/behavior-logs/{log_id}",
    response_model=BehaviorLogResponse,
    summary="행동/증상 기록 수정",
)
def update_behavior_log(
    log_id: int,
    payload: BehaviorLogUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> BehaviorLogResponse:
    """행동 및 증상 기록을 수정합니다 (작성자 본인만 가능)."""
    return service.update_behavior_log(current_user_id, log_id, payload)


@router.delete(
    "/behavior-logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="행동/증상 기록 삭제",
)
def delete_behavior_log(
    log_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """행동 및 증상 기록을 삭제합니다 (작성자 본인만 가능)."""
    service.delete_behavior_log(current_user_id, log_id)


# ==========================================
# 3. Medications (복약 목록)
# ==========================================


@router.post(
    "/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="복약 항목 등록",
)
def create_medication(
    payload: MedicationCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> MedicationResponse:
    """새로운 복약 항목을 등록합니다."""
    return service.create_medication(current_user_id, payload)


@router.get(
    "/medications/{medication_id}",
    response_model=MedicationResponse,
    summary="복약 항목 단건 조회",
)
def get_medication(
    medication_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> MedicationResponse:
    """ID로 복약 항목을 조회합니다."""
    return service.get_medication(current_user_id, medication_id)


@router.get(
    "/medications",
    response_model=list[MedicationResponse],
    summary="복약 항목 목록 조회",
)
def list_medications(
    patient_id: int = Query(..., description="환자 ID"),
    is_active: bool | None = Query(None, description="현재 복용 중 여부 필터"),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[MedicationResponse]:
    """환자의 복약 항목 목록을 조회합니다."""
    return service.list_medications(current_user_id, patient_id, is_active)


@router.patch(
    "/medications/{medication_id}",
    response_model=MedicationResponse,
    summary="복약 항목 수정",
)
def update_medication(
    medication_id: int,
    payload: MedicationUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> MedicationResponse:
    """복약 항목 정보(복용량, 종료일, 활성화 여부 등)를 수정합니다."""
    return service.update_medication(current_user_id, medication_id, payload)


@router.delete(
    "/medications/{medication_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="복약 항목 삭제",
)
def delete_medication(
    medication_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """복약 항목을 삭제합니다."""
    service.delete_medication(current_user_id, medication_id)


# ==========================================
# 4. Medication Intake Logs (일별 복용 여부)
# ==========================================


@router.post(
    "/medication-intake-logs",
    response_model=MedicationIntakeLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="일별 복용 여부 기록 등록 (Upsert)",
)
def create_or_update_intake_log(
    payload: MedicationIntakeLogCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> MedicationIntakeLogResponse:
    """특정 날짜의 약 복용 여부를 기록합니다 (이미존재할 경우 업데이트)."""
    return service.create_or_update_intake_log(current_user_id, payload)


@router.get(
    "/medication-intake-logs",
    response_model=list[MedicationIntakeLogResponse],
    summary="일별 복용 여부 목록 조회",
)
def list_intake_logs(
    patient_id: int = Query(..., description="환자 ID"),
    start_date: date | None = Query(None, description="조회 시작 날짜"),
    end_date: date | None = Query(None, description="조회 종료 날짜"),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[MedicationIntakeLogResponse]:
    """환자의 약 복용 확인 이력을 날짜별로 조회합니다."""
    return service.list_intake_logs_for_patient(current_user_id, patient_id, start_date, end_date)


@router.patch(
    "/medication-intake-logs/{log_id}",
    response_model=MedicationIntakeLogResponse,
    summary="일별 복용 여부 수정",
)
def update_intake_log(
    log_id: int,
    payload: MedicationIntakeLogUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> MedicationIntakeLogResponse:
    """복용 여부 기록을 수정합니다."""
    return service.update_intake_log(current_user_id, log_id, payload)


@router.delete(
    "/medication-intake-logs/{log_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="일별 복용 여부 삭제",
)
def delete_intake_log(
    log_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """복용 여부 기록을 삭제합니다."""
    service.delete_intake_log(current_user_id, log_id)


# ==========================================
# 5. Hospital Visits (병원 및 진료 기록)
# ==========================================


@router.post(
    "/hospital-visits",
    response_model=HospitalVisitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="병원 진료 기록 작성",
)
def create_hospital_visit(
    payload: HospitalVisitCreate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> HospitalVisitResponse:
    """병원 및 진료 기록을 생성합니다."""
    return service.create_hospital_visit(current_user_id, payload)


@router.get(
    "/hospital-visits/{visit_id}",
    response_model=HospitalVisitResponse,
    summary="병원 진료 기록 단건 조회",
)
def get_hospital_visit(
    visit_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> HospitalVisitResponse:
    """ID로 병원 및 진료 기록을 조회합니다."""
    return service.get_hospital_visit(current_user_id, visit_id)


@router.get(
    "/hospital-visits",
    response_model=list[HospitalVisitResponse],
    summary="병원 진료 기록 목록 조회",
)
def list_hospital_visits(
    patient_id: int = Query(..., description="환자 ID"),
    start_date: date | None = Query(None, description="조회 시작 날짜"),
    end_date: date | None = Query(None, description="조회 종료 날짜"),
    current_user_id: UUID = Depends(get_current_user_id),
) -> list[HospitalVisitResponse]:
    """환자의 병원 및 진료 기록 목록을 조회합니다."""
    return service.list_hospital_visits(current_user_id, patient_id, start_date, end_date)


@router.patch(
    "/hospital-visits/{visit_id}",
    response_model=HospitalVisitResponse,
    summary="병원 진료 기록 수정",
)
def update_hospital_visit(
    visit_id: int,
    payload: HospitalVisitUpdate,
    current_user_id: UUID = Depends(get_current_user_id),
) -> HospitalVisitResponse:
    """병원 및 진료 기록을 수정합니다 (작성자 본인만 가능)."""
    return service.update_hospital_visit(current_user_id, visit_id, payload)


@router.delete(
    "/hospital-visits/{visit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="병원 진료 기록 삭제",
)
def delete_hospital_visit(
    visit_id: int,
    current_user_id: UUID = Depends(get_current_user_id),
) -> None:
    """병원 및 진료 기록을 삭제합니다 (작성자 본인만 가능)."""
    service.delete_hospital_visit(current_user_id, visit_id)
