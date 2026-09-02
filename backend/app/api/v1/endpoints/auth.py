from fastapi import APIRouter, HTTPException, status

from app.schemas.users import LoginRequest, LoginResponse, SignupRequest, SignupResponse
from app.services.users import login_user, signup_user

router = APIRouter(tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest) -> SignupResponse:
    try:
        data = signup_user(
            email=str(payload.email),
            password=payload.password,
            name=payload.name,
            phone_number=payload.phone_number,
        )
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail="Signup failed") from exc

    user = data["user"]
    return SignupResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    try:
        data = login_user(email=str(payload.email), password=payload.password)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=500, detail="Authentication failed") from exc

    return LoginResponse(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
    )
