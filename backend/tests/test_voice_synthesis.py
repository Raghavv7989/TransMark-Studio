from pathlib import Path
import numpy as np
import pytest
import soundfile as sf

from app.models.segment import IsochronicSegment
from app.services.voice_synthesis import voice_synthesis_engine


def test_align_audio_duration(tmp_path: Path):
    """
    Verify dynamic pitch-invariant time-alignment matches target duration
    to exact millisecond accuracy.
    """
    sr = 44100
    # Generate 1.2s tone
    initial_dur = 1.2
    t = np.linspace(0, initial_dur, int(initial_dur * sr), endpoint=False)
    initial_audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    in_file = tmp_path / "initial_seg.wav"
    sf.write(str(in_file), initial_audio, sr)

    # 1. Expand duration to 1.850s
    target_expand = 1.850
    out_expand = tmp_path / "aligned_expand.wav"
    voice_synthesis_engine.align_audio_duration(in_file, target_expand, out_expand)
    assert out_expand.exists()
    y_exp, _ = sf.read(str(out_expand))
    exp_dur = len(y_exp) / sr
    assert pytest.approx(exp_dur, abs=0.005) == target_expand

    # 2. Compress duration to 0.750s
    target_compress = 0.750
    out_compress = tmp_path / "aligned_compress.wav"
    voice_synthesis_engine.align_audio_duration(in_file, target_compress, out_compress)
    assert out_compress.exists()
    y_comp, _ = sf.read(str(out_compress))
    comp_dur = len(y_comp) / sr
    assert pytest.approx(comp_dur, abs=0.005) == target_compress


def test_build_master_timeline_and_ambient_mix(tmp_path: Path):
    """
    Verify dialogue segments are placed at exact timestamps on master timeline
    and remixed with ambient background track without clipping.
    """
    sr = 44100
    total_sec = 4.0

    # Create two 1.0s segments
    t = np.linspace(0, 1.0, sr, endpoint=False)
    seg_audio = (0.4 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)

    p1 = tmp_path / "seg1.wav"
    p2 = tmp_path / "seg2.wav"
    sf.write(str(p1), seg_audio, sr)
    sf.write(str(p2), seg_audio, sr)

    seg1 = IsochronicSegment(
        segment_id=1, start_time=0.5, end_time=1.5, start_ms=500, end_ms=1500,
        duration_budget=1.0, source_text="seg1", target_text="seg1", phonetic_text="seg1",
        original_syllables=2, target_syllables=2, pacing_ratio=1.0, fit_status="FITS", tolerance_pct=0.0,
    )
    seg2 = IsochronicSegment(
        segment_id=2, start_time=2.2, end_time=3.2, start_ms=2200, end_ms=3200,
        duration_budget=1.0, source_text="seg2", target_text="seg2", phonetic_text="seg2",
        original_syllables=2, target_syllables=2, pacing_ratio=1.0, fit_status="FITS", tolerance_pct=0.0,
    )

    # 1. Stitch timeline
    master_dlg = tmp_path / "master_dlg.wav"
    voice_synthesis_engine.build_master_dialogue_timeline([(seg1, p1), (seg2, p2)], total_sec, master_dlg)
    assert master_dlg.exists()
    dlg_y, _ = sf.read(str(master_dlg))
    assert pytest.approx(len(dlg_y) / sr, abs=0.01) == total_sec

    # Silence before first segment (at 0.2s) should be near zero
    assert np.max(np.abs(dlg_y[:int(0.3 * sr)])) == 0.0
    # Segment 1 should be active at 0.7s
    assert np.max(np.abs(dlg_y[int(0.6 * sr):int(1.2 * sr)])) > 0.1

    # 2. Ambient remix
    bg_audio = (0.2 * np.sin(2 * np.pi * 80 * np.linspace(0, total_sec, int(total_sec * sr)))).astype(np.float32)
    bg_file = tmp_path / "bg_ambient.wav"
    sf.write(str(bg_file), bg_audio, sr)

    final_mixed = tmp_path / "master_mixed.wav"
    voice_synthesis_engine.mix_master_audio(master_dlg, bg_file, final_mixed, background_volume=0.7)
    assert final_mixed.exists()
    mix_y, _ = sf.read(str(final_mixed))
    assert len(mix_y) == len(dlg_y)
    # Peak should be within safe limits (no clipping)
    assert np.max(np.abs(mix_y)) <= 0.98
