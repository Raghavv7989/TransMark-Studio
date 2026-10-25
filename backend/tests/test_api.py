import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.config import settings
from app.models.job import JobStatus


@pytest.fixture
def client():
    """FastAPI test client."""
    with TestClient(app) as c:
        yield c


def test_health_check(client: TestClient):
    """Verify system health endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "TransMark" in data["platform"]


def test_system_health_telemetry(client: TestClient):
    """Verify detailed /api/v1/system/health telemetry endpoint."""
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "hardware_accelerator" in data
    assert data["hardware_accelerator"] in ["cuda", "mps", "cpu"]
    assert "engines" in data
    engines = data["engines"]
    for expected_engine in ["demux", "asr", "translation", "voice_cloning", "lipsync"]:
        assert expected_engine in engines
        assert "name" in engines[expected_engine]
        assert "mode" in engines[expected_engine]
        assert engines[expected_engine]["mode"] in ["LIVE_PRODUCTION", "LOCAL_FALLBACK", "FFMPEG_FALLBACK"]


def test_upload_invalid_extension(client: TestClient, tmp_path: Path):
    """Verify rejection of non-video file types."""
    invalid_file = tmp_path / "document.txt"
    invalid_file.write_text("not a video")

    with open(invalid_file, "rb") as f:
        response = client.post(
            "/api/v1/projects/upload",
            files={"file": ("document.txt", f, "text/plain")},
        )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_video_and_websocket_stream(client: TestClient, tmp_path: Path):
    """Test video upload endpoint and verify WebSocket receives progress updates."""
    # Create small valid dummy video file
    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1mp41")

    with open(video_file, "rb") as f:
        response = client.post(
            "/api/v1/projects/upload",
            files={"file": ("sample.mp4", f, "video/mp4")},
        )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == JobStatus.UPLOADING
    assert data["ws_url"].startswith("/ws/progress/")

    job_id = data["job_id"]

    # Test GET job status endpoint
    get_res = client.get(f"/api/v1/projects/{job_id}")
    assert get_res.status_code == 200
    job_info = get_res.json()
    assert job_info["job_id"] == job_id
    assert job_info["filename"] == "sample.mp4"

    # Test WebSocket connection and initial message receipt
    with client.websocket_connect(f"/ws/progress/{job_id}") as websocket:
        initial_msg = websocket.receive_json()
        assert initial_msg["job_id"] == job_id
        assert initial_msg["status"] in [status.value for status in JobStatus]
        assert "progress" in initial_msg

        # Test heartbeat
        websocket.send_text("ping")
        pong_msg = websocket.receive_json()
        assert pong_msg.get("type") == "pong"
