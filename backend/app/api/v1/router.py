from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    care_notes,
    diaries,
    groups,
    letters,
    media,
    memories,
    patients,
    system,
    users,
)

router = APIRouter()
router.include_router(system.router)
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(diaries.router, prefix="/diaries", tags=["diaries"])
router.include_router(memories.router, prefix="/memories", tags=["memories"])
router.include_router(care_notes.router, prefix="/care-notes", tags=["care-notes"])
router.include_router(letters.router, prefix="/letters", tags=["letters"])
router.include_router(media.router, prefix="/media", tags=["media"])

