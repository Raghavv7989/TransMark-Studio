from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api import api_router
from app.api.websockets import router as ws_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan lifecycle: init storage and teardown."""
    setup_logging()
    logger.info("Initializing TransMark backend services...")
    settings.init_storage()
    logger.info(f"Storage directories initialized at {settings.STORAGE_ROOT}")
    yield
    logger.info("TransMark backend services shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Grade AI Video Dubbing and Lip-Sync Platform Backend",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix="/api")
app.include_router(ws_router)  # Mounted at root level for /ws/progress/{job_id}


@app.get("/", tags=["Health"])
async def root():
    """Health check and platform status endpoint."""
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs",
        "storage_root": str(settings.STORAGE_ROOT),
        "demucs_model": settings.DEMUCS_MODEL,
        "demucs_device": settings.DEMUCS_DEVICE,
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
