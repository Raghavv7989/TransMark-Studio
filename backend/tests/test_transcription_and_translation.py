import pytest
from app.models.segment import IsochronicSegment, WordTimestamp
from app.services.transcription import transcription_engine
from app.services.translator import isochronic_translator


def test_pause_based_word_grouping():
    """
    Verify words are grouped into natural phrasing segments where pauses exceed 300ms.
    """
    words = [
        # Segment 1: "Hey everyone," (0ms - 800ms)
        WordTimestamp(word="Hey", start_ms=0, end_ms=300, start_time=0.0, end_time=0.3, confidence=0.98),
        WordTimestamp(word="everyone,", start_ms=350, end_ms=800, start_time=0.35, end_time=0.8, confidence=0.97),
        # 450ms pause (> 300ms boundary!)
        # Segment 2: "welcome back to the channel." (1250ms - 2700ms)
        WordTimestamp(word="welcome", start_ms=1250, end_ms=1600, start_time=1.25, end_time=1.6, confidence=0.99),
        WordTimestamp(word="back", start_ms=1650, end_ms=1950, start_time=1.65, end_time=1.95, confidence=0.99),
        WordTimestamp(word="to", start_ms=2000, end_ms=2150, start_time=2.0, end_time=2.15, confidence=0.95),
        WordTimestamp(word="the", start_ms=2180, end_ms=2300, start_time=2.18, end_time=2.3, confidence=0.95),
        WordTimestamp(word="channel.", start_ms=2350, end_ms=2700, start_time=2.35, end_time=2.7, confidence=0.98),
    ]

    segments = transcription_engine.group_words_by_pauses(words, pause_threshold_ms=300)

    assert len(segments) == 2, f"Expected 2 segments due to >300ms pause, got {len(segments)}"

    # Segment 1 assertions
    seg1 = segments[0]
    assert seg1.segment_id == 1
    assert seg1.source_text == "Hey everyone,"
    assert seg1.start_ms == 0
    assert seg1.end_ms == 800
    assert seg1.duration_budget == 0.8
    assert len(seg1.words) == 2

    # Segment 2 assertions
    seg2 = segments[1]
    assert seg2.segment_id == 2
    assert seg2.source_text == "welcome back to the channel."
    assert seg2.start_ms == 1250
    assert seg2.end_ms == 2700
    assert seg2.duration_budget == 1.45
    assert len(seg2.words) == 5


@pytest.mark.asyncio
async def test_isochronic_translation_telugu():
    """Verify isochronic translation generates Telugu native script and Teluglish phonetic script."""
    seg = IsochronicSegment(
        segment_id=1,
        start_time=0.0,
        end_time=1.8,
        start_ms=0,
        end_ms=1800,
        duration_budget=1.8,
        source_text="welcome back",
        target_text="",
        phonetic_text="",
        original_syllables=3,
        target_syllables=0,
        pacing_ratio=0.0,
        fit_status="PENDING",
        tolerance_pct=0.0,
        words=[],
    )

    translated = await isochronic_translator.translate_segment(seg, target_lang_code="te")

    assert translated.target_text != ""
    assert translated.phonetic_text != ""
    assert translated.target_syllables > 0
    assert translated.pacing_ratio > 0
    assert translated.fit_status in ["FITS", "TOO_LONG", "TOO_SHORT"]


@pytest.mark.asyncio
async def test_isochronic_translation_hindi_and_spanish():
    """Verify isochronic translation supports Hindi and Spanish."""
    seg_hindi = IsochronicSegment(
        segment_id=1,
        start_time=0.0,
        end_time=2.0,
        start_ms=0,
        end_ms=2000,
        duration_budget=2.0,
        source_text="hello everyone",
        target_text="",
        phonetic_text="",
        original_syllables=5,
        target_syllables=0,
        pacing_ratio=0.0,
        fit_status="PENDING",
        tolerance_pct=0.0,
    )
    res_hi = await isochronic_translator.translate_segment(seg_hindi, target_lang_code="hi")
    assert res_hi.target_text != ""
    assert res_hi.phonetic_text != ""

    seg_spanish = IsochronicSegment(
        segment_id=2,
        start_time=0.0,
        end_time=2.0,
        start_ms=0,
        end_ms=2000,
        duration_budget=2.0,
        source_text="thank you for watching",
        target_text="",
        phonetic_text="",
        original_syllables=6,
        target_syllables=0,
        pacing_ratio=0.0,
        fit_status="PENDING",
        tolerance_pct=0.0,
    )
    res_es = await isochronic_translator.translate_segment(seg_spanish, target_lang_code="es")
    assert res_es.target_text != ""
    assert res_es.phonetic_text != ""
