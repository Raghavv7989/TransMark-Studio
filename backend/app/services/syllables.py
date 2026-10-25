import re
from typing import Dict, Tuple

# Unicode Virama / Halant codepoints across Indic scripts
INDIC_VIRAMAS = {
    0x094D,  # Devanagari Virama (Hindi, Marathi)
    0x0C4D,  # Telugu Virama
    0x0BCD,  # Tamil Virama
    0x0CCD,  # Kannada Virama
    0x0D4D,  # Malayalam Virama
    0x09CD,  # Bengali Virama
    0x0A4D,  # Gurmukhi Virama
    0x0ACD,  # Gujarati Virama
    0x0B4D,  # Odia Virama
}

# Unicode Independent Vowel Ranges across Indic scripts
INDIC_INDEPENDENT_VOWEL_RANGES = [
    (0x0904, 0x0914),  # Devanagari
    (0x0C05, 0x0C14),  # Telugu
    (0x0B85, 0x0B94),  # Tamil
    (0x0C85, 0x0C94),  # Kannada
    (0x0D05, 0x0D14),  # Malayalam
    (0x0985, 0x0994),  # Bengali
]

# Unicode Consonant Ranges across Indic scripts
INDIC_CONSONANT_RANGES = [
    (0x0915, 0x0939),  # Devanagari
    (0x0C15, 0x0C39),  # Telugu
    (0x0B95, 0x0BB9),  # Tamil
    (0x0C95, 0x0CB9),  # Kannada
    (0x0D15, 0x0D39),  # Malayalam
    (0x0995, 0x09B9),  # Bengali
]


class SyllableEstimator:
    """
    Precision multi-lingual syllable counter engineered for isochronic translation
    and audiovisual lip-sync pacing across English, Indic scripts, Romance languages,
    and Romanized phonetic vernaculars.
    """

    def is_indic_script(self, text: str) -> bool:
        """Detect if text contains Indic Unicode script characters."""
        for ch in text:
            code = ord(ch)
            if (0x0900 <= code <= 0x097F or   # Devanagari
                0x0C00 <= code <= 0x0C7F or   # Telugu
                0x0B80 <= code <= 0x0BFF or   # Tamil
                0x0C80 <= code <= 0x0CFF or   # Kannada
                0x0D00 <= code <= 0x0D7F or   # Malayalam
                0x0980 <= code <= 0x09FF):    # Bengali
                return True
        return False

    def count_indic_syllables(self, text: str) -> int:
        """
        Count phonetic aksharas (spoken syllables) in Brahmic abugidas.
        In Indic orthography:
        1. An independent vowel forms a distinct syllable.
        2. A consonant carries an inherent vowel (forms 1 syllable) unless followed
           immediately by a virama/halant (which joins it into a consonant cluster).
        """
        syllables = 0
        chars = list(text)
        n = len(chars)

        for i in range(n):
            code = ord(chars[i])

            # 1. Independent vowel
            is_ind_vowel = any(start <= code <= end for start, end in INDIC_INDEPENDENT_VOWEL_RANGES)
            if is_ind_vowel:
                syllables += 1
                continue

            # 2. Consonant
            is_consonant = any(start <= code <= end for start, end in INDIC_CONSONANT_RANGES)
            if is_consonant:
                # Check if followed by virama/halant
                has_virama_next = (i + 1 < n and ord(chars[i + 1]) in INDIC_VIRAMAS)
                if not has_virama_next:
                    syllables += 1

        return max(1, syllables) if any(c.isalnum() for c in text) else 0

    def count_latin_syllables(self, text: str) -> int:
        """
        Count syllables in Latin-script languages (English, Spanish, French,
        and Romanized transliterations like Teluglish and Hinglish).
        Accurately accounts for vowel clusters, hiatuses (e.g. vid-e-o, ra-di-o),
        and silent word-final vowels.
        """
        clean_text = re.sub(r"[^a-zA-Z\s]", "", text).lower().strip()
        if not clean_text:
            return 0

        words = clean_text.split()
        total = 0

        for word in words:
            if len(word) <= 2:
                total += 1
                continue

            # Count basic contiguous vowel groups
            vowel_groups = re.findall(r"[aeiouy]+", word)
            count = len(vowel_groups)

            # Detect hiatus vowel pairs that form 2 distinct syllables (e.g., 'eo', 'ia', 'io', 'iu', 'ua', 'uo')
            for vg in vowel_groups:
                if len(vg) >= 2:
                    for hiatus in ["eo", "ia", "io", "iu", "ua", "uo"]:
                        if hiatus in vg:
                            count += 1

            # Trailing silent 'e' in English words (e.g. 'game', 'voice', but not 'the' or '-le')
            if word.endswith("e") and not word.endswith("le") and len(word) > 2:
                if count > 1 and word[-2] not in "aeiouy":
                    count -= 1

            total += max(1, count)

        return max(1, total)

    def count_syllables(self, text: str) -> int:
        """Universal multi-lingual syllable counter."""
        if not text or not text.strip():
            return 0

        if self.is_indic_script(text):
            return self.count_indic_syllables(text)
        return self.count_latin_syllables(text)

    def evaluate_fit(
        self,
        original_syllables: int,
        target_syllables: int,
        duration_seconds: float,
        margin: float = 0.10,
    ) -> Tuple[str, float, float]:
        """
        Evaluate if translated syllables fit within duration budget and pacing margin.
        Returns (fit_status, pacing_ratio, tolerance_pct).
        - fit_status: 'FITS', 'TOO_LONG', or 'TOO_SHORT'
        - pacing_ratio: target / original
        - tolerance_pct: percentage deviation
        """
        orig = max(1, original_syllables)
        targ = max(1, target_syllables)

        pacing_ratio = round(targ / orig, 3)
        tolerance_pct = round(abs(targ - orig) / orig * 100.0, 1)

        allowed_diff = max(1, int(round(orig * margin)))
        min_syllables = max(1, orig - allowed_diff)
        max_syllables = orig + allowed_diff

        if min_syllables <= targ <= max_syllables:
            fit_status = "FITS"
        elif targ > max_syllables:
            fit_status = "TOO_LONG"
        else:
            fit_status = "TOO_SHORT"

        return fit_status, pacing_ratio, tolerance_pct


syllable_estimator = SyllableEstimator()
