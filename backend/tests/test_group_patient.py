import pytest
from fastapi import HTTPException

from app.schemas.groups import GroupDetail
from app.services import groups


@pytest.mark.parametrize("patient", [None, {
    "id": 43, "patient_name": "환자", "patient_birth_date": "1950-01-02", "gender": "선택 안 함",
}])
def test_group_detail_includes_patient_after_membership_check(monkeypatch, patient):
    monkeypatch.setattr(groups.repository, "get_group", lambda group_id: {
        "id": group_id, "group_name": "가족", "invite_code": "INVITE",
        "created_at": "2026-10-28T00:00:00Z",
    })
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: True)
    monkeypatch.setattr(groups.repository, "count_members", lambda group_id: 1)
    monkeypatch.setattr(groups.repository, "get_members", lambda group_id: [])
    monkeypatch.setattr(groups.patient_repository, "get_patient_by_group_id", lambda group_id: patient)
    result = GroupDetail.model_validate(groups.get_group_detail("user-1", 7))
    assert (result.patient.id if result.patient else None) == (43 if patient else None)


def test_nonmember_cannot_query_patient(monkeypatch):
    monkeypatch.setattr(groups.repository, "get_group", lambda group_id: {"id": group_id})
    monkeypatch.setattr(groups.repository, "is_member", lambda group_id, user_id: False)
    def unexpected_query(group_id):
        pytest.fail("Patient lookup must follow the membership check")
    monkeypatch.setattr(groups.patient_repository, "get_patient_by_group_id", unexpected_query)
    with pytest.raises(HTTPException) as error:
        groups.get_group_detail("outsider", 7)
    assert error.value.status_code == 403
