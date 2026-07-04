#!/usr/bin/env python3
"""Clean and migrate canonical content from da-xue into the-big-learn.

Input:  ../da-xue/content/books/<book>/{catalog.json, chapters/*.json}
Output: ./content/books/<book>/{catalog.json, chapters/*.json}

Cleans (per the approved Phase 1 plan):
  - strips stray footnote/endnote digits polluting reading text
  - strips segmentation spaces da-xue injected in sunzi/daodejing
  - adds translator/license/source_url per translation, per unit
  - reshapes translation_en -> canonical_translations[] (array, future-multi)
  - normalizes JSON (stable key order, readable UTF-8, 2-space indent)
  - re-validates every file parses

v1 books: da-xue, zhong-yong, lunyu, mengzi, daodejing (curated).
deferred books: copied as-is, flagged not-v1 (separate pass, not this script's job).

This script is READ-ONLY on da-xue; it only writes to the-big-learn/content/.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

# --- paths ------------------------------------------------------------------
REPO = Path(__file__).resolve().parents[1]
SRC_BOOKS = REPO.parent / "da-xue" / "content" / "books"
DST_BOOKS = REPO / "content" / "books"

V1_BOOKS = ["da-xue", "zhong-yong", "lunyu", "mengzi", "daodejing"]
DEFERRED_BOOKS = ["sunzi-bingfa", "san-zi-jing", "qian-zi-wen", "sanguo-yanyi"]

# --- translator attribution -------------------------------------------------
# Verified against actual JSON + the import tool's docstring. ChineseNotes hosts
# Legge's public-domain text, so "ChineseNotes (CC BY 4.0)" = delivery channel,
# translator is Legge. Modern copyrighted translators are NOT stored verbatim.
TRANSLATOR = {
    "da-xue":       ("Legge", 1891, "public domain",
                     "https://en.wikisource.org/wiki/The_Chinese_Classics/Volume_1/The_Great_Learning"),
    "zhong-yong":   ("Legge", 1885, "public domain",
                     "https://en.wikisource.org/wiki/The_Chinese_Classics/Volume_1/The_Doctrine_of_the_Mean"),
    "lunyu":        ("Legge", 1891, "public domain",
                     "https://en.wikisource.org/wiki/The_Chinese_Classics/Volume_1/Confucian_Analects"),
    "mengzi":       ("Legge", 1895, "public domain",
                     "https://en.wikisource.org/wiki/The_Chinese_Classics/Volume_2/The_Works_of_Mencius"),
    "daodejing":    ("Legge", 1891, "public domain",
                     "https://en.wikisource.org/wiki/The_Sacred_Books_of_the_East/Volume_39"),
    # deferred — not v1, copied as-is; attributions best-effort
    "sunzi-bingfa": ("ChineseNotes", None, "CC BY 4.0", "https://chinesenotes.com/sunzibingfa.html"),
    "san-zi-jing":  ("Giles", 1900, "public domain", "https://en.wikisource.org/wiki/San_Tzu_Ching"),
    "qian-zi-wen":  ("Chinasage", None, "CC BY 3.0", "https://www.chinasage.info/1000character-classic.htm"),
    "sanguo-yanyi": ("Brewitt-Taylor", 1925, "public domain",
                     "https://en.wikisource.org/wiki/Romance_of_the_Three_Kingdoms"),
}

# --- text cleaners ----------------------------------------------------------

# Footnote/endnote digits injected by upstream source (ctext/wikisource) that
# pollute the reading text. Pattern: an ASCII digit immediately adjacent to a
# CJK char or CJK punctuation. Keep digits inside legitimate western fields
# (none in reading text), so strip any digit touching CJK.
_FOOTNOTE_NEIGHBOR = re.compile(
    r"(?<=[\u3000-\u9fff\uff00-\uffef])\d+|"   # digit(s) after CJK
    r"\d+(?=[\u3000-\u9fff\uff00-\uffef])"      # digit(s) before CJK
)

# Segmentation spaces da-xue inserted between CJK chars / CJK punctuation
# (sunzi: 孫子 曰 ：). Strip ASCII space between two CJK-range chars or between
# a CJK char and CJK punctuation.
_CJK = r"\u3000-\u9fff\uff00-\uffef"
_SEG_SPACE = re.compile(rf"(?<=[{_CJK}]) +(?=[{_CJK}])")


def clean_text(text: str) -> str:
    """Apply all text cleaners. Idempotent."""
    if not text:
        return text
    text = _FOOTNOTE_NEIGHBOR.sub("", text)
    text = _SEG_SPACE.sub("", text)
    return text


def make_canonical_translation(en_text: str, book: str) -> dict | None:
    """Reshape a bare translation_en string into a canonical_translations entry."""
    if not en_text or not en_text.strip():
        return None
    translator, year, license_, url = TRANSLATOR[book]
    return {
        "translator": translator,
        "year": year,
        "license": license_,
        "source_url": url,
        "text": en_text,
    }


def clean_reading_unit(unit: dict, book: str) -> dict:
    """Clean text + reshape translation_en -> canonical_translations[] in one unit."""
    cleaned = dict(unit)
    if "text" in cleaned:
        cleaned["text"] = clean_text(cleaned["text"])

    en = None
    layers = cleaned.pop("generated_annotation", None)
    if isinstance(layers, dict):
        en = layers.get("layers", {}).get("translation_en")
    canonical = make_canonical_translation(en, book) if en else None
    cleaned["canonical_translations"] = [canonical] if canonical else []
    return cleaned


def clean_chapter(doc: dict, book: str) -> dict:
    """Clean a chapter document: chapter-level text + every reading unit."""
    out = json.loads(json.dumps(doc))  # deep copy, leave input untouched
    ch = out.get("chapter", {})
    if "text" in ch:
        ch["text"] = clean_text(ch["text"])
    if "summary" in ch:
        ch["summary"] = clean_text(ch["summary"])
    units = ch.get("reading_units", [])
    ch["reading_units"] = [clean_reading_unit(u, book) for u in units]
    # also clean any supplemental units
    for su in ch.get("supplemental_units", []):
        if "text" in su:
            su["text"] = clean_text(su["text"])
    return out


def dump_json(obj) -> str:
    """Stable, readable JSON. ensure_ascii=False keeps Chinese legible."""
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


# --- book-level provenance --------------------------------------------------

# Project-level notes added to each catalog.json so the choice is documented,
# not hidden.
V1_NOTES = {
    "provenance_note_v1": (
        "v1 canon. Chinese text via ctext.org (Si Shu Zhang Ju Ji Zhu). "
        "English translation: James Legge (public domain), seeded as the sole "
        "canonical translation per line. Modern copyrighted translations "
        "(Lau/Slingerland/Watson) are referenced by the platform, not stored. "
        "Source-of-truth file in this repo: content/SOURCES.md."
    ),
}


def process_book(book: str, *, curate: bool) -> tuple[int, int]:
    """Copy + clean one book. Returns (chapters_written, units_cleaned)."""
    src = SRC_BOOKS / book
    dst = DST_BOOKS / book
    if not src.exists():
        print(f"  [skip] source missing: {src}", file=sys.stderr)
        return 0, 0
    # fresh write — remove stale target so re-runs are clean
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    chapters_written = 0
    units_cleaned = 0

    # catalog.json — copy + (for v1) append project notes
    src_catalog = src / "catalog.json"
    if src_catalog.exists():
        catalog = json.loads(src_catalog.read_text(encoding="utf-8"))
        if curate:
            catalog.update(V1_NOTES)
            tr, yr, lic_, _ = TRANSLATOR[book]
            catalog["seed_translator"] = {"translator": tr, "year": yr, "license": lic_}
        (dst / "catalog.json").write_text(dump_json(catalog), encoding="utf-8")

    # chapters
    src_ch = src / "chapters"
    if not src_ch.exists():
        return chapters_written, units_cleaned
    (dst / "chapters").mkdir(exist_ok=True)
    for ch_file in sorted(src_ch.glob("chapter-*.json")):
        try:
            doc = json.loads(ch_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  [INVALID JSON] {ch_file}: {e}", file=sys.stderr)
            continue
        cleaned = clean_chapter(doc, book) if curate else doc
        units_cleaned += len(cleaned.get("chapter", {}).get("reading_units", []))
        out_path = dst / "chapters" / ch_file.name
        out_path.write_text(dump_json(cleaned), encoding="utf-8")
        # round-trip validate the file we just wrote
        json.loads(out_path.read_text(encoding="utf-8"))
        chapters_written += 1

    return chapters_written, units_cleaned


def main() -> int:
    if not SRC_BOOKS.exists():
        print(f"Source books root not found: {SRC_BOOKS}", file=sys.stderr)
        return 1

    print(f"src: {SRC_BOOKS}")
    print(f"dst: {DST_BOOKS}\n")

    print("== v1 books (curated) ==")
    total_units = 0
    for book in V1_BOOKS:
        ch, units = process_book(book, curate=True)
        total_units += units
        print(f"  {book:14s}  {ch:4d} chapters, {units:5d} units cleaned")
    print(f"  {'TOTAL':14s}  {'':>4s}         {total_units:5d} units\n")

    print("== deferred books (copied as-is, not v1) ==")
    for book in DEFERRED_BOOKS:
        ch, _ = process_book(book, curate=False)
        print(f"  {book:14s}  {ch:4d} chapters (copied, not cleaned)")

    print("\nDone. Next: write content/SOURCES.md (separate step).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
