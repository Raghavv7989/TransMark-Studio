from typing import List
from fastapi import APIRouter, HTTPException, status

from app.core.logging import get_logger
from app.core.ws_manager import ws_manager
from app.models.job import JobProgressUpdate, JobStatus
from app.models.segment import (
    IsochronicSegment,
    SegmentsBatchUpdateRequest,
    SegmentsBatchUpdateResponse,
    SegmentsListResponse,
)
from app.services.orchestrator import orchestrator
from app.services.syllables import syllable_estimator

logger = get_logger("api_curation")
router = APIRouter(prefix="/projects", tags=["curation"])


@router.get("/{job_id}/segments", response_model=SegmentsListResponse)
async def get_project_segments(job_id: str):
    """
    Retrieve all time-coded phrasing segments for human curation and review.
    Returns:
    - segment_id, start_time, end_time, source_text, target_text, phonetic_text, duration_budget,
      syllable counts, pacing ratio, and fit status.
    """
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    if not job.segments:
        # Check if job is still processing earlier phases
        if job.status in [JobStatus.UPLOADING, JobStatus.SEPARATING_AUDIO]:
            raise HTTPException(
                status_code=status.HTTP_425_TOO_EARLY,
                detail=f"Job {job_id} is currently at state '{job.status.value}'. Segments are not generated yet.",
            )
        return SegmentsListResponse(
            job_id=job.job_id,
            target_language=job.target_language,
            total_segments=0,
            all_fit=True,
            segments=[],
        )

    segment_models = [IsochronicSegment(**s) for s in job.segments]
    all_fit = all(s.fit_status == "FITS" for s in segment_models)

    return SegmentsListResponse(
        job_id=job.job_id,
        target_language=job.target_language,
        total_segments=len(segment_models),
        all_fit=all_fit,
        segments=segment_models,
    )


@router.put("/{job_id}/segments", response_model=SegmentsBatchUpdateResponse)
async def update_project_segments(job_id: str, payload: SegmentsBatchUpdateRequest):
    """
    Human-in-the-loop editing endpoint:
    Allows user/frontend to modify target text or phonetic words for any segment.
    Automatically recalculates syllable pacing, ratio, and verifies if the edited text
    fits within the duration budget.
    """
    job = await orchestrator.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    if not job.segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No segments exist on job {job_id} to update.",
        )

    # Index existing segments
    segments_by_id = {s["segment_id"]: IsochronicSegment(**s) for s in job.segments}
    updated_count = 0

    for edit in payload.segments:
        if edit.segment_id not in segments_by_id:
            logger.warning(f"Segment ID {edit.segment_id} not found in job {job_id}. Skipping.")
            continue

        target_seg = segments_by_id[edit.segment_id]

        # 1. Update target text and recalculate syllables
        if edit.target_text is not None:
            new_target_text = edit.target_text.strip()
            target_seg.target_text = new_target_text

            # Recalculate syllables
            new_syllables = syllable_estimator.count_syllables(new_target_text)
            fit_status, pacing_ratio, tolerance_pct = syllable_estimator.evaluate_fit(
                original_syllables=target_seg.original_syllables,
                target_syllables=new_syllables,
                duration_seconds=target_seg.duration_budget,
            )

            target_seg.target_syllables = new_syllables
            target_seg.pacing_ratio = pacing_ratio
            target_seg.fit_status = fit_status
            target_seg.tolerance_pct = tolerance_pct

        # 2. Update phonetic text
        if edit.phonetic_text is not None:
            target_seg.phonetic_text = edit.phonetic_text.strip()
            # If target text was empty or latin, update target syllables if zero
            if target_seg.target_syllables == 0:
                p_syll = syllable_estimator.count_syllables(target_seg.phonetic_text)
                fit_status, pacing_ratio, tolerance_pct = syllable_estimator.evaluate_fit(
                    original_syllables=target_seg.original_syllables,
                    target_syllables=p_syll,
                    duration_seconds=target_seg.duration_budget,
                )
                target_seg.target_syllables = p_syll
                target_seg.pacing_ratio = pacing_ratio
                target_seg.fit_status = fit_status
                target_seg.tolerance_pct = tolerance_pct

        # 3. Update word breakdowns if provided
        if edit.words is not None:
            target_seg.words = edit.words

        target_seg.is_curated = True
        updated_count += 1

    # Persist updated segment list onto job state
    updated_segments_list = [segments_by_id[s_id] for s_id in sorted(segments_by_id.keys())]
    job.segments = [s.model_dump() for s in updated_segments_list]

    all_fit = all(s.fit_status == "FITS" for s in updated_segments_list)

    # Broadcast notification to WebSocket subscribers
    await ws_manager.broadcast(
        job_id=job_id,
        update=JobProgressUpdate(
            job_id=job_id,
            status=job.status,
            progress=job.progress,
            subtask=f"Human curation updated {updated_count} segment(s). All fit budget: {all_fit}",
            details={"updated_count": updated_count, "all_fit": all_fit},
        ),
    )

    return SegmentsBatchUpdateResponse(
        job_id=job.job_id,
        updated_count=updated_count,
        all_fit=all_fit,
        segments=updated_segments_list,
        message=f"Successfully curated {updated_count} segment(s). Time budget fit: {all_fit}",
    )
