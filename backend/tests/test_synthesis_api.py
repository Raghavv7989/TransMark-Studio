import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from app.models.job import JobStatus
from app.models.segment import IsochronicSegment
from app.services.orchestrator import orchestrator


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def synthesis_ready_job(tmp_path: Path):
    """Fixture creating a project with segments and media stems ready for synthesis."""
    job = asyncio.run(
        orchestrator.create_job(
            filename="synth_test.mp4",
            input_file_path=tmp_path / "synth_test.mp4",
            target_language="te",
        )
    )
    job.status = JobStatus.CURATING_TRANSLATION

    # Mock media extraction paths
    silent_vid = tmp_path / "lossless_silent.mp4"
    silent_vid.write_bytes(b"mock video")
    vocal_clone = tmp_path / "vocals_44k.wav"
    vocal_clone.write_bytes(b"mock vocal clone")
    bg_audio = tmp_path / "background.wav"
    bg_audio.write_bytes(b"mock background")

    job.extraction_results = {
        "job_id": job.job_id,
        "raw_video_path": str(tmp_path / "synth_test.mp4"),
        "lossless_video_path": str(silent_vid),
        "extracted_audio_path": str(vocal_clone),
        "vocals_asr_path": str(vocal_clone),
        "vocals_clone_path": str(vocal_clone),
        "background_path": str(bg_audio),
        "separation_method": "demucs",
        "metadata": {
            "duration_seconds": 2.5,
            "width": 640,
            "height": 360,
            "fps": 30.0,
            "total_frames": 75,
            "video_codec": "h264",
            "has_audio": True,
            "file_size_bytes": 1024,
        },
    }

    seg1 = IsochronicSegment(
        segment_id=1,
        start_time=0.0,
        end_time=2.0,
        start_ms=0,
        end_ms=2000,
        duration_budget=2.0,
        source_text="Welcome back",
        target_text="తిరిగి స్వాగతం",
        phonetic_text="Tirigi swagatham",
        original_syllables=3,
        target_syllables=5,
        pacing_ratio=1.66,
        fit_status="FITS",
        tolerance_pct=0.0,
        words=[],
    )
    job.segments = [seg1.model_dump()]
    return job


def test_synthesize_not_found(client: TestClient):
    """POST /synthesize returns 404 for non-existent job."""
    res = client.post("/api/v1/projects/non-existent-job-id/synthesize")
    assert res.status_code == 404


def test_synthesize_trigger_success(client: TestClient, synthesis_ready_job):
    """POST /synthesize triggers synthesis and returns 202 with ws_url."""
    job_id = synthesis_ready_job.job_id
    res = client.post(f"/api/v1/projects/{job_id}/synthesize")

    assert res.status_code == 202
    data = res.json()
    assert data["job_id"] == job_id
    assert data["status"] == JobStatus.CLONING_VOICE
    assert data["ws_url"] == f"/ws/progress/{job_id}"
    assert "initiated" in data["message"].lower()


def test_download_artifacts_after_synthesis(client: TestClient, synthesis_ready_job, tmp_path: Path):
    """Verify download endpoint for final_video and master_audio."""
    job_id = synthesis_ready_job.job_id

    # Create dummy final video & master audio
    dummy_final_vid = tmp_path / "final_dubbed.mp4"
    dummy_final_vid.write_bytes(b"dummy final dubbed video stream")
    dummy_master_aud = tmp_path / "master_mixed.wav"
    dummy_master_aud.write_bytes(b"dummy master audio wav")

    synthesis_ready_job.final_video_path = str(dummy_final_vid)
    synthesis_ready_job.master_audio_path = str(dummy_master_aud)

    # Test downloading final_video
    vid_res = client.get(f"/api/v1/projects/{job_id}/artifacts/final_video")
    assert vid_res.status_code == 200
    assert vid_res.content == b"dummy final dubbed video stream"

    # Test downloading master_audio
    aud_res = client.get(f"/api/v1/projects/{job_id}/artifacts/master_audio")
    assert aud_res.status_code == 200
    assert aud_res.content == b"dummy master audio wav"
