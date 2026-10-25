from typing import Optional
from pydantic import BaseModel, Field
from app.models.job import JobStatus
from app.models.media import MediaExtractionResult, VideoMetadata


class ProjectUploadResponse(BaseModel):
    """Response returned upon successful video upload and job initialization."""
    job_id: str = Field(..., description="Unique job identifier")
    filename: str = Field(..., description="Uploaded video filename")
    status: JobStatus = Field(default=JobStatus.UPLOADING, description="Initial job state")
    ws_url: str = Field(..., description="WebSocket progress stream URL")
    message: str = Field(..., description="Status summary message")


class ProjectStatusResponse(BaseModel):
    """Full status response for polling or initial WebSocket synchronization."""
    job_id: str
    filename: str
    status: JobStatus
    progress: float
    subtask: str
    metadata: Optional[VideoMetadata] = None
    extraction_results: Optional[MediaExtractionResult] = None
    final_video_path: Optional[str] = None
    master_audio_path: Optional[str] = None
    error: Optional[str] = None


class ProjectSynthesizeResponse(BaseModel):
    """Response returned upon triggering the synthesis and lip-sync pipeline."""
    job_id: str
    status: JobStatus
    ws_url: str
    message: str


class JobPollingStatusResponse(BaseModel):
    """Normalized polling status response compatible with both state and status schemas."""
    job_id: str
    status: JobStatus
    state: JobStatus
    progress: float
    subtask: str
    message: str
    output_video_url: Optional[str] = None
    segments: Optional[list] = None
    error: Optional[str] = None
