from fastapi import APIRouter, Depends

from app.core.security import AuthenticatedUser, get_current_user
from app.schemas.patients import PatientResponse, PatientUpdate
from app.services import patients as service

router = APIRouter()


def user_id(current_user: AuthenticatedUser) -> str:
    return str(current_user.id)


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: int, current_user: AuthenticatedUser = Depends(get_current_user)):
    return service.get_patient(user_id(current_user), patient_id)


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    return service.update_patient(
        user_id(current_user), patient_id, payload.model_dump(exclude_unset=True)
    )
