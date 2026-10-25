/**
 * High-Precision Multi-Lingual Syllable & Akshara Counting Engine.
 * Supports Brahmic abugidas (Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali)
 * and Latin phonology (English, Spanish, French, and Romanized vernaculars like Teluglish/Hinglish).
 */

const INDIC_VIRAMAS = new Set([
  0x094d, // Devanagari Virama (Hindi, Marathi)
  0x0c4d, // Telugu Virama
  0x0bcd, // Tamil Virama
  0x0ccd, // Kannada Virama
  0x0d4d, // Malayalam Virama
  0x09cd, // Bengali Virama
  0x0a4d, // Gurmukhi Virama
  0x0acd, // Gujarati Virama
  0x0b4d, // Odia Virama
]);

const INDIC_INDEPENDENT_VOWELS: [number, number][] = [
  [0x0904, 0x0914], // Devanagari
  [0x0c05, 0x0c14], // Telugu
  [0x0b85, 0x0b94], // Tamil
  [0x0c85, 0x0c94], // Kannada
  [0x0d05, 0x0d14], // Malayalam
  [0x0985, 0x0994], // Bengali
];

const INDIC_CONSONANTS: [number, number][] = [
  [0x0915, 0x0939], // Devanagari
  [0x0c15, 0x0c39], // Telugu
  [0x0b95, 0x0bb9], // Tamil
  [0x0c95, 0x0cb9], // Kannada
  [0x0d15, 0x0d39], // Malayalam
  [0x0995, 0x09b9], // Bengali
];

export function isIndicScript(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    const code = text.charCodeAt(i);
    if (
      (code >= 0x0900 && code <= 0x097f) || // Devanagari
      (code >= 0x0c00 && code <= 0x0c7f) || // Telugu
      (code >= 0x0b80 && code <= 0x0bff) || // Tamil
      (code >= 0x0c80 && code <= 0x0cff) || // Kannada
      (code >= 0x0d00 && code <= 0x0d7f) || // Malayalam
      (code >= 0x0980 && code <= 0x09ff)    // Bengali
    ) {
      return true;
    }
  }
  return false;
}

/**
 * Counts Aksharas (orthographic spoken syllables) in Brahmic abugidas.
 * - An independent vowel constitutes a distinct spoken syllable.
 * - A consonant carries an inherent vowel (forms 1 syllable) unless followed
 *   immediately by a virama/halant (which marks it as a conjunct coda).
 */
export function countIndicAksharas(text: string): number {
  let syllables = 0;
  const chars = Array.from(text);
  const n = chars.length;

  for (let i = 0; i < n; i++) {
    const code = chars[i].charCodeAt(0);

    // 1. Check if independent vowel
    const isIndVowel = INDIC_INDEPENDENT_VOWELS.some(
      ([start, end]) => code >= start && code <= end
    );
    if (isIndVowel) {
      syllables++;
      continue;
    }

    // 2. Check if consonant
    const isConsonant = INDIC_CONSONANTS.some(
      ([start, end]) => code >= start && code <= end
    );
    if (isConsonant) {
      // If followed immediately by a virama/halant, it binds to the next akshara
      const hasViramaNext =
        i + 1 < n && INDIC_VIRAMAS.has(chars[i + 1].charCodeAt(0));
      if (!hasViramaNext) {
        syllables++;
      }
    }
  }

  return syllables > 0 ? syllables : text.trim().length > 0 ? 1 : 0;
}

/**
 * Counts syllables in Latin text (English, Spanish, French, Teluglish, Hinglish).
 * Accounts for contiguous vowel clusters, hiatus pairs, and silent endings.
 */
export function countLatinSyllables(text: string): number {
  const clean = text.replace(/[^a-zA-Z\s]/g, "").toLowerCase().trim();
  if (!clean) return 0;

  const words = clean.split(/\s+/);
  let total = 0;

  for (const word of words) {
    if (word.length <= 2) {
      total += 1;
      continue;
    }

    const vowelGroups = word.match(/[aeiouy]+/g) || [];
    let count = vowelGroups.length;

    // Detect hiatus pairs that form 2 distinct syllables (e.g. vid-e-o, ra-di-o, di-al)
    for (const vg of vowelGroups) {
      if (vg.length >= 2) {
        for (const hiatus of ["eo", "ia", "io", "iu", "ua", "uo"]) {
          if (vg.includes(hiatus)) {
            count += 1;
          }
        }
      }
    }

    // Trailing silent 'e'
    if (word.endsWith("e") && !word.endsWith("le") && word.length > 2) {
      if (count > 1 && !"aeiouy".includes(word[word.length - 2])) {
        count -= 1;
      }
    }

    total += Math.max(1, count);
  }

  return Math.max(1, total);
}

/**
 * Universal syllable & akshara counter.
 */
export function countSyllables(text: string): number {
  if (!text || !text.trim()) return 0;
  if (isIndicScript(text)) {
    return countIndicAksharas(text);
  }
  return countLatinSyllables(text);
}

export function evaluateFit(
  originalSyllables: number,
  targetSyllables: number,
  margin: number = 0.10
): {
  fitStatus: "FITS" | "TOO_LONG" | "TOO_SHORT";
  pacingRatio: number;
  tolerancePct: number;
} {
  const orig = Math.max(1, originalSyllables);
  const targ = Math.max(1, targetSyllables);

  const pacingRatio = Number((targ / orig).toFixed(2));
  const tolerancePct = Number((Math.abs(targ - orig) / orig * 100).toFixed(1));

  const allowedDiff = Math.max(1, Math.round(orig * margin));
  const minSyllables = Math.max(1, orig - allowedDiff);
  const maxSyllables = orig + allowedDiff;

  let fitStatus: "FITS" | "TOO_LONG" | "TOO_SHORT" = "FITS";
  if (targ < minSyllables) {
    fitStatus = "TOO_SHORT";
  } else if (targ > maxSyllables) {
    fitStatus = "TOO_LONG";
  }

  return { fitStatus, pacingRatio, tolerancePct };
}
