"""Service layer for Care Notebook (돌봄수첩) domain.

Includes business logic and manual Python-level authorization checks to compensate
for Supabase Service Role Key bypassing RLS.
"""

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.repositories import care_notes as repo
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


# ==========================================
# 0. Authorization Verification Helpers
# ==========================================


def validate_patient_access(user_id: UUID, patient_id: int) -> dict[str, Any]:
    """환자가 존재하고 요청한 사용자가 환자의 그룹 멤버인지 검증한다."""
    patient = repo.get_patient_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with id {patient_id} not found",
        )

    group_id = patient.get("group_id")
    if group_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient is not associated with any group",
        )

    if not repo.is_user_in_group(user_id, group_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: user is not a member of the patient's group",
        )

    return patient


def validate_record_author(record_user_id: str | UUID, current_user_id: UUID) -> None:
    """기록의 작성자 본인인지 검증한다 (수정/삭제 권한 제한)."""
    if str(record_user_id) != str(current_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only the author can modify or delete this record",
        )


# ==========================================
# 1. Daily Conditions (오늘의 환자 상태)
# ==========================================


def create_daily_condition(
    user_id: UUID, schema: DailyConditionCreate
) -> DailyConditionResponse:
    """오늘 상태 작성."""
    validate_patient_access(user_id, schema.patient_id)

    payload = {
        "patient_id": schema.patient_id,
        "user_id": str(user_id),
        "record_date": schema.record_date.isoformat(),
        "meal_status": schema.meal_status.value if hasattr(schema.meal_status, "value") else schema.meal_status,
        "sleep_status": schema.sleep_status.value if hasattr(schema.sleep_status, "value") else schema.sleep_status,
        "bowel_status": schema.bowel_status.value if hasattr(schema.bowel_status, "value") else schema.bowel_status,
        "activity_status": schema.activity_status.value if hasattr(schema.activity_status, "value") else schema.activity_status,
        "mood_status": schema.mood_status,
        "cognitive_status": schema.cognitive_status.value if hasattr(schema.cognitive_status, "value") else schema.cognitive_status,
        "behavior_change": schema.behavior_change,
        "medication_status": schema.medication_status.value if hasattr(schema.medication_status, "value") else schema.medication_status,
        "note": schema.note,
    }

    record = repo.create_daily_condition(payload)
    return DailyConditionResponse.model_validate(record)


