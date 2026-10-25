from fastapi import APIRouter
from app.api.v1 import api_v1_router
from app.api.websockets import router as ws_router

api_router = APIRouter()
api_router.include_router(api_v1_router, prefix="/v1")
api_router.include_router(ws_router)

__all__ = ["api_router", "ws_router"]
