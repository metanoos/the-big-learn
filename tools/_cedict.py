"""Shared CC-CEDICT loader + numeric-to-marked-pinyin converter.

Extracted verbatim from build_chengyu.py so both the chengyu catalog and the
word-gloss builder (build_word_gloss.py) share one canonical download/parse
path. The chengyu builder keys phrases of 4+ chars; the word-gloss builder
wants 2-3 char compounds too — hence the `min_simp_len` parameter (formerly a
hardcoded `len(simp) < 4` filter inside load_cedict).

Network: downloads CC-CEDICT once (~4MB gz) to /tmp on first use, then reads
the uncompressed cache on subsequent runs. The cache is shared across both
consumers; safe because parsing is deterministic.
"""
from __future__ import annotations

import gzip
import re
import sys
import urllib.request
from pathlib import Path

CEDICT_CACHE = Path("/tmp/tbl_cedict.tsv")  # uncompressed cache for re-runs
CEDICT_URL = "https://cc-cedict.org/editor/editor_export_cedict.php?c=gz"
CEDICT_LINE = re.compile(r"^(\S+)\s+(\S+)\s+\[(.*?)\]\s+/(.*)/$")

# numeric-tone -> tone-mark map (a1..a4, etc.)
_TONE_MARKS = {
    "a": "āáǎà", "e": "ēéěè", "i": "īíǐì", "o": "ōóǒò",
    "u": "ūúǔù", "ü": "ǖǘǚǜ", "A": "ĀÁǍÀ", "E": "ĒÉĚÈ",
    "I": "ĪÍǏÌ", "O": "ŌÓǑÒ", "U": "ŪÚǓÙ", "Ü": "ǕǗǙǛ",
}


def numeric_to_marked(numeric: str) -> str:
    """'chi2 zhi1 yi3 heng2' -> 'chí zhī yǐ héng'."""
    out = []
    for syll in numeric.split():
        out.append(_one_syllable(syll))
    return " ".join(out)


def _one_syllable(syll: str) -> str:
    m = re.match(r"^([a-züA-ZÜ]+?)([1-5])?$", syll)
    if not m:
        return syll
    base, tone = m.group(1), m.group(2)
    if not tone or tone == "5":
        return base.replace("v", "ü").replace("V", "Ü")
    tone = int(tone)
    # handle u: -> ü
    base = base.replace("v", "ü").replace("V", "Ü")
    # find vowel to mark: priority a,o,e, then last of a pair, else first vowel
    vowels = "aeiouüAEIOUÜ"
    # rule: if 'a' or 'e' or 'o' present, mark the first of those; else mark last vowel
    idx = -1
    for pri in ("a", "e", "o", "A", "E", "O"):
        if pri in base:
            idx = base.index(pri)
            break
    if idx < 0:
        # mark the last vowel in the cluster (or first if no cluster)
        v_positions = [i for i, c in enumerate(base) if c in vowels]
        if v_positions:
            # if two+ consecutive vowels, mark the second; else the only one
            seq = [v_positions[0]]
            for p in v_positions[1:]:
                if p == seq[-1] + 1:
                    seq.append(p)
                else:
                    break
            idx = seq[-1] if len(seq) >= 2 else seq[0]
    if idx < 0:
        return base  # no vowel (shouldn't happen for valid pinyin)
    c = base[idx]
    marked = _TONE_MARKS.get(c, c)
    if c in _TONE_MARKS:
        return base[:idx] + marked[tone - 1] + base[idx + 1:]
    return base


def load_cedict(min_simp_len: int = 1) -> dict[str, tuple[str, str]]:
    """Load CC-CEDICT, returning {simplified: (marked_pinyin, slash_joined_defs)}.

    `min_simp_len` filters entries by simplified-form length: build_chengyu
    passes 4 (idioms only); build_word_gloss passes 2 (compounds). Last entry
    wins on duplicate simplified keys, matching the source file's order.

    Pinyin is tone-marked via numeric_to_marked; defs are joined with " / ".
    Consumers that want a shorter gloss for a small UI (e.g. the popover) do
    their own truncation on top of this canonical, lossless form.
    """
    raw = None
    if CEDICT_CACHE.exists():
        raw = CEDICT_CACHE.read_bytes()
    else:
        print(f"  downloading CC-CEDICT from {CEDICT_URL} ...", file=sys.stderr)
        req = urllib.request.Request(CEDICT_URL, headers={"User-Agent": "tbl-chengyu/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = gzip.decompress(r.read())
        CEDICT_CACHE.write_bytes(raw)
        print(f"  cached at {CEDICT_CACHE} ({len(raw)} bytes)", file=sys.stderr)

    entries: dict[str, tuple[str, str]] = {}
    text = raw.decode("utf-8", errors="replace")
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        m = CEDICT_LINE.match(line)
        if not m:
            continue
        _trad, simp, pinyin_num, defs = m.groups()
        if len(simp) < min_simp_len:
            continue
        marked = numeric_to_marked(pinyin_num)
        clean_defs = " / ".join(d for d in defs.split("/") if d)
        entries[simp] = (marked, clean_defs)
    return entries
