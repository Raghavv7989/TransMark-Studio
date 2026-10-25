import shutil
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
import aiofiles

from app.core.config import settings
from app.core.logging import get_logger
from app.models.job import JobStatus
from app.models.media import MediaExtractionResult, VideoMetadata
from app.models.project import (
    ProjectStatusResponse,
    ProjectUploadResponse,
    ProjectSynthesizeResponse,
    JobPollingStatusResponse,
)
from app.services.orchestrator import orchestrator

logger = get_logger("api_projects")
router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/upload", response_model=ProjectUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_video(
    file: UploadFile = File(...),
    target_language: str = Form("te"),
):
    """
    Accepts a video file upload, assigns a unique job_id,
    triggers the lossless media extraction pipeline asynchronously,
    and returns connection metadata for real-time WebSocket progress tracking.
    """
    # 1. Validate file extension
    original_filename = file.filename or "uploaded_video.mp4"
    file_ext = Path(original_filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{file_ext}'. Allowed extensions: {settings.ALLOWED_EXTENSIONS}",
        )

    # 2. Prepare storage destination
    temp_filename = f"{original_filename}"
    raw_save_path = settings.RAW_STORAGE / f"temp_{original_filename}"
    settings.RAW_STORAGE.mkdir(parents=True, exist_ok=True)

    # 3. Stream upload asynchronously in chunks
    try:
        async with aiofiles.open(raw_save_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                await out_file.write(chunk)
    except Exception as e:
        logger.error(f"Failed to stream upload to disk: {e}")
        if raw_save_path.exists():
            raw_save_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to write uploaded file to storage: {str(e)}",
        )

    # 4. Initialize job in orchestrator
    job = await orchestrator.create_job(
        filename=original_filename,
        input_file_path=raw_save_path,
        target_language=target_language,
    )
    job_id = job.job_id

    # Rename file with job_id prefix for immutability
    final_raw_path = settings.RAW_STORAGE / f"{job_id}_{original_filename}"
    raw_save_path.rename(final_raw_path)
    job.input_file_path = str(final_raw_path)

    # 5. Kick off asynchronous extraction and separation pipeline
    orchestrator.trigger_pipeline(job_id)

    ws_url = f"/ws/progress/{job_id}"
    logger.info(f"Video uploaded successfully. Job {job_id} scheduled. Progress available at {ws_url}")

    return ProjectUploadResponse(
        job_id=job_id,
        filename=original_filename,
        status=JobStatus.UPLOADING,
        ws_url=ws_url,
        message="Video received successfully. Demuxing and audio separation initiated.",
    )


@router.get("/{job_id}", response_model=ProjectStatusResponse)
async def get_project_status(job_id: str):
    """Retrieve current job execution status, metadata, and extracted stems."""
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    meta = VideoMetadata(**job.media_metadata) if job.media_metadata else None
    results = MediaExtractionResult(**job.extraction_results) if job.extraction_results else None

    return ProjectStatusResponse(
        job_id=job.job_id,
        filename=job.filename,
        status=job.status,
        progress=job.progress,
        subtask=job.subtask,
        metadata=meta,
        extraction_results=results,
        error=job.error,
    )


@router.get("/{job_id}/status", response_model=JobPollingStatusResponse)
async def poll_project_status(job_id: str):
    """
    Lightweight polling endpoint returning real-time progress and completion state.
    Designed for frontend polling fallbacks when WebSockets buffer or disconnect.
    """
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    # Check for completed artifacts on disk to heal recovered or restarted state
    final_vid_cand = Path(job.final_video_path) if job.final_video_path else (settings.get_job_storage(job_id)["output_dir"] / f"{job_id}_final_dubbed.mp4")
    if final_vid_cand.exists():
        if not job.final_video_path or job.status != JobStatus.COMPLETED:
            job.final_video_path = str(final_vid_cand)
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.subtask = "Dubbing & Lip-Sync pipeline completed successfully. Master video ready."
            job.error = None

    output_url = f"/api/v1/projects/{job.job_id}/artifacts/final_video" if job.final_video_path else None

    return JobPollingStatusResponse(
        job_id=job.job_id,
        status=job.status,
        state=job.status,
        progress=job.progress,
        subtask=job.subtask,
        message=job.subtask,
        output_video_url=output_url,
        segments=job.segments,
        error=job.error,
    )


@router.post("/{job_id}/synthesize", response_model=ProjectSynthesizeResponse, status_code=status.HTTP_202_ACCEPTED)
async def synthesize_project(job_id: str):
    """
    Trigger voice cloning, dynamic audio time-alignment, zero-damage lip-sync,
    and final remuxing pipeline for a curated project.
    Progress is streamed live over WS /ws/progress/{job_id}.
    """
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    if not job.extraction_results or not job.segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job {job_id} is not ready for synthesis. Segments or extraction stems missing.",
        )

    orchestrator.trigger_synthesis(job_id)
    ws_url = f"/ws/progress/{job_id}"

    return ProjectSynthesizeResponse(
        job_id=job_id,
        status=JobStatus.CLONING_VOICE,
        ws_url=ws_url,
        message="Voice cloning, zero-damage lip-sync, and remuxing initiated.",
    )


@router.get("/{job_id}/artifacts/{artifact_type}")
async def download_artifact(job_id: str, artifact_type: str):
    """
    Download pipeline output artifacts:
    - 'final_video': Fully dubbed, zero-damage lip-synced final master video (CRF 18)
    - 'master_audio': Master dialogue mixed with original ambient background
    - 'video': Lossless silent video stream
    - 'vocals_asr': 16kHz mono vocal audio stem
    - 'vocals_clone': 44.1kHz stereo vocal audio stem
    - 'background': 44.1kHz stereo ambient audio stem
    """
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    artifact_map = {}
    if job.extraction_results:
        ext = job.extraction_results
        if ext.get("lossless_video_path"):
            artifact_map["video"] = (ext["lossless_video_path"], "video/mp4")
        if ext.get("vocals_asr_path"):
            artifact_map["vocals_asr"] = (ext["vocals_asr_path"], "audio/wav")
        if ext.get("vocals_clone_path"):
            artifact_map["vocals_clone"] = (ext["vocals_clone_path"], "audio/wav")
        if ext.get("background_path"):
            artifact_map["background"] = (ext["background_path"], "audio/wav")

    if job.final_video_path:
        artifact_map["final_video"] = (job.final_video_path, "video/mp4")
    else:
        final_cand = settings.get_job_storage(job_id)["output_dir"] / f"{job_id}_final_dubbed.mp4"
        if final_cand.exists():
            artifact_map["final_video"] = (str(final_cand), "video/mp4")

    if job.master_audio_path:
        artifact_map["master_audio"] = (job.master_audio_path, "audio/wav")
    else:
        audio_cand = settings.get_job_storage(job_id)["output_dir"] / f"{job_id}_master_mixed.wav"
        if audio_cand.exists():
            artifact_map["master_audio"] = (str(audio_cand), "audio/wav")

    if artifact_type not in artifact_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid artifact type '{artifact_type}'. Choose from: {list(artifact_map.keys())}",
        )

    path_str, media_type = artifact_map[artifact_type]
    file_path = Path(path_str)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact file not found: {file_path.name}")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )


@router.get("/{job_id}/download")
async def download_final_video_alias(job_id: str):
    """Direct alias endpoint for downloading final dubbed video."""
    return await download_artifact(job_id, "final_video")
