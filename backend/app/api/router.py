from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.api.v1.endpoints import emotion_model, system
from app.core.config import get_settings

settings = get_settings()

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(emotion_model.router)
api_router.include_router(v1_router, prefix=settings.api_v1_prefix)
