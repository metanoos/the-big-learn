#!/usr/bin/env python3
"""Ingest the Hundred Family Surnames (百家姓 / bai-jia-xing) from Wikisource.

WHY THIS EXISTS
---------------
content/books/bai-jia-xing/ shipped as a placeholder stub (available:false,
chapter_count:0). This script ingests the real text so the book is readable
in the web app, matching the schema already used by qian-zi-wen (the other
Wikisource primer in the 三百千 triad).

SOURCE
  zh.wikisource.org/wiki/百家姓 — anonymous Song-dynasty primer, public
  domain ({{PD-old}} on the page). Wikisource is bulk-API-permitted, which
  is the same reason ingest_shi_jing.py uses it instead of ctext.org (whose
  ToS forbid automated download and will IP-ban).

CHAPTER / UNIT SHAPE
  One chapter "全篇", one reading unit per verse line — the same shape as
  qian-zi-wen. Each line is 8 CJK runes (four surnames, an ideographic
  space, four surnames); the closing line 第五言福　 carries only four.

ANNOTATION: HONEST GAP
  Bai Jia Xing is a rhymed list of surnames — there is no prose to
  translate. We deliberately ship NO translation_en layer, matching the
  chengyu-catalog discipline ("untranslated = honest gap, NOT fabricated").
  build_pinyin.py and build_word_gloss.py enrich every unit afterwards
  (they auto-discover all books under content/books/).

IDEMPOTENT & NETWORK-GENTLE
  - Caches the fetched wikitext to tools/raw/bai-jia-xing/baijiaxing.wt so
    re-runs don't re-fetch.
  - Sleeps between requests (Wikisource asks bots to be gentle).
  - Re-running overwrites content/books/bai-jia-xing/ deterministically.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from opencc import OpenCC

REPO = Path(__file__).resolve().parents[1]
DST = REPO / "content" / "books" / "bai-jia-xing"
CACHE = REPO / "tools" / "raw" / "bai-jia-xing"

UA = (
    "the-big-learn-ingestion/1.0 "
    "(educational classical-text reader; one-time ingest; "
    "https://www.wikisource.org/)"
)
SLEEP = 1.0  # seconds between live requests — be a polite API client

ZH_PAGE = "百家姓"

# opencc t2s is the repo-wide simplifier (see tools/to_simplified.py). For
# the overwhelming majority of surnames it is correct, but a handful of
# rare surname glyphs get over-simplified to a non-surname reading
# (曲→曲, 厐→厐). The map below restores those few to the canonical
# simplified surname form recorded in CC-CEDICT / Unihan, so we don't
# silently change a family name into a different character. Anything NOT
# in this map is left to opencc — we do not blanket-override.
SURNAME_RESTORE = {
    "曲": "曲",   # 曲 is a surname (曲嘉, 曲氏); opencc t2s collapses it to 曲
    "厐": "厐",   # 厐 is a rare surname variant; keep the wikisource form
}

CONVERTER = OpenCC("t2s")


# --- network ---------------------------------------------------------------

def _live_get(domain: str, path_or_query: str) -> str:
    """GET a URL, return body text. Retries on 429 with exponential backoff."""
    url = f"https://{domain}{path_or_query}"
    last_err = None
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429 and attempt < 4:
                wait = SLEEP * (2 ** attempt) * 4  # 4s, 8s, 16s, 32s
                print(
                    f"      429 rate-limited; backing off {wait:.0f}s "
                    f"(attempt {attempt + 1}/5)",
                    file=sys.stderr,
                )
                time.sleep(wait)
                continue
            raise
    raise last_err  # type: ignore[misc]


def fetch_wikitext(domain: str, page: str, cache_key: str) -> str:
    """Fetch a page's wikitext via the MediaWiki API, with on-disk cache."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE / f"{cache_key}.wt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    q = urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "wikitext", "format": "json"}
    )
    body = _live_get(domain, f"/w/api.php?{q}")
    time.sleep(SLEEP)
    try:
        wt = json.loads(body)["parse"]["wikitext"]["*"]
    except (KeyError, json.JSONDecodeError):
        wt = ""  # cache empty so we don't hammer on re-runs
    cache_file.write_text(wt, encoding="utf-8")
    return wt


# --- wikitext cleanup ------------------------------------------------------
# These three helpers are lifted verbatim from tools/ingest_shi_jing.py:130-160
# so both ingestors resolve zh-ws markup the same way. If they drift, fix both.

# Language converter: -{zh-hans:简; zh-hant:繁}- → take the traditional form.
# We resolve to zh-hant FIRST and let opencc t2s do the final simplification,
# which keeps the two-step pipeline identical to ingest_shi_jing.
_LANG_CONV = re.compile(r"-\{[^}]*\}-")


