import shutil
import subprocess
from pathlib import Path
import pytest

from app.core.config import settings
from app.services.media_engine import media_engine, MediaProcessingError


@pytest.fixture(scope="module")
def synthetic_video_path(tmp_path_factory) -> Path:
    """Fixture that generates a 3-second synthetic video with 90 frames."""
    temp_dir = tmp_path_factory.mktemp("media_fixtures")
    video_path = temp_dir / "test_synth_video.mp4"

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", "testsrc=duration=3:size=320x240:rate=30",
        "-f", "lavfi",
        "-i", "sine=frequency=440:duration=3:sample_rate=44100",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "96k",
        str(video_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return video_path


def test_probe_metadata(synthetic_video_path: Path):
    """Test accurate probing of video container and stream attributes."""
    meta = media_engine.probe_metadata(synthetic_video_path)

    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0
    assert meta.total_frames == 90
    assert meta.has_audio is True
    assert meta.video_codec in ["h264", "libx264"]
    assert meta.audio_sample_rate == 44100
    assert meta.duration_seconds >= 2.9


def test_lossless_video_extraction(synthetic_video_path: Path, tmp_path: Path):
    """
    Test extraction of video stream without re-encoding, verifying
    zero dropped frames and identical visual metadata.
    """
    output_silent_video = tmp_path / "silent_stream_copy.mp4"
    extracted_path = media_engine.extract_lossless_video(synthetic_video_path, output_silent_video)

    assert extracted_path.exists()

    # Verify frame counts
    input_frames = media_engine.count_exact_frames(synthetic_video_path)
    output_frames = media_engine.count_exact_frames(extracted_path)

    assert input_frames == 90
    assert output_frames == 90
    assert input_frames == output_frames, "Frames dropped during stream copy extraction!"

    # Verify metadata
    meta = media_engine.probe_metadata(extracted_path)
    assert meta.has_audio is False
    assert meta.width == 320
    assert meta.height == 240
    assert meta.fps == 30.0


def test_audio_extraction_and_fallback_separation(synthetic_video_path: Path, tmp_path: Path):
    """Test audio demuxing and acoustic stem separation fallback."""
    raw_audio = tmp_path / "raw.wav"
    media_engine.extract_raw_audio(synthetic_video_path, raw_audio)
    assert raw_audio.exists()

    vocals_raw, bg_raw = media_engine.separate_audio_ffmpeg_fallback(raw_audio, tmp_path)
    assert vocals_raw.exists()
    assert bg_raw.exists()

    v_16k, v_44k, bg = media_engine.format_audio_stems(vocals_raw, bg_raw, tmp_path)
    assert v_16k.exists()
    assert v_44k.exists()
    assert bg.exists()

    # Probe stem specs
    import ffmpeg
    p_16k = ffmpeg.probe(str(v_16k))["streams"][0]
    p_44k = ffmpeg.probe(str(v_44k))["streams"][0]
    p_bg = ffmpeg.probe(str(bg))["streams"][0]

    assert int(p_16k["sample_rate"]) == 16000
    assert int(p_16k["channels"]) == 1
    assert int(p_44k["sample_rate"]) == 44100
    assert int(p_44k["channels"]) == 2
    assert int(p_bg["sample_rate"]) == 44100
    assert int(p_bg["channels"]) == 2


@pytest.mark.asyncio
async def test_end_to_end_pipeline(synthetic_video_path: Path, monkeypatch):
    """Test process_media_pipeline with forced fallback to verify complete async flow."""
    monkeypatch.setattr(settings, "FORCE_FFMPEG_FALLBACK", True)

    events = []

    async def progress_tracker(job_id: str, pct: float, desc: str, extra=None):
        events.append((pct, desc))

    result = await media_engine.process_media_pipeline(
        job_id="test-job-1234",
        video_path=synthetic_video_path,
        progress_callback=progress_tracker,
    )

    assert result.job_id == "test-job-1234"
    assert Path(result.lossless_video_path).exists()
    assert Path(result.vocals_asr_path).exists()
    assert Path(result.vocals_clone_path).exists()
    assert Path(result.background_path).exists()
    assert result.metadata.total_frames == 90
    assert len(events) >= 3
