"""Unit tests for Care Notebook (돌봄수첩) schemas, services, and endpoints."""

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.care_notes import (
    ActivityStatus,
    BehaviorLogCreate,
    BowelStatus,
    CognitiveStatus,
    DailyConditionCreate,
    HospitalVisitCreate,
    MealStatus,
    MedicationCreate,
    MedicationIntakeLogCreate,
    MedicationStatus,
    SleepStatus,
)
from app.services import care_notes as service


def test_care_notes_schemas_validation():
    """Schemas validation and enum parsing tests."""
    dc = DailyConditionCreate(
        patient_id=1,
        record_date=date(2026, 9, 7),
        meal_status=MealStatus.GREAT,
        sleep_status=SleepStatus.NORMAL,
        bowel_status=BowelStatus.NORMAL,
        activity_status=ActivityStatus.NORMAL,
        mood_status="평온함",
        cognitive_status=CognitiveStatus.NORMAL,
        behavior_change=False,
        medication_status=MedicationStatus.COMPLETED,
        note="이상 없음",
    )
    assert dc.meal_status == MealStatus.GREAT
    assert dc.mood_status == "평온함"

    with pytest.raises(ValidationError):
        DailyConditionCreate(
            patient_id=1,
            record_date=date(2026, 9, 7),
            meal_status="INVALID_STATUS",  # Enum constraint validation
            sleep_status=SleepStatus.NORMAL,
            bowel_status=BowelStatus.NORMAL,
            activity_status=ActivityStatus.NORMAL,
            mood_status="평온함",
            cognitive_status=CognitiveStatus.NORMAL,
            behavior_change=False,
            medication_status=MedicationStatus.COMPLETED,
        )


def test_behavior_log_schema():
    """Behavior log schema test."""
    now = datetime.now(timezone.utc)
    bl = BehaviorLogCreate(
        patient_id=1,
        behavior_type="배회",
        occurred_at=now,
        memo="야간 배회 증상",
    )
    assert bl.behavior_type == "배회"
    assert bl.occurred_at == now


def test_medication_schema():
    """Medication schema test."""
    med = MedicationCreate(
        patient_id=1,
        medication_name="아리셉트정 5mg",
        dosage="1정",
        time_of_day="아침 식후 30분",
        start_date=date(2026, 1, 1),
        is_active=True,
    )
    assert med.medication_name == "아리셉트정 5mg"
    assert med.is_active is True


def test_medication_intake_log_schema():
    """Medication intake log schema test."""
    log = MedicationIntakeLogCreate(
        medication_id=10,
        log_date=date(2026, 9, 7),
        status=MedicationStatus.COMPLETED,
        taken_at=datetime.now(timezone.utc),
    )
    assert log.status == MedicationStatus.COMPLETED


def test_hospital_visit_schema():
    """Hospital visit schema test."""
    hv = HospitalVisitCreate(
        patient_id=1,
        visit_date=date(2026, 9, 7),
        hospital_name="서울대학교병원",
        department="신경과",
        visit_reason="정기 검진",
        medication_changed=False,
    )
    assert hv.hospital_name == "서울대학교병원"
    assert hv.department == "신경과"


def test_author_validation_logic():
    """Author authorization check helper test."""
    u1 = uuid4()
    u2 = uuid4()

    # Same user should not raise
    service.validate_record_author(u1, u1)

    # Different user should raise 403 Forbidden
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        service.validate_record_author(u1, u2)
    assert exc_info.value.status_code == 403
