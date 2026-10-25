from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Strict lifecycle states for video dubbing & lip-sync pipeline."""
    UPLOADING = "UPLOADING"
    SEPARATING_AUDIO = "SEPARATING_AUDIO"
    TRANSCRIBING = "TRANSCRIBING"
    CURATING_TRANSLATION = "CURATING_TRANSLATION"
    CLONING_VOICE = "CLONING_VOICE"
    LIP_SYNCING = "LIP_SYNCING"
    REMUXING = "REMUXING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobProgressUpdate(BaseModel):
    """Real-time progress notification schema pushed to WebSockets."""
    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current pipeline lifecycle phase")
    progress: float = Field(..., ge=0.0, le=100.0, description="Overall pipeline completion percentage (0-100)")
    subtask: str = Field(..., description="Human-readable subtask currently executing")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of the update")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed subtask metrics or payloads")
    error: Optional[str] = Field(default=None, description="Error message if status is FAILED")


class JobState(BaseModel):
    """Complete state snapshot of a job stored in the orchestrator."""
    job_id: str
    filename: str
    status: JobStatus = JobStatus.UPLOADING
    progress: float = 0.0
    subtask: str = "Job initialized"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input_file_path: Optional[str] = None
    target_language: str = "te"
    media_metadata: Optional[Dict[str, Any]] = None
    extraction_results: Optional[Dict[str, Any]] = None
    segments: Optional[list] = None
    final_video_path: Optional[str] = None
    master_audio_path: Optional[str] = None
    error: Optional[str] = None

    def update_progress(
        self,
        status: JobStatus,
        progress: float,
        subtask: str,
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> JobProgressUpdate:
        self.status = status
        self.progress = round(progress, 2)
        self.subtask = subtask
        self.updated_at = datetime.now(timezone.utc)
        if error:
            self.error = error
        return JobProgressUpdate(
            job_id=self.job_id,
            status=self.status,
            progress=self.progress,
            subtask=self.subtask,
            timestamp=self.updated_at,
            details=details,
            error=self.error,
        )