def _resolve_lang_conv(s: str) -> str:
    def pick(m: re.Match) -> str:
        inner = m.group()[2:-2]  # strip -{ }-
        for part in inner.split(";"):
            part = part.strip()
            if part.startswith(("zh-hant:", "zh-tw:", "zh-hk:", "zh-mo:")):
                return part.split(":", 1)[1]
        # Single-form converter like -{范}- or -{zh:阎;zh-hans:阎;zh-hant:阎}-
        # with no zh-hant tag: return the raw inner text (opencc handles it).
        if ":" not in inner:
            return inner
        # Tagged but no zh-hant: fall back to the first option's text.
        first = inner.split(";")[0].strip()
        return first.split(":", 1)[1] if ":" in first else first

    prev = None
    cur = s
    while prev != cur:  # nested converters
        prev = cur
        cur = _LANG_CONV.sub(pick, cur)
    return cur


def _strip_wikitext_templ(s: str) -> str:
    """Resolve simple templates we encounter in surname lines.

    {{另|栢|柏}}  → 栢   (zh-ws "variant reading" template: first arg is the
    canonical reading per ingest_shi_jing's convention; opencc then maps 栢→柏)
    {{·}} etc.    → pass through (collapse to empty)
    """
    s = re.sub(r"\{\{另\|([^|}]+)\|[^}]*\}\}", r"\1", s)
    s = re.sub(r"\{\{[^|}]*\}\}", "", s)
    return s


def clean_verse_line(raw: str) -> str:
    """Turn one raw wikitext verse line into clean TRADITIONAL Chinese.

    Simplification happens once, at the end, over the whole text — so that
    language-converter resolution (which keys on zh-hant) lands first.
    Mirrors ingest_shi_jing.clean_verse_line.
    """
    s = raw.strip().lstrip(":").strip()  # drop wikitext indent markup
    s = _resolve_lang_conv(s)
    s = _strip_wikitext_templ(s)
    s = s.replace("&nbsp;", " ")
    return s.strip()


# --- text simplification ---------------------------------------------------

def to_canonical_simplified(text: str) -> str:
    """opencc t2s + the small surname-restoration map.

    Restoring AFTER t2s means a handful of surname glyphs that opencc
    over-simplifies (曲→曲) come back to their canonical simplified surname
    form. See SURNAME_RESTORE.
    """
    simplified = CONVERTER.convert(text)
    for wrong, right in SURNAME_RESTORE.items():
        simplified = simplified.replace(wrong, right)
    return simplified


# --- parsing ---------------------------------------------------------------

# The closing line 百家姓终 is a colophon, not content.
COLOPHON = "百家姓终"


def extract_lines(wikitext: str) -> list[str]:
    """Pull the <poem>…</poem> block and return one cleaned line per entry.

    Blank lines and the colophon are dropped. The ideographic space (U+3000)
    that separates the two four-surname halves is preserved — it's how the
    reader aligns pinyin_per_char to rune positions (matches qian-zi-wen).
    """
    m = re.search(r"<poem>(.*?)</poem>", wikitext, re.DOTALL)
    if not m:
        raise RuntimeError("no <poem>…</poem> block found on the source page")
    lines: list[str] = []
    for raw in m.group(1).splitlines():
        line = clean_verse_line(raw)
        if not line or line == COLOPHON:
            continue
        lines.append(line)
    return lines


def cjk_count(s: str) -> int:
    return sum(1 for r in s if "\u4e00" <= r <= "\u9fff")


# --- output ----------------------------------------------------------------

def dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def build_unit(order: int, chapter_id: str, text: str, block_order: int) -> dict:
    return {
        "id": f"{chapter_id}-line-{order:03d}",
        "order": order,
        "character_count": len(text),
        "text": text,
        # source_block_* mirror qian-zi-wen's per-unit provenance: each unit
        # is one block of the source page, in source order.
        "source_block_chunk": 1,
        "source_block_order": block_order,
    }


