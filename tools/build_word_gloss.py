#!/usr/bin/env python3
"""Generate per-reading-unit word spans + glosses for the chapter reader.

WHY THIS EXISTS
---------------
The reader used to surface only per-char glosses: clicking 学 in 大学 showed
"study/learn" but never the token-level meaning "The Great Learning." This
script pre-computes, for every reading unit, a set of word spans — each one a
multi-char compound with its pinyin and gloss — so the reader can show the
*token* the clicked char belongs to, on top of the per-char breakdown.

Mirrors build_pinyin.py's pattern (build-time enrichment, idempotent, scoped
to content/books/** except chengyu-catalog, writes one field per unit,
preserves everything else byte-for-byte). Shares the same layered-segmentation
discipline as pinyin: curated classical overrides first, then a dictionary,
then per-char fallback.

PIPELINE (per reading unit)
---------------------------
1. Longest-match overrides (word-gloss-overrides.json): verified classical
   compounds matched on the TRADITIONAL form (the canon is traditional).
   Highest priority — these fix cases where CC-CEDICT is wrong (大学 =
   "university") or absent (明明德).
2. CC-CEDICT longest-match on the SIMPLIFIED form (CC-CEDICT is
   simplified-keyed; we reuse build_pinyin.py's trad→simplified map so the
   match lands). Supplies modern-Mandarin glosses for the rest of the
   compounds. The reader's provenance label distinguishes these from the
   classical overrides so the user knows what they're reading.
3. Per-char fallback: any CJK rune not covered by 1 or 2 becomes a
   single-char span with no gloss — the existing per-char breakdown already
   covers it.

OUTPUT
------
Each reading unit gains `word_spans: [{start, end, word, pinyin, gloss, source}]`
where start/end are rune indices into `text` (same alignment contract as
pinyin_per_char — non-CJK runes occupy a slot but no span covers them), gloss
may be null (per-char fallback), and source ∈
{"classical-override", "CC-CEDICT", "char"}.

IDEMPOTENT & SAFE TO RE-RUN
---------------------------
Only `word_spans` is touched. Re-running with updated overrides propagates.

SCOPE
-----
All book chapters under content/books/ EXCEPT chengyu-catalog (each unit is
already a 4-char idiom with its own canonical translation; the reader shows
that translation elsewhere, so a single word span per unit would be redundant).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Shared CC-CEDICT loader (extracted from build_chengyu.py so this builder and
# that one don't drift on the download/parse/numeric→marked logic).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cedict import load_cedict  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
BOOKS_DIR = REPO / "content" / "books"
CHAR_INDEX = REPO / "content" / "references" / "characters" / "index.json"
OVERRIDES = REPO / "content" / "references" / "characters" / "word-gloss-overrides.json"

# Longest compound we'll attempt to match. The overrides file caps out at 4-5
# chars; CC-CEDICT has a few long entries but anything past 6 is almost always
# a full sentence fragment that isn't a useful "word" to surface. Keep this
# generous so override phrases like 大学之道 (5) land.
MAX_MATCH_LEN = 8

# CC-CEDICT gloss cap for the span field. The reader truncates in the popover
# anyway, but bounding here keeps the JSON lean (CC-CEDICT glosses can run to
# 200+ chars with examples and CL: classifiers).
MAX_CEDICT_GLOSS = 100


def is_cjk(r: str) -> bool:
    """True for a CJK Unified Ideograph (U+4E00..U+9FFF). Conservative —
    matches build_pinyin.py's range (no extension blocks; the canon doesn't
    use them)."""
    return len(r) == 1 and "\u4e00" <= r <= "\u9fff"


# --- trad→simplified map (mirrors build_pinyin.py) -------------------------
# CC-CEDICT is simplified-keyed; the canon is traditional. Without this map,
# 大学 wouldn't match CEDICT's 大学 entry. Same construction as build_pinyin.py.

def load_trad2simpl() -> dict[str, str]:
    """{traditional_char: simplified_char}, from the character index."""
    idx = json.loads(CHAR_INDEX.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in idx.get("entries", []):
        s = e.get("simplified") or e.get("character")
        t = e.get("traditional") or s
        if not s or not t:
            continue
        if len(t) == 1 and len(s) == 1:
            out[t] = s
        out.setdefault(s, s)
    return out


def trad2simpl(text: str, t2s: dict[str, str]) -> str:
    """Convert traditional→simplified. Unknown runes pass through unchanged."""
    return "".join(t2s.get(c, c) for c in text)


# --- overrides -------------------------------------------------------------

def load_overrides() -> dict[str, dict[str, str]]:
    """{traditional_compound: {pinyin, gloss, source}}. Loaded from the curated
    overrides file; classical compounds whose CC-CEDICT gloss is wrong/absent."""
    if not OVERRIDES.exists():
        return {}
    d = json.loads(OVERRIDES.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = {}
    for k, v in (d.get("entries") or {}).items():
        # Validate: key is non-empty, value has the required fields. Skip + warn
        # rather than crash so a malformed entry doesn't block the whole build.
        if k and isinstance(v, dict) and v.get("pinyin") and v.get("gloss"):
            out[k] = {
                "pinyin": v["pinyin"],
                "gloss": v["gloss"],
                "source": v.get("source", "curated"),
            }
        else:
            print(f"  warn: override {k!r} malformed — dropping", file=sys.stderr)
    return out


# --- segmentation ----------------------------------------------------------

def segment(
    text: str,
    overrides: dict[str, dict[str, str]],
    cedict: dict[str, tuple[str, str]],
    t2s: dict[str, str],
) -> list[dict]:
    """Segment a reading unit's text into word spans.

    Walks the text rune-by-rune. At each CJK rune, tries the longest match in
    this priority order: classical overrides (traditional form), CC-CEDICT
    (simplified form), then per-char fallback. Non-CJK runes are skipped (no
    span covers them) — the renderer handles spacing/punctuation as it does
    today.

    Returns a list of {start, end, word, pinyin, gloss, source} dicts, ordered
    by start position, covering every CJK rune in `text`.
    """
    runes = list(text)
    n = len(runes)
    spans: list[dict] = []
    i = 0
    while i < n:
        r = runes[i]
        if not is_cjk(r):
            i += 1
            continue

        matched = False
        # Try phrase lengths from longest to shortest, starting at this rune.
        # Both override and CEDICT layers are consulted at each length; the
        # override layer wins when both match at the same length (classical
        # sense beats modern-Mandarin sense by design).
        max_len = min(n - i, MAX_MATCH_LEN)
        for L in range(max_len, 0, -1):
            phrase_trad = "".join(runes[i:i + L])

            # Layer 1: classical override (traditional form).
            ov = overrides.get(phrase_trad)
            if ov:
                spans.append({
                    "start": i, "end": i + L, "word": phrase_trad,
                    "pinyin": ov["pinyin"], "gloss": ov["gloss"],
                    "source": "classical-override",
                })
                i += L
                matched = True
                break

            # Layer 2: CC-CEDICT (simplified form). Single-char CEDICT entries
            # are skipped here (L>=2) — they'd shadow the per-char fallback
            # with a modern-Mandarin gloss that adds nothing over the char
            # breakdown, and would also block the per-char fallback for every
            # common char. Compound (2+) entries only.
            if L >= 2:
                phrase_simp = trad2simpl(phrase_trad, t2s)
                entry = cedict.get(phrase_simp)
                if entry:
                    pinyin, defs = entry
                    gloss = defs if len(defs) <= MAX_CEDICT_GLOSS else defs[:MAX_CEDICT_GLOSS - 1] + "…"
                    spans.append({
                        "start": i, "end": i + L, "word": phrase_trad,
                        # CEDICT pinyin is already tone-marked by load_cedict.
                        "pinyin": pinyin, "gloss": gloss,
                        "source": "CC-CEDICT",
                    })
                    i += L
                    matched = True
                    break

        # Layer 3: per-char fallback. No word match → single-char span with no
        # gloss; the reader's per-char breakdown covers it.
        if not matched:
            spans.append({
                "start": i, "end": i + 1, "word": r,
                "pinyin": None, "gloss": None, "source": "char",
            })
            i += 1

    return spans


# --- per-unit driver -------------------------------------------------------

def generate_for_unit(
    text: str,
    overrides: dict[str, dict[str, str]],
    cedict: dict[str, tuple[str, str]],
    t2s: dict[str, str],
) -> list[dict]:
    """Return the word_spans list for one reading unit."""
    return segment(text, overrides, cedict, t2s)


def process_book(
    book_dir: Path,
    overrides: dict[str, dict[str, str]],
    cedict: dict[str, tuple[str, str]],
    t2s: dict[str, str],
) -> tuple[int, int, int]:
    """Process all chapters in a book. Returns (chapters, units, span count)."""
    chapters = sorted((book_dir / "chapters").glob("chapter-*.json"))
    units_touched = 0
    span_count = 0
    for ch_path in chapters:
        d = json.loads(ch_path.read_text(encoding="utf-8"))
        ch = d.get("chapter") or {}
        units = ch.get("reading_units") or []
        changed = False
        for u in units:
            text = u.get("text") or ""
            if not text:
                continue
            spans = generate_for_unit(text, overrides, cedict, t2s)
            u["word_spans"] = spans
            units_touched += 1
            span_count += len(spans)
            changed = True
        if changed:
            # Preserve existing JSON formatting conventions (matches
            # build_pinyin.py: indent=2, sort_keys, trailing newline).
            ch_path.write_text(
                json.dumps(d, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    return len(chapters), units_touched, span_count


def main() -> int:
    if not CHAR_INDEX.exists():
        print(f"char index missing: {CHAR_INDEX}", file=sys.stderr)
        return 1

    print("Loading trad→simplified map ...")
    t2s = load_trad2simpl()
    print(f"  {len(t2s)} mappings")
    print("Loading overrides ...")
    overrides = load_overrides()
    print(f"  {len(overrides)} compound overrides")
    print("Loading CC-CEDICT (2+ char compounds) ...")
    cedict = load_cedict(min_simp_len=2)
    print(f"  {len(cedict)} compound entries\n")

    books = sorted(p for p in BOOKS_DIR.iterdir() if p.is_dir())
    total_ch = 0
    total_u = 0
    total_spans = 0
    for b in books:
        if not (b / "chapters").exists():
            continue
        # chengyu-catalog: each unit is already a 4-char idiom with its own
        # canonical translation; a word span per unit would be redundant.
        if b.name == "chengyu-catalog":
            print(f"  {b.name}: skipped (units carry own translations)")
            continue
        ch, u, spans = process_book(b, overrides, cedict, t2s)
        total_ch += ch
        total_u += u
        total_spans += spans
        print(f"  {b.name:18s}  {ch:4d} chapters, {u:5d} units, {spans:6d} spans")

    print(f"\nTotals: {total_ch} chapters, {total_u} units, {total_spans} spans")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
