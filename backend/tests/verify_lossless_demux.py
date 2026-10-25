#!/usr/bin/env python3
"""
Verification script for lossless video and audio demuxing.
Generates a known synthetic video with exact frame count, extracts the lossless video stream,
and strictly verifies that zero frames were dropped and all audio stems are generated.
"""
import os
import subprocess
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.media_engine import media_engine
from app.core.config import settings


def generate_synthetic_video(output_path: Path, duration_sec: int = 5, fps: int = 30) -> int:
    """Generate a synthetic test video with exact frame count and stereo audio."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_expected_frames = duration_sec * fps

    # Synthetic video: testsrc pattern with counter, plus synth audio (sine tone + noise)
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration_sec}:size=640x360:rate={fps}",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration_sec}:sample_rate=44100",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(output_path),
    ]

    print(f"[*] Generating synthetic video ({duration_sec}s @ {fps}fps = {total_expected_frames} frames)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Error creating synthetic video: {res.stderr}")
        sys.exit(1)

    print(f"[+] Synthetic video generated at: {output_path}")
    return total_expected_frames


def run_verification():
    print("=" * 70)
    print("TransMark Lossless FFmpeg Demuxing & Zero-Frame-Drop Verification")
    print("=" * 70)

    test_dir = settings.STORAGE_ROOT / "test_verification"
    test_dir.mkdir(parents=True, exist_ok=True)
    raw_video = test_dir / "synthetic_test_video.mp4"
    lossless_video = test_dir / "lossless_silent_video.mp4"

    # Step 1: Create synthetic reference video
    expected_frames = generate_synthetic_video(raw_video, duration_sec=5, fps=30)

    # Step 2: Probe metadata of original video
    print("\n[*] Probing original video metadata...")
    meta_original = media_engine.probe_metadata(raw_video)
    print(f"    - Resolution:   {meta_original.width}x{meta_original.height}")
    print(f"    - FPS:          {meta_original.fps}")
    print(f"    - Total frames: {meta_original.total_frames}")
    print(f"    - Codec:        {meta_original.video_codec}")
    print(f"    - Has Audio:    {meta_original.has_audio} ({meta_original.audio_codec} @ {meta_original.audio_sample_rate}Hz)")

    assert meta_original.total_frames == expected_frames, (
        f"Expected {expected_frames} frames but probed {meta_original.total_frames}"
    )

    # Step 3: Perform lossless stream copy extraction
    print("\n[*] Performing lossless stream copy extraction (-c:v copy -an)...")
    media_engine.extract_lossless_video(raw_video, lossless_video)
    assert lossless_video.exists(), "Extracted video file does not exist!"

    # Step 4: Verify zero dropped frames and intact properties
    print("\n[*] Verifying extracted video properties...")
    meta_extracted = media_engine.probe_metadata(lossless_video)
    input_exact_frames = media_engine.count_exact_frames(raw_video)
    output_exact_frames = media_engine.count_exact_frames(lossless_video)

    print(f"    - Original exact packet count:  {input_exact_frames}")
    print(f"    - Extracted exact packet count: {output_exact_frames}")
    print(f"    - Extracted resolution:         {meta_extracted.width}x{meta_extracted.height}")
    print(f"    - Extracted FPS:                {meta_extracted.fps}")
    print(f"    - Extracted Codec:              {meta_extracted.video_codec}")
    print(f"    - Extracted Has Audio:          {meta_extracted.has_audio}")

    # Assertions
    assert input_exact_frames == output_exact_frames, (
        f"Frame count mismatch! Original={input_exact_frames}, Extracted={output_exact_frames}"
    )
    assert output_exact_frames == expected_frames, (
        f"Expected {expected_frames} frames, got {output_exact_frames}"
    )
    assert meta_extracted.width == meta_original.width, "Width mismatch!"
    assert meta_extracted.height == meta_original.height, "Height mismatch!"
    assert meta_extracted.video_codec == meta_original.video_codec, "Codec mismatch!"
    assert meta_extracted.has_audio is False, "Extracted silent video must not contain audio stream!"

    print("\n[+] FRAME DROP CHECK PASSED: 0 dropped frames. 100% visual quality preserved.")

    # Step 5: Test audio demuxing and separation
    print("\n[*] Testing audio demuxing & stem separation...")
    raw_audio = test_dir / "extracted_raw.wav"
    media_engine.extract_raw_audio(raw_video, raw_audio)
    assert raw_audio.exists(), "Extracted audio does not exist!"

    # Fallback separation test (guaranteed on all platforms without requiring model download)
    vocals_raw, bg_raw = media_engine.separate_audio_ffmpeg_fallback(raw_audio, test_dir)
    assert vocals_raw.exists() and bg_raw.exists(), "Separated raw stems missing!"

    # Format stems
    v_asr, v_clone, bg = media_engine.format_audio_stems(vocals_raw, bg_raw, test_dir)
    assert v_asr.exists(), "vocals_16k.wav missing!"
    assert v_clone.exists(), "vocals_44k.wav missing!"
    assert bg.exists(), "background.wav missing!"

    # Probe stem formats
    import ffmpeg
    p_asr = ffmpeg.probe(str(v_asr))["streams"][0]
    p_clone = ffmpeg.probe(str(v_clone))["streams"][0]
    p_bg = ffmpeg.probe(str(bg))["streams"][0]

    print(f"    - vocals_16k.wav:   sample_rate={p_asr['sample_rate']}Hz, channels={p_asr['channels']}")
    print(f"    - vocals_44k.wav:   sample_rate={p_clone['sample_rate']}Hz, channels={p_clone['channels']}")
    print(f"    - background.wav:   sample_rate={p_bg['sample_rate']}Hz, channels={p_bg['channels']}")

    assert int(p_asr["sample_rate"]) == 16000 and int(p_asr["channels"]) == 1, "ASR stem must be 16kHz mono!"
    assert int(p_clone["sample_rate"]) == 44100 and int(p_clone["channels"]) == 2, "Voice clone stem must be 44.1kHz stereo!"
    assert int(p_bg["sample_rate"]) == 44100 and int(p_bg["channels"]) == 2, "Background stem must be 44.1kHz stereo!"

    print("\n" + "=" * 70)
    print("ALL LOSSLESS MEDIA VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_verification()
