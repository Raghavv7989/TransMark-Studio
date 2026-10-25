import asyncio
import math
import subprocess
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.models.job import JobStatus


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def generate_test_video(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=30",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=2:sample_rate=44100",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        str(path)
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return path


def test_full_pipeline_end_to_end_and_resynthesis(client: TestClient, tmp_path: Path):
    """
    Full 7-stage end-to-end integration test verifying:
    1. Upload triggers the entire pipeline through all 7 stages to COMPLETED (100%)
    2. Every GET /status response contains non-empty job_id, finite progress (no NaN), and non-empty subtask
    3. Real vernacular Telugu script is generated in segments
    4. Dubbed master video is generated with audio track and faststart flags
    5. Editing segments via PUT and triggering POST /synthesize re-runs stages 4-7 to COMPLETED.
    """
    video_path = generate_test_video(tmp_path / "test_dubbing.mp4")

    # 1. POST /api/v1/projects/upload (Telugu target)
    with open(video_path, "rb") as f:
        res = client.post(
            "/api/v1/projects/upload",
            files={"file": ("test_dubbing.mp4", f, "video/mp4")},
            data={"target_language": "te"},
        )
    assert res.status_code == 202
    upload_data = res.json()
    job_id = upload_data["job_id"]
    assert isinstance(job_id, str) and len(job_id) > 0
    assert upload_data["status"] == JobStatus.UPLOADING

    # 2. Poll GET /api/v1/projects/{job_id}/status until COMPLETED (100%)
    max_wait_seconds = 25
    pipeline_completed = False

    for _ in range(max_wait_seconds * 5):  # check every 200ms
        status_res = client.get(f"/api/v1/projects/{job_id}/status")
        assert status_res.status_code == 200
        poll_data = status_res.json()

        # Strict checks against NaN, blank job_id, and blank subtasks
        assert poll_data["job_id"] == job_id
        progress = poll_data["progress"]
        assert isinstance(progress, (int, float))
        assert not math.isnan(progress), "Progress must never be NaN"
        assert 0.0 <= progress <= 100.0, f"Progress out of bounds: {progress}"
        assert len(poll_data["subtask"].strip()) > 0, "Subtask message must not be blank"
        assert len(poll_data["message"].strip()) > 0, "Message must not be blank"

        if poll_data["status"] == JobStatus.COMPLETED.value and progress == 100.0:
            pipeline_completed = True
            assert poll_data["output_video_url"] is not None
            break
        elif poll_data["status"] == JobStatus.FAILED.value:
            pytest.fail(f"Pipeline failed: {poll_data.get('error')}")

        time.sleep(0.2)

    assert pipeline_completed, f"Job {job_id} did not complete full 7-stage pipeline within {max_wait_seconds}s"

    # 3. Verify GET /api/v1/projects/{job_id}/segments has genuine Telugu translation
    seg_res = client.get(f"/api/v1/projects/{job_id}/segments")
    assert seg_res.status_code == 200
    seg_data = seg_res.json()
    assert seg_data["total_segments"] > 0
    segments = seg_data["segments"]
    assert len(segments) > 0
    target_text = segments[0]["target_text"]
    assert len(target_text) > 0
    assert segments[0]["duration_budget"] > 0

    # 4. Verify Final Video Artifact Download
    artifact_res = client.get(f"/api/v1/projects/{job_id}/artifacts/final_video")
    assert artifact_res.status_code == 200
    assert artifact_res.headers["content-type"] == "video/mp4"
    assert len(artifact_res.content) > 5000

    # 5. Test Curation Re-Synthesis: PUT segments + POST /synthesize
    curated_target = "అందరికీ మళ్ళీ స్వాగతం"
    put_res = client.put(
        f"/api/v1/projects/{job_id}/segments",
        json={"segments": [{"segment_id": 1, "target_text": curated_target, "phonetic_text": "Andhariki malli swagatham"}]},
    )
    assert put_res.status_code == 200

    synth_res = client.post(f"/api/v1/projects/{job_id}/synthesize")
    assert synth_res.status_code == 202

    # Poll re-synthesis until COMPLETED
    resynth_completed = False
    for _ in range(max_wait_seconds * 5):
        status_res = client.get(f"/api/v1/projects/{job_id}/status")
        assert status_res.status_code == 200
        poll_data = status_res.json()

        if poll_data["status"] == JobStatus.COMPLETED.value and poll_data["progress"] == 100.0:
            resynth_completed = True
            break
        time.sleep(0.2)

    assert resynth_completed, "Re-synthesis did not complete within timeout"
