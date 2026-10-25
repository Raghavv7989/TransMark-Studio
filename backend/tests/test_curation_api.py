import asyncio
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from main import app
from app.models.job import JobStatus
from app.models.segment import IsochronicSegment, WordTimestamp
from app.services.orchestrator import orchestrator


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_job():
    """Create a sample job with initialized time-coded segments for curation tests."""
    job = asyncio.run(
        orchestrator.create_job(
            filename="curation_test.mp4",
            input_file_path=Path("/tmp/curation_test.mp4"),
            target_language="te",
        )
    )
    job.status = JobStatus.CURATING_TRANSLATION

    seg1 = IsochronicSegment(
        segment_id=1,
        start_time=0.0,
        end_time=2.0,
        start_ms=0,
        end_ms=2000,
        duration_budget=2.0,
        source_text="Hey everyone, welcome back",
        target_text="హే అందరికీ తిరిగి స్వాగతం",
        phonetic_text="Hey andhariki tirigi swagatham",
        original_syllables=8,
        target_syllables=9,
        pacing_ratio=1.12,
        fit_status="FITS",
        tolerance_pct=12.5,
        speaker_id="SPEAKER_00",
        words=[
            WordTimestamp(word="Hey", start_ms=0, end_ms=300, start_time=0.0, end_time=0.3, confidence=0.98),
            WordTimestamp(word="everyone,", start_ms=350, end_ms=1000, start_time=0.35, end_time=1.0, confidence=0.97),
            WordTimestamp(word="welcome", start_ms=1100, end_ms=1600, start_time=1.1, end_time=1.6, confidence=0.99),
            WordTimestamp(word="back", start_ms=1650, end_ms=2000, start_time=1.65, end_time=2.0, confidence=0.99),
        ],
        is_curated=False,
    )

    seg2 = IsochronicSegment(
        segment_id=2,
        start_time=2.5,
        end_time=5.0,
        start_ms=2500,
        end_ms=5000,
        duration_budget=2.5,
        source_text="to the channel today.",
        target_text="ఈ రోజు మన ఛానెల్‌కి",
        phonetic_text="ee roju mana channel ki",
        original_syllables=6,
        target_syllables=6,
        pacing_ratio=1.0,
        fit_status="FITS",
        tolerance_pct=0.0,
        speaker_id="SPEAKER_00",
        words=[],
        is_curated=False,
    )

    job.segments = [seg1.model_dump(), seg2.model_dump()]
    return job


def test_get_segments_not_found(client: TestClient):
    """GET /segments returns 404 for non-existent job."""
    res = client.get("/api/v1/projects/non-existent-id/segments")
    assert res.status_code == 404


def test_get_and_put_curated_segments(client: TestClient, sample_job):
    """
    Test retrieving segments via GET and updating words/target_text via PUT,
    verifying automatic recalculation of syllable budget fit.
    """
    job_id = sample_job.job_id

    # 1. GET /api/v1/projects/{job_id}/segments
    get_res = client.get(f"/api/v1/projects/{job_id}/segments")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["job_id"] == job_id
    assert data["total_segments"] == 2
    assert data["target_language"] == "te"

    seg1 = data["segments"][0]
    assert seg1["segment_id"] == 1
    assert seg1["duration_budget"] == 2.0
    assert seg1["source_text"] == "Hey everyone, welcome back"
    assert "హే" in seg1["target_text"]
    assert seg1["fit_status"] == "FITS"

    # 2. PUT /api/v1/projects/{job_id}/segments (Editing text to fit budget)
    put_payload = {
        "segments": [
            {
                "segment_id": 1,
                "target_text": "అందరికీ మళ్ళీ స్వాగతం",
                "phonetic_text": "Andhariki malli swagatham",
            }
        ]
    }
    put_res = client.put(f"/api/v1/projects/{job_id}/segments", json=put_payload)
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["updated_count"] == 1

    updated_seg1 = updated_data["segments"][0]
    assert updated_seg1["target_text"] == "అందరికీ మళ్ళీ స్వాగతం"
    assert updated_seg1["phonetic_text"] == "Andhariki malli swagatham"
    assert updated_seg1["is_curated"] is True
    assert updated_seg1["target_syllables"] > 0
    assert updated_seg1["fit_status"] in ["FITS", "TOO_LONG", "TOO_SHORT"]

    # 3. PUT with excessively long text that exceeds duration budget -> TOO_LONG
    long_payload = {
        "segments": [
            {
                "segment_id": 1,
                "target_text": "ఈ వీడియోలో మనం చాలా విషయాల గురించి విస్తారంగా చర్చించుకోబోతున్నాము మరియు ఇది చాలా పెద్ద వాక్యం",
            }
        ]
    }
    long_res = client.put(f"/api/v1/projects/{job_id}/segments", json=long_payload)
    assert long_res.status_code == 200
    long_data = long_res.json()
    assert long_data["segments"][0]["fit_status"] == "TOO_LONG"
    assert long_data["all_fit"] is False
