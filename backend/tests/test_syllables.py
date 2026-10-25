import pytest
from app.services.syllables import syllable_estimator


def test_english_syllable_counting():
    """Verify English syllable counter on common words and phrases."""
    assert syllable_estimator.count_syllables("hello") == 2
    assert syllable_estimator.count_syllables("world") == 1
    assert syllable_estimator.count_syllables("welcome back") == 3
    assert syllable_estimator.count_syllables("video dubbing and lip sync platform") == 10


def test_indic_telugu_syllable_counting():
    """Verify Telugu akshara syllable counting."""
    # "నమస్కారం" -> న (1), మ (1), స్కా (1), రం (1) = 4
    # "అందరికీ" -> అం (1), ద (1), రి (1), కీ (1) = 4
    telugu_text = "నమస్కారం అందరికీ"
    count = syllable_estimator.count_syllables(telugu_text)
    assert count == 8, f"Expected 8 syllables for '{telugu_text}', got {count}"


def test_indic_hindi_syllable_counting():
    """Verify Hindi Devanagari akshara syllable counting."""
    # "नमस्ते" -> न (1), म (1), स्ते (1) = 3
    # "दोस्तों" -> दो (1), स्तों (1) = 2
    hindi_text = "नमस्ते दोस्तों"
    count = syllable_estimator.count_syllables(hindi_text)
    assert count == 5, f"Expected 5 syllables for '{hindi_text}', got {count}"


def test_spanish_syllable_counting():
    """Verify Spanish syllable counting."""
    # "hola a todos" -> ho-la (2), a (1), to-dos (2) = 5
    spanish_text = "hola a todos"
    count = syllable_estimator.count_syllables(spanish_text)
    assert count == 5, f"Expected 5 syllables for '{spanish_text}', got {count}"


def test_evaluate_fit_tolerance():
    """Verify ±10% duration and syllable pacing margin evaluation."""
    # 10 original syllables, 10 target syllables -> FITS
    status, ratio, tol = syllable_estimator.evaluate_fit(10, 10, 2.5, margin=0.10)
    assert status == "FITS"
    assert ratio == 1.0
    assert tol == 0.0

    # 10 original, 11 target (+10%) -> FITS
    status, ratio, tol = syllable_estimator.evaluate_fit(10, 11, 2.5, margin=0.10)
    assert status == "FITS"
    assert ratio == 1.1

    # 10 original, 9 target (-10%) -> FITS
    status, ratio, tol = syllable_estimator.evaluate_fit(10, 9, 2.5, margin=0.10)
    assert status == "FITS"
    assert ratio == 0.9

    # 10 original, 15 target (+50%) -> TOO_LONG
    status, ratio, tol = syllable_estimator.evaluate_fit(10, 15, 2.5, margin=0.10)
    assert status == "TOO_LONG"
    assert ratio == 1.5

    # 10 original, 5 target (-50%) -> TOO_SHORT
    status, ratio, tol = syllable_estimator.evaluate_fit(10, 5, 2.5, margin=0.10)
    assert status == "TOO_SHORT"
    assert ratio == 0.5