def get_daily_condition(user_id: UUID, condition_id: int) -> DailyConditionResponse:
    """오늘 상태 단건 조회."""
    record = repo.get_daily_condition_by_id(condition_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily condition with id {condition_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    return DailyConditionResponse.model_validate(record)


def list_daily_conditions(
    user_id: UUID,
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[DailyConditionResponse]:
    """오늘 상태 목록 조회."""
    validate_patient_access(user_id, patient_id)
    records = repo.list_daily_conditions(patient_id, start_date, end_date)
    return [DailyConditionResponse.model_validate(r) for r in records]


def update_daily_condition(
    user_id: UUID, condition_id: int, schema: DailyConditionUpdate
) -> DailyConditionResponse:
    """오늘 상태 수정 (작성자 본인 검증)."""
    record = repo.get_daily_condition_by_id(condition_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily condition with id {condition_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)

    update_data = schema.model_dump(exclude_unset=True)
    if not update_data:
        return DailyConditionResponse.model_validate(record)

    # Enum 객체가 남아있는 경우 Enum.value로 변환
    for key, val in list(update_data.items()):
        if hasattr(val, "value"):
            update_data[key] = val.value

    updated_record = repo.update_daily_condition(condition_id, update_data)
    return DailyConditionResponse.model_validate(updated_record)


def delete_daily_condition(user_id: UUID, condition_id: int) -> None:
    """오늘 상태 삭제 (작성자 본인 검증)."""
    record = repo.get_daily_condition_by_id(condition_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Daily condition with id {condition_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)
    repo.delete_daily_condition(condition_id)


# ==========================================
# 2. Behavior Logs (행동 및 증상 기록)
# ==========================================


def create_behavior_log(user_id: UUID, schema: BehaviorLogCreate) -> BehaviorLogResponse:
    """행동/증상 기록 생성."""
    validate_patient_access(user_id, schema.patient_id)

    payload = {
        "patient_id": schema.patient_id,
        "user_id": str(user_id),
        "behavior_type": schema.behavior_type,
        "memo": schema.memo,
        "occurred_at": schema.occurred_at.isoformat(),
    }

    record = repo.create_behavior_log(payload)
    return BehaviorLogResponse.model_validate(record)


def get_behavior_log(user_id: UUID, log_id: int) -> BehaviorLogResponse:
    """행동/증상 기록 단건 조회."""
    record = repo.get_behavior_log_by_id(log_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavior log with id {log_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    return BehaviorLogResponse.model_validate(record)


def list_behavior_logs(
    user_id: UUID,
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[BehaviorLogResponse]:
    """행동/증상 기록 목록 조회."""
    validate_patient_access(user_id, patient_id)
    records = repo.list_behavior_logs(patient_id, start_date, end_date)
    return [BehaviorLogResponse.model_validate(r) for r in records]


def update_behavior_log(
    user_id: UUID, log_id: int, schema: BehaviorLogUpdate
) -> BehaviorLogResponse:
    """행동/증상 기록 수정 (작성자 본인 검증)."""
    record = repo.get_behavior_log_by_id(log_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavior log with id {log_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)

    update_data = schema.model_dump(exclude_unset=True)
    if "occurred_at" in update_data and update_data["occurred_at"]:
        update_data["occurred_at"] = update_data["occurred_at"].isoformat()

    if not update_data:
        return BehaviorLogResponse.model_validate(record)

    updated_record = repo.update_behavior_log(log_id, update_data)
    return BehaviorLogResponse.model_validate(updated_record)


def delete_behavior_log(user_id: UUID, log_id: int) -> None:
    """행동/증상 기록 삭제 (작성자 본인 검증)."""
    record = repo.get_behavior_log_by_id(log_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Behavior log with id {log_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)
    repo.delete_behavior_log(log_id)


# ==========================================
# 3. Medications (복약 목록)
# ==========================================


def create_medication(user_id: UUID, schema: MedicationCreate) -> MedicationResponse:
    """복약 항목 등록."""
    validate_patient_access(user_id, schema.patient_id)

    payload = {
        "patient_id": schema.patient_id,
        "medication_name": schema.medication_name,
        "dosage": schema.dosage,
        "time_of_day": schema.time_of_day,
        "start_date": schema.start_date.isoformat(),
        "end_date": schema.end_date.isoformat() if schema.end_date else None,
        "note": schema.note,
        "is_active": schema.is_active,
    }

    record = repo.create_medication(payload)
    return MedicationResponse.model_validate(record)


def get_medication(user_id: UUID, medication_id: int) -> MedicationResponse:
    """복약 항목 단건 조회."""
    record = repo.get_medication_by_id(medication_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication with id {medication_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    return MedicationResponse.model_validate(record)


def list_medications(
    user_id: UUID, patient_id: int, is_active: bool | None = None
) -> list[MedicationResponse]:
    """복약 항목 목록 조회."""
    validate_patient_access(user_id, patient_id)
    records = repo.list_medications(patient_id, is_active)
    return [MedicationResponse.model_validate(r) for r in records]


def update_medication(
    user_id: UUID, medication_id: int, schema: MedicationUpdate
) -> MedicationResponse:
    """복약 항목 수정 (그룹 멤버 권한)."""
    record = repo.get_medication_by_id(medication_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication with id {medication_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])

    update_data = schema.model_dump(exclude_unset=True)
    if "start_date" in update_data and update_data["start_date"]:
        update_data["start_date"] = update_data["start_date"].isoformat()
    if "end_date" in update_data and update_data["end_date"]:
        update_data["end_date"] = update_data["end_date"].isoformat()

    if not update_data:
        return MedicationResponse.model_validate(record)

    updated_record = repo.update_medication(medication_id, update_data)
    return MedicationResponse.model_validate(updated_record)


def delete_medication(user_id: UUID, medication_id: int) -> None:
    """복약 항목 삭제."""
    record = repo.get_medication_by_id(medication_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication with id {medication_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    repo.delete_medication(medication_id)


# ==========================================
# 4. Medication Intake Logs (일별 복용 여부)
# ==========================================


def create_or_update_intake_log(
    user_id: UUID, schema: MedicationIntakeLogCreate
) -> MedicationIntakeLogResponse:
    """일별 복용 여부 기록 등록 또는 업데이트 (Upsert)."""
    medication = repo.get_medication_by_id(schema.medication_id)
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication with id {schema.medication_id} not found",
        )

    validate_patient_access(user_id, medication["patient_id"])

    status_val = schema.status.value if hasattr(schema.status, "value") else schema.status
    taken_at_val = schema.taken_at.isoformat() if schema.taken_at else None

    existing = repo.get_medication_intake_log_by_medication_and_date(
        schema.medication_id, schema.log_date
    )

    if existing:
        payload = {"status": status_val, "taken_at": taken_at_val}
        record = repo.update_medication_intake_log(existing["id"], payload)
    else:
        payload = {
            "medication_id": schema.medication_id,
            "log_date": schema.log_date.isoformat(),
            "status": status_val,
            "taken_at": taken_at_val,
        }
        record = repo.create_medication_intake_log(payload)

    return MedicationIntakeLogResponse.model_validate(record)


def list_intake_logs_for_patient(
    user_id: UUID,
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MedicationIntakeLogResponse]:
    """환자의 전체 복약 항목에 대한 일별 복용 여부 목록 조회."""
    validate_patient_access(user_id, patient_id)
    medications = repo.list_medications(patient_id)
    medication_ids = [m["id"] for m in medications]

    if not medication_ids:
        return []

    records = repo.list_medication_intake_logs(medication_ids, start_date, end_date)
    return [MedicationIntakeLogResponse.model_validate(r) for r in records]


def update_intake_log(
    user_id: UUID, log_id: int, schema: MedicationIntakeLogUpdate
) -> MedicationIntakeLogResponse:
    """일별 복용 여부 수정."""
    record = repo.get_medication_intake_log_by_id(log_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication intake log with id {log_id} not found",
        )

    medication = repo.get_medication_by_id(record["medication_id"])
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated medication not found",
        )

    validate_patient_access(user_id, medication["patient_id"])

    update_data = schema.model_dump(exclude_unset=True)
    if "status" in update_data and hasattr(update_data["status"], "value"):
        update_data["status"] = update_data["status"].value
    if "taken_at" in update_data and update_data["taken_at"]:
        update_data["taken_at"] = update_data["taken_at"].isoformat()

    if not update_data:
        return MedicationIntakeLogResponse.model_validate(record)

    updated_record = repo.update_medication_intake_log(log_id, update_data)
    return MedicationIntakeLogResponse.model_validate(updated_record)


def delete_intake_log(user_id: UUID, log_id: int) -> None:
    """일별 복용 여부 삭제."""
    record = repo.get_medication_intake_log_by_id(log_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Medication intake log with id {log_id} not found",
        )

    medication = repo.get_medication_by_id(record["medication_id"])
    if not medication:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated medication not found",
        )

    validate_patient_access(user_id, medication["patient_id"])
    repo.delete_medication_intake_log(log_id)


# ==========================================
# 5. Hospital Visits (병원 및 진료 기록)
# ==========================================


def create_hospital_visit(
    user_id: UUID, schema: HospitalVisitCreate
) -> HospitalVisitResponse:
    """병원 진료 기록 생성."""
    validate_patient_access(user_id, schema.patient_id)

    payload = {
        "patient_id": schema.patient_id,
        "user_id": str(user_id),
        "visit_date": schema.visit_date.isoformat(),
        "hospital_name": schema.hospital_name,
        "department": schema.department,
        "visit_reason": schema.visit_reason,
        "message_to_doctor": schema.message_to_doctor,
        "doctor_instructions": schema.doctor_instructions,
        "medication_changed": schema.medication_changed,
        "next_visit_date": schema.next_visit_date.isoformat() if schema.next_visit_date else None,
        "guardian_memo": schema.guardian_memo,
    }

    record = repo.create_hospital_visit(payload)
    return HospitalVisitResponse.model_validate(record)


def get_hospital_visit(user_id: UUID, visit_id: int) -> HospitalVisitResponse:
    """병원 진료 기록 단건 조회."""
    record = repo.get_hospital_visit_by_id(visit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital visit with id {visit_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    return HospitalVisitResponse.model_validate(record)


def list_hospital_visits(
    user_id: UUID,
    patient_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[HospitalVisitResponse]:
    """병원 진료 기록 목록 조회."""
    validate_patient_access(user_id, patient_id)
    records = repo.list_hospital_visits(patient_id, start_date, end_date)
    return [HospitalVisitResponse.model_validate(r) for r in records]


def update_hospital_visit(
    user_id: UUID, visit_id: int, schema: HospitalVisitUpdate
) -> HospitalVisitResponse:
    """병원 진료 기록 수정 (작성자 본인 검증)."""
    record = repo.get_hospital_visit_by_id(visit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital visit with id {visit_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)

    update_data = schema.model_dump(exclude_unset=True)
    if "visit_date" in update_data and update_data["visit_date"]:
        update_data["visit_date"] = update_data["visit_date"].isoformat()
    if "next_visit_date" in update_data and update_data["next_visit_date"]:
        update_data["next_visit_date"] = update_data["next_visit_date"].isoformat()

    if not update_data:
        return HospitalVisitResponse.model_validate(record)

    updated_record = repo.update_hospital_visit(visit_id, update_data)
    return HospitalVisitResponse.model_validate(updated_record)


def delete_hospital_visit(user_id: UUID, visit_id: int) -> None:
    """병원 진료 기록 삭제 (작성자 본인 검증)."""
    record = repo.get_hospital_visit_by_id(visit_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital visit with id {visit_id} not found",
        )

    validate_patient_access(user_id, record["patient_id"])
    validate_record_author(record["user_id"], user_id)
    repo.delete_hospital_visit(visit_id)
