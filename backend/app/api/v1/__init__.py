from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.curation import router as curation_router
from app.api.v1.system import router as system_router

api_v1_router = APIRouter()
api_v1_router.include_router(projects_router)
api_v1_router.include_router(curation_router)
api_v1_router.include_router(system_router)

__all__ = ["api_v1_router"]
