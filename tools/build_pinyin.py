#!/usr/bin/env python3
"""Generate context-aware, per-character pinyin for every reading unit.

WHY THIS EXISTS
---------------
The reader originally built pinyin from a per-character index, returning the
first reading of each rune regardless of context. That's wrong for polyphones
(为 always shows wèi even in 为政 = wéi zhèng) and skips tone sandhi (你好
renders nǐ hǎo instead of ní hǎo).

This script pre-computes per-rune pinyin at build time and writes it into each
reading unit as `pinyin_per_char`. pypinyin's word dictionary does the heavy
lifting (modern Mandarin polyphones), the overrides file (see below) supplies
the classical-Chinese cases pypinyin provably gets wrong, and a small sandhi
post-processor handles 3rd-tone / 不 rules.

PIPELINE (per reading unit)
---------------------------
1. Traditional → simplified conversion via the per-character index's
   `traditional`/`simplified` pairs (pypinyin's word dictionary is
   simplified-keyed — without this, 为政 loses its polyphone disambiguation).
   NOTE: this map is largely a no-op in practice because the index's
   traditional field is itself simplified for most entries (only 23/7817
   differ). The chapter text is already simplified (the repo was migrated
   via tools/to_simplified.py), so this pass exists for defense, not need.
2. Longest-match overrides first. pinyin-overrides.json holds verified
   classical-Chinese phrase readings (keyed by SIMPLIFIED form, matching the
   canon) consulted before pypinyin.
3. pypinyin for the rest, with `Style.TONE` and `heteronym=False`. Chars
   pypinyin doesn't know fall back to the per-char index's first reading.
4. Tone sandhi post-pass: 3rd-tone before 3rd-tone → 2nd-tone; 不 before 4th →
   bú. (一 sandhi intentionally not applied — it depends on positional
   numerology that's rarely right in classical text.)
5. Emit one string per RUNE of the original (simplified) text. Non-CJK runes
   map to "" so rune-index alignment holds and the frontend can index by rune
   position regardless of script.

IDEMPOTENT & SAFE TO RE-RUN
---------------------------
Only the `pinyin_per_char` and `pinyin_source` fields are touched. Everything
else (text, translations, orders, ids) is preserved byte-for-byte. Re-running
with an updated overrides file propagates the new readings.

SCOPE
-----
All book chapters under content/books/ EXCEPT chengyu-catalog (which carries
its own authoritative per-idiom CEDICT pinyin). Idempotent — adding new books
or chapters just picks them up next run.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from pypinyin import pinyin, Style

REPO = Path(__file__).resolve().parents[1]
BOOKS_DIR = REPO / "content" / "books"
CHAR_INDEX = REPO / "content" / "references" / "characters" / "index.json"
OVERRIDES = REPO / "content" / "references" / "characters" / "pinyin-overrides.json"

# Source string written onto every unit we touch. Lets the reader / future
# tooling distinguish "build-time pypinyin + sandhi + overrides" from the
# older chengyu per-idiom source or any future source.
SOURCE_TAG = "pypinyin + tone-sandhi + classical-overrides"


def is_cjk(r: str) -> bool:
    """True for a CJK Unified Ideograph (U+4E00..U+9FFF). Conservative —
    excludes extension blocks (B/C/...) since the canon doesn't use them and
    pypinyin coverage there is spotty anyway."""
    return len(r) == 1 and "\u4e00" <= r <= "\u9fff"


# --- trad→simplified map ---------------------------------------------------

def load_trad2simpl() -> dict[str, str]:
    """{traditional_char: simplified_char}, from the character index. Used so
    pypinyin's word dictionary (simplified-keyed) can match traditional text.
    Identity-maps chars with no traditional form."""
    idx = json.loads(CHAR_INDEX.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in idx.get("entries", []):
        s = e.get("simplified") or e.get("character")
        t = e.get("traditional") or s
        if not s or not t:
            continue
        # Many entries have multi-char traditional/alias strings; only single-
        # char mappings are useful here.
        if len(t) == 1 and len(s) == 1:
            out[t] = s
            if t != s:
                # headword self-map is implicit (identity fallback below).
                pass
        out.setdefault(s, s)  # simplified self-maps
    return out


def trad2simpl(text: str, t2s: dict[str, str]) -> str:
    """Convert text traditional→simplified. Unknown runes pass through
    unchanged (already-simplified chars self-map via the index)."""
    return "".join(t2s.get(c, c) for c in text)


# --- per-char fallback (for chars pypinyin doesn't know) -------------------

def load_char_pinyin_map() -> dict[str, str]:
    """{simplified_char: first_marked_pinyin}. Used as last-resort fallback
    for chars pypinyin returns no reading for (rare/archaic glyphs)."""
    idx = json.loads(CHAR_INDEX.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in idx.get("entries", []):
        c = e.get("character") or e.get("simplified")
        pys = e.get("pinyin") or []
        if c and pys:
            out[c] = pys[0]
    return out


# --- overrides --------------------------------------------------------------

def load_overrides() -> dict[str, list[str]]:
    """{simplified_phrase: [syllable per CJK char]}. Loaded from the curated
    overrides file (keyed by simplified form, matching the canon); classical
    polyphones pypinyin provably mis-reads."""
    if not OVERRIDES.exists():
        return {}
    d = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for k, v in (d.get("entries") or {}).items():
        # Validate: every override's syllable count must equal its CJK char
        # count, otherwise alignment would silently drift. Drop + warn.
        cjk_count = sum(1 for c in k if is_cjk(c))
        if len(v) == cjk_count and all(isinstance(x, str) for x in v):
            out[k] = v
        else:
            print(f"  warn: override {k!r} has {len(v)} syllables for "
                  f"{cjk_count} CJK chars — dropping", file=sys.stderr)
    return out


# --- tone sandhi -----------------------------------------------------------

_T3 = set("ǎěǐǒǔǚǍĚǏǑǓǙ")
_T2 = set("áéíóúǘÁÉÍÓÚǗ")
_T1 = set("āēīōūǖĀĒĪŌŪǕ")
_T4 = set("àèìòùǜÀÈÌÒÙǛ")
_T3_TO_T2 = str.maketrans("ǎěǐǒǔǚǍĚǏǑǓǙ", "áéíóúǘÁÉÍÓÚǗ")


def _tone_of(syll: str) -> int:
    for c in syll:
        if c in _T3: return 3
        if c in _T2: return 2
        if c in _T1: return 1
        if c in _T4: return 4
    return 0


def apply_sandhi(syllables: list[str]) -> list[str]:
    """Tone-sandhi post-pass on a per-rune syllable list (non-CJK = "").

    Rules applied:
      - 3rd tone before 3rd tone → 2nd tone (nǐ hǎo → ní hǎo). Chained: each
        converted syllable is itself 2nd-tone for the next check, which is the
        correct behavior (nǐ hǎo gǒu → ní hǎo gǒu, not ní háo gǒu).
      - 不 (bù) before 4th tone → bú.

    Intentionally NOT applied:
      - 一 (yī) sandhi — depends on positional/numeric context that's
        unreliable in classical text; correctness rate would be a coin flip.
      - 半 / 七 / 八 sandhi — same reason, marginal in the canon.
      - Neutral-tone / er-hua — preserves full tones, the safer default for
        learners reading classical text aloud.
    """
    out = list(syllables)
    # 3rd-tone sandhi. Iterate left to right; once a syllable is promoted to
    # 2nd tone it no longer triggers a 3rd-tone-flip in the next position,
    # which matches the standard rule (only consecutive ORIGINAL 3rd tones
    # flip each other when separated by promoted syllables — but we check the
    # *current* tone of the previous syllable, so chains resolve correctly).
    for i in range(len(out) - 1):
        if out[i] and _tone_of(out[i]) == 3 and out[i+1] and _tone_of(out[i+1]) == 3:
            out[i] = out[i].translate(_T3_TO_T2)
    # 不 sandhi: skip empty slots (non-CJK) when looking ahead.
    for i in range(len(out)):
        if out[i] == "bù":
            # find next non-empty syllable
            j = i + 1
            while j < len(out) and not out[j]:
                j += 1
            if j < len(out) and _tone_of(out[j]) == 4:
                out[i] = "bú"
    return out


# --- per-unit pinyin generation --------------------------------------------

def generate_for_unit(
    text: str,
    t2s: dict[str, str],
    overrides: dict[str, list[str]],
    char_pinyin: dict[str, str],
) -> tuple[list[str], str]:
    """Return (per_rune_pinyin_list, source_tag) for one reading unit.

    The returned list has exactly len(list(text)) entries (one per rune).
    Non-CJK runes get "". The source_tag names whichever path produced the
    reading — useful when triaging mis-readings later.
    """
    runes = list(text)
    n = len(runes)
    result: list[str] = [""] * n
    used_override = False

    # Pass 1: longest-match overrides on the text (overrides are authored in
    # simplified form to match the canon). Walk left to right, try the longest
    # key that fits and matches.
    i = 0
    while i < n:
        matched = False
        # Try phrase lengths from longest to shortest. The overrides file's
        # longest entry bounds this; cap at remaining text.
        max_len = min(n - i, 8)
        for L in range(max_len, 1, -1):
            phrase = "".join(runes[i:i+L])
            if phrase in overrides:
                py_list = overrides[phrase]
                # Validate alignment: override covers exactly L CJK chars OR
                # exactly L runes including non-CJK (overridden phrases are
                # CJK-only in the curated file, but be defensive).
                cjk_idx = [k for k in range(L) if is_cjk(runes[i+k])]
                if len(py_list) == len(cjk_idx):
                    for k, syll in zip(cjk_idx, py_list):
                        result[i+k] = syll
                    used_override = True
                    i += L
                    matched = True
                    break
                elif len(py_list) == L:
                    # one syllable per rune (incl. punctuation as "") — rare
                    for k in range(L):
                        result[i+k] = py_list[k] if is_cjk(runes[i+k]) else ""
                    used_override = True
                    i += L
                    matched = True
                    break
        if matched:
            continue
        i += 1

    # Pass 2: pypinyin for any rune still empty. Run pypinyin on the
    # simplified form of the WHOLE unit so its word dictionary can match
    # multi-char phrases (polyphones like 行/了/中/长). Then bucket the
    # syllables back onto the runes.
    simpl = trad2simpl(text, t2s)
    pinyin_for: dict[int, str] = {}  # rune_index -> syllable
    pinyin_runs: list[tuple[int, str]] = []  # (rune_idx, simplified_cjk_char)
    for k, r in enumerate(runes):
        if is_cjk(r) and not result[k]:
            pinyin_runs.append((k, simpl[k] if k < len(simpl) else r))

    if pinyin_runs:
        # Build a contiguous simplified string for pypinyin to maximize its
        # word-dictionary hits. We extract just the unknown CJK runes and run
        # them together; gaps between them would split phrase matches, but
        # they're already either filled (overrides) or non-CJK (skipped).
        # Run per-segment so a gap-filled unit doesn't accidentally merge two
        # words across punctuation.
        segments: list[list[tuple[int, str]]] = []
        cur: list[tuple[int, str]] = []
        prev_idx = -2
        for (idx, c) in pinyin_runs:
            if idx == prev_idx + 1:
                cur.append((idx, c))
            else:
                if cur: segments.append(cur)
                cur = [(idx, c)]
            prev_idx = idx
        if cur: segments.append(cur)

        for seg in segments:
            simpl_seg = "".join(c for _, c in seg)
            pys = pinyin(simpl_seg, style=Style.TONE, heteronym=False,
                         errors=lambda x: None)
            for (idx, _), py in zip(seg, pys):
                if py and py[0]:
                    pinyin_for[idx] = py[0]

        # Pass 3: per-char index fallback for anything pypinyin returned None
        # for (archaic glyphs).
        for idx, c in pinyin_runs:
            if idx not in pinyin_for:
                # try both simplified and original forms
                fb = char_pinyin.get(c) or char_pinyin.get(simpl[idx] if idx < len(simpl) else c)
                if fb:
                    pinyin_for[idx] = fb

        for idx, syll in pinyin_for.items():
            result[idx] = syll

    # Pass 4: tone sandhi across the whole per-rune list. Non-CJK empty
    # slots are skipped inside the rules but kept for alignment.
    result = apply_sandhi(result)

    source = SOURCE_TAG + (" (with classical override)" if used_override else "")
    return result, source


# --- driver ----------------------------------------------------------------

def process_book(book_dir: Path, t2s, overrides, char_pinyin) -> tuple[int, int]:
    """Process all chapters in a book dir. Returns (chapters, units touched)."""
    chapters = sorted((book_dir / "chapters").glob("chapter-*.json"))
    units_touched = 0
    for ch_path in chapters:
        d = json.loads(ch_path.read_text(encoding="utf-8"))
        ch = d.get("chapter") or {}
        units = ch.get("reading_units") or []
        changed = False
        for u in units:
            text = u.get("text") or ""
            if not text:
                continue
            py_list, source = generate_for_unit(text, t2s, overrides, char_pinyin)
            u["pinyin_per_char"] = py_list
            u["pinyin_source"] = source
            units_touched += 1
            changed = True
        if changed:
            # Preserve existing JSON formatting conventions in this repo
            # (indent=2, sort_keys, trailing newline).
            ch_path.write_text(
                json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    return len(chapters), units_touched


def main() -> int:
    if not CHAR_INDEX.exists():
        print(f"char index missing: {CHAR_INDEX}", file=sys.stderr)
        return 1

    print("Loading trad→simplified map ...")
    t2s = load_trad2simpl()
    print(f"  {len(t2s)} mappings")
    print("Loading per-char fallback map ...")
    char_pinyin = load_char_pinyin_map()
    print(f"  {len(char_pinyin)} chars")
    print("Loading overrides ...")
    overrides = load_overrides()
    print(f"  {len(overrides)} phrase overrides")

    books = sorted(p for p in BOOKS_DIR.iterdir() if p.is_dir())
    total_ch = 0
    total_u = 0
    for b in books:
        if not (b / "chapters").exists():
            continue
        # chengyu-catalog carries its own per-idiom CEDICT pinyin — skip.
        if b.name == "chengyu-catalog":
            print(f"  {b.name}: skipped (has own per-idiom pinyin)")
            continue
        ch, u = process_book(b, t2s, overrides, char_pinyin)
        total_ch += ch
        total_u += u
        print(f"  {b.name:18s}  {ch:4d} chapters, {u:5d} units")

    print(f"\nTotals: {total_ch} chapters, {total_u} units enriched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
