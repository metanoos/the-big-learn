// isCJK reports whether r is a Unified CJK ideograph (the common plane the
// canon lives in). Shared by the chapter page (Server Component, which collects
// chars for the batch pinyin fetch) and AnnotatedText (Client Component, which
// renders them). Kept in a plain module — no "use client" — so both sides can
// import it.
export function isCJK(r: string): boolean {
  const cp = r.codePointAt(0);
  if (cp === undefined) return false;
  // CJK Unified Ideographs (common), Ext A, Ext B-F (rare), Compatibility.
  return (
    (cp >= 0x3400 && cp <= 0x4dbf) ||
    (cp >= 0x4e00 && cp <= 0x9fff) ||
    (cp >= 0x20000 && cp <= 0x2fa1f) ||
    (cp >= 0xf900 && cp <= 0xfaff)
  );
}

// toneOf derives the Mandarin tone (1–4) of a single pinyin syllable, or 0 for
// neutral tone, or null when no tone can be determined. Accepts BOTH pinyin
// forms the reader sees:
//   - tone-marked  (build-time perCharPinyin, e.g. "yǐn", "háng") — preferred,
//     produced by tools/build_pinyin.py with sandhi already applied.
//   - numeric      (per-char-map fallback, e.g. "yin2", "hang2", "ma5") — the
//     server's /characters/batch emits these; we still color them.
// Tone marks: macron=1, acute=2, caron=3, grave=4. A vowel with no diacritic
// (and no trailing digit) is neutral (5/0). Non-syllables (no vowel at all)
// return null so the caller can render without a tone class.
//
// Kept here next to isCJK so the CJK rendering helpers share one home and one
// import surface. Pure function, no deps — safe in Server and Client alike.
const TONE_MARKS: Record<string, number> = {
  // Tone 1 — macron
  ā: 1, ē: 1, ī: 1, ō: 1, ū: 1, ǖ: 1,
  // Tone 2 — acute
  á: 2, é: 2, í: 2, ó: 2, ú: 2, ǘ: 2,
  // Tone 3 — caron
  ǎ: 3, ě: 3, ǐ: 3, ǒ: 3, ǔ: 3, ǚ: 3,
  // Tone 4 — grave
  à: 4, è: 4, ì: 4, ò: 4, ù: 4, ǜ: 4,
};
const PLAIN_VOWELS = new Set(["a", "e", "i", "o", "u", "ü", "A", "E", "I", "O", "U", "Ü"]);

export function toneOf(syllable: string): number | null {
  if (!syllable) return null;
  // 1. Numeric form ("yin2", "ma5", "hang4"). The first ASCII digit 1–5 wins;
  //    5 is the neutral-tone marker and maps to 0.
  const m = syllable.match(/[1-5]/);
  if (m) {
    const d = Number(m[0]);
    return d === 5 ? 0 : d;
  }
  // 2. Tone-marked form. The first marked vowel reveals the tone.
  for (const ch of syllable) {
    if (TONE_MARKS[ch] !== undefined) return TONE_MARKS[ch];
  }
  // 3. Plain vowels present but unmarked → neutral tone.
  for (const ch of syllable) {
    if (PLAIN_VOWELS.has(ch)) return 0;
  }
  // 4. No vowel (empty, punctuation, or a malformed entry) → unknown.
  return null;
}