def main() -> int:
    print("== Hundred Family Surnames (百家姓) ingestion ==")
    CACHE.mkdir(parents=True, exist_ok=True)

    # 1. Fetch
    print("[1/4] Fetching zh-ws 百家姓 ...")
    wt = fetch_wikitext("zh.wikisource.org", ZH_PAGE, "baijiaxing")
    if not wt:
        print("      ERROR: empty wikitext — aborting", file=sys.stderr)
        return 1

    # 2. Parse + clean + simplify
    print("[2/4] Extracting verse lines ...")
    trad_lines = extract_lines(wt)
    simp_lines = [to_canonical_simplified(ln) for ln in trad_lines]

    # 3. Write chapter
    print("[3/4] Writing chapter-001.json ...")
    if DST.exists():
        import shutil

        shutil.rmtree(DST)
    (DST / "chapters").mkdir(parents=True)

    chapter_id = "chapter-001"
    units = [
        build_unit(i, chapter_id, ln, i)
        for i, ln in enumerate(simp_lines, start=1)
    ]
    chapter_chars = sum(u["character_count"] for u in units)
    full_text = " ".join(u["text"] for u in units)

    chapter_doc = {
        "chapter": {
            "id": chapter_id,
            "order": 1,
            "title": "全篇",
            "summary": simp_lines[0] if simp_lines else "",
            "text": full_text,
            "character_count": chapter_chars,
            "reading_unit_count": len(units),
            "reading_units": units,
            "supplemental_text": "",
            "supplemental_unit_count": 0,
            "supplemental_units": [],
        },
        "chapter_path": "books/bai-jia-xing/chapters/chapter-001.json",
        "provider": "wikisource-html",
        "schema_version": 2,
        "source_title": (
            "百家姓 (zh.wikisource) — anonymous Song-dynasty primer, public "
            "domain ({{PD-old}}). No English translation shipped: the text is "
            "a rhymed list of surnames with no prose to translate (honest gap, "
            "not fabricated)."
        ),
        "source_url": "https://zh.wikisource.org/wiki/百家姓",
    }
    (DST / "chapters" / f"{chapter_id}.json").write_text(
        dump(chapter_doc), encoding="utf-8"
    )

    # 4. Catalog
    print("[4/4] Writing catalog.json ...")
    catalog = {
        "cache_dir": "books/bai-jia-xing",
        "catalog_path": "books/bai-jia-xing/catalog.json",
        "display_name": "Bai Jia Xing 百家姓",
        "name_zh": "百家姓",
        "name_pinyin": "Bǎi Jiā Xìng",
        "name_en": "The Hundred Family Surnames",
        "v1": False,
        "available": True,
        "tradition": "secular",
        "form": "primer",
        "year": 1000,
        "tier": "B",
        "difficulty": "foundational",
        "curriculum_order": 2,
        "title": "百家姓",
        "source_url": "https://zh.wikisource.org/wiki/百家姓",
        "source_title": (
            "v1 canon. Chinese text via zh.wikisource.org/wiki/百家姓 "
            "(anonymous Song-dynasty primer, public domain). No English "
            "translation is seeded: the text is a rhymed catalogue of "
            "surnames with no prose to translate — the reader surfaces "
            "pinyin and per-surname glosses instead. Honest gap, not "
            "fabricated. Source-of-truth file in this repo: content/SOURCES.md."
        ),
        "blurb": (
            "A rhymed catalogue of Chinese surnames — the second of the 三百千 "
            "primer triad. A literacy copybook, no doctrinal program."
        ),
        "background": (
            "The Bai Jia Xing (Hundred Family Surnames) is a Song-dynasty "
            "primer (c. 1000 CE) that lists several hundred Chinese surnames "
            "in four-character rhymed lines, beginning with the imperial "
            "surnames of the Song and its predecessors: 赵钱孙李 (Zhao, Qian, "
            "Sun, Li). It was one of three texts — together with San Zi Jing "
            "and Qian Zi Wen, the 三百千 — that almost every child in late "
            "imperial China memorized first, recited for the rhythm and the "
            "literacy, with no particular doctrinal content beyond a basic "
            "social map of the great family names. As a primer it is the "
            "lightest of the three: no curriculum like San Zi Jing, no "
            "allusive sweep like Qian Zi Wen, just a list — but the list "
            "itself is cultural knowledge every Mandarin speaker implicitly "
            "shares, and the text is short enough to read in one sitting. "
            "Tradition is `secular` for the same reason Qian Zi Wen is: a "
            "literacy copybook with no Confucian, Daoist, or Buddhist "
            "program. No English translation is shipped: the text is a list "
            "of names, so the reader surfaces pinyin and per-surname glosses "
            "rather than a prose rendering."
        ),
        "provider": "wikisource-html",
        "chapter_count": 1,
        "chapters": [
            {
                "chapter_path": "books/bai-jia-xing/chapters/chapter-001.json",
                "id": chapter_id,
                "order": 1,
                "title": "全篇",
                "summary": simp_lines[0] if simp_lines else "",
                "character_count": chapter_chars,
                "reading_unit_count": len(units),
                "supplemental_unit_count": 0,
            }
        ],
        "commentary_chapter_count": 0,
        "commentary_chapters": [],
    }
    (DST / "catalog.json").write_text(dump(catalog), encoding="utf-8")

    # Report
    cjk_total = sum(cjk_count(u["text"]) for u in units)
    print("Done.\n")
    print(f"  lines (units)     : {len(units)}")
    print(f"  runes (incl. 　)  : {chapter_chars}")
    print(f"  CJK surnames      : {cjk_total}")
    print(
        "\nNext: run tools/build_pinyin.py then tools/build_word_gloss.py "
        "to enrich every unit with pinyin_per_char and word_spans."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
