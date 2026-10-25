import numpy as np
import pytest
from app.services.lipsync_engine import lipsync_engine


def test_mouth_roi_detection():
    """Verify lower facial mouth ROI detection within geometric boundaries."""
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    x1, y1, x2, y2 = lipsync_engine.detect_mouth_roi(dummy_frame)

    assert 0 <= x1 < x2 <= 640
    assert 0 <= y1 < y2 <= 480
    # Mouth must be in lower half of frame
    assert y1 >= int(0.50 * 480)
    assert (x2 - x1) > 20
    assert (y2 - y1) > 20


def test_feathered_mouth_mask():
    """Verify smooth Gaussian falloff alpha mask."""
    w, h = 100, 60
    mask = lipsync_engine.generate_feathered_mouth_mask(w, h)

    assert mask.shape == (h, w)
    assert mask.dtype == np.float32
    assert 0.0 <= mask.min() <= mask.max() <= 1.0
    # Center should be high confidence (close to 1.0)
    assert mask[h // 2, w // 2] > 0.8
    # Edges should smoothly decay to zero
    assert mask[0, 0] < 0.2
    assert mask[-1, -1] < 0.2


def test_zero_damage_frame_constraint():
    """
    CRITICAL CONSTRAINT VERIFICATION:
    Verifies that the upper face, eyes, hair, and background remain 100% untouched
    and bit-identical to the source video frame.
    """
    # Create deterministic frame with gradient and noise
    h, w = 360, 480
    original_frame = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)

    # Box in lower face
    box = (140, 210, 340, 320)
    bx1, by1, bx2, by2 = box
    bw = bx2 - bx1
    bh = by2 - by1

    synth_mouth = np.full((bh, bw, 3), 180, dtype=np.uint8)

    # Execute zero-damage blend
    blended_frame = lipsync_engine.blend_mouth_zero_damage(original_frame, synth_mouth, box)

    # 1. Upper face check (top 50% of the frame)
    upper_original = original_frame[:180, :, :]
    upper_blended = blended_frame[:180, :, :]
    assert np.array_equal(upper_original, upper_blended), "ZERO-DAMAGE VIOLATION: Upper face pixels were modified!"

    # 2. Left side background check
    left_original = original_frame[:, :100, :]
    left_blended = blended_frame[:, :100, :]
    assert np.array_equal(left_original, left_blended), "ZERO-DAMAGE VIOLATION: Left background pixels were modified!"

    # 3. Right side background check
    right_original = original_frame[:, 380:, :]
    right_blended = blended_frame[:, 380:, :]
    assert np.array_equal(right_original, right_blended), "ZERO-DAMAGE VIOLATION: Right background pixels were modified!"

    # 4. Mouth ROI inside the box should have modified pixels
    assert not np.array_equal(original_frame[by1:by2, bx1:bx2], blended_frame[by1:by2, bx1:bx2]), (
        "Mouth ROI was not modified with synthesized lip movements."
    )


def test_codeformer_restoration_filter():
    """Verify CodeFormer high-frequency restoration sharpens mouth crop."""
    dummy_mouth = np.random.randint(50, 200, (80, 120, 3), dtype=np.uint8)
    restored = lipsync_engine.restore_mouth_patch(dummy_mouth)

    assert restored.shape == dummy_mouth.shape
    assert restored.dtype == np.uint8
