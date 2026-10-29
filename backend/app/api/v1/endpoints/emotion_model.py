"""Operational endpoints for the emotion model (MLOps).

POST /reload-model is called by the training job after a new revision passes its
evaluation gate.  It is mounted at the root (not under /api/v1) and requires the
X-Reload-Token header to match EMOTION_MODEL_RELOAD_TOKEN.
"""

import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.integrations.ai.emotion_analyzer import current_model_info, reload_classifier

logger = logging.getLogger(__name__)

router = APIRouter(tags=["emotion-model"])


class ReloadRequest(BaseModel):
    revision: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9._-]+$")


@router.get("/model-info")
def model_info() -> dict:
    return current_model_info()


@router.post("/reload-model", status_code=status.HTTP_202_ACCEPTED)
def reload_model(
    body: ReloadRequest,
    background_tasks: BackgroundTasks,
    x_reload_token: str = Header(default=""),
) -> dict:
    expected = get_settings().emotion_model_reload_token
    if not expected:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Model reload is not configured")
    if not hmac.compare_digest(x_reload_token, expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid reload token")

    def _swap(revision: str) -> None:
        try:
            reload_classifier(revision)
        except Exception:
            logger.exception("Emotion model reload to %s failed; keeping the current model", revision)

    background_tasks.add_task(_swap, body.revision)
    return {"status": "processing", "from": current_model_info()["model_version"], "to": body.revision}
