#!/usr/bin/env python3
"""Rebuild the chengyu catalog: 1,000 curated idioms with pinyin + honest translations.

Source:  agent-skill-the-big-learn/books/chengyu-catalog/  (20 themed ch × 50)
Output:  the-big-learn/content/books/chengyu-catalog/

Strategy (decided after measuring 52.8% CEDICT coverage on the 1,000):
  - PINYIN:  CEDICT where the phrase exists (authoritative); else composed from
             the per-character index (the-big-learn/content/references/.../index.json),
             which has 100% char coverage for our idioms. ~100% pinyin coverage.
  - TRANSLATION: CC-CEDICT ONLY. 528/1000 get a real definition; 472 get null
             (honest gap). We do NOT fabricate translations — the original
             catalog's ~13% meaning-inverting errors came from a Google-Translate
             fallback. The platform's user submissions + LLM feedback fill gaps;
             seeding them with wrong MT would defeat the purpose.

Reshapes the source text-blob into proper reading_units[] (one per idiom),
matching the classical-books schema. Preserves the themed chapter titles
(real pedagogical curation).

Network: downloads CC-CEDICT once (~4MB gz) to /tmp. Re-uses cached file.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

# _cedict holds the shared CC-CEDICT download/parse + numeric→marked pinyin
# logic. Importing it here keeps build_chengyu.py and build_word_gloss.py from
# drifting. min_simp_len=4 preserves the idiom-only filter this builder has
# always applied (now parameterized in _cedict.load_cedict).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cedict import load_cedict  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SRC = REPO.parent / "agent-skill-the-big-learn" / "books" / "chengyu-catalog"
DST = REPO / "content" / "books" / "chengyu-catalog"
CHAR_INDEX = REPO / "content" / "references" / "characters" / "index.json"


def load_char_index() -> dict[str, dict]:
    """{character: entry}. For composing pinyin of idioms CEDICT lacks."""
    idx = json.loads(CHAR_INDEX.read_text(encoding="utf-8"))
    out = {}
    for e in idx.get("entries", []):
        c = e.get("character")
        if c:
            out[c] = e
    return out


# --- the build --------------------------------------------------------------

def derive_pinyin_from_chars(idiom: str, char_index: dict) -> str | None:
    """Compose pinyin per-character. Returns space-joined, or None if any char unknown."""
    parts = []
    for c in idiom:
        e = char_index.get(c)
        if not e:
            return None
        py = e.get("pinyin") or []
        if not py:
            return None
        parts.append(py[0])  # index stores marked already
    return " ".join(parts)


def build_unit(idiom: str, order: int, chapter_id: str, cedict: dict, char_index: dict) -> dict:
    """One reading unit per idiom."""
    entry = cedict.get(idiom)
    pinyin = None
    translation = None
    source = None
    if entry:
        pinyin, defs = entry
        translation = defs
        source = "CC-CEDICT (CC BY-SA 3.0)"
    else:
        derived = derive_pinyin_from_chars(idiom, char_index)
        if derived:
            pinyin = derived
            source = "derived from per-character index"
        # translation stays None — honest gap, not fabricated

    canonical = []
    if translation:
        canonical.append({
            "translator": "CC-CEDICT",
            "year": None,
            "license": "CC BY-SA 3.0",
            "source_url": "https://cc-cedict.org/",
            "text": translation,
        })

    return {
        "id": f"{chapter_id}-line-{order:03d}",
        "order": order,
        "character_count": len(idiom),
        "text": idiom,
        "pinyin": pinyin,
        "pinyin_source": source,
        "canonical_translations": canonical,
    }


def dump_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    if not SRC.exists():
        print(f"source missing: {SRC}", file=sys.stderr)
        return 1
    if not CHAR_INDEX.exists():
        print(f"char index missing: {CHAR_INDEX}", file=sys.stderr)
        return 1

    print("Loading CC-CEDICT ...")
    cedict = load_cedict(min_simp_len=4)
    print(f"  {len(cedict)} phrase entries (4+-char)")
    print("Loading character index ...")
    char_index = load_char_index()
    print(f"  {len(char_index)} characters\n")

    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    (DST / "chapters").mkdir()

    total = 0
    with_pinyin = 0
    with_translation = 0
    chapters_meta = []

    for ch_num in range(1, 21):
        src_path = SRC / "chapters" / f"chapter-{ch_num:03d}.json"
        src_doc = json.loads(src_path.read_text(encoding="utf-8"))
        ch = src_doc["chapter"]
        idioms = [l.strip() for l in ch["text"].split("\n") if l.strip()]
        chapter_id = f"chapter-{ch_num:03d}"

        units = []
        for i, idiom in enumerate(idioms, 1):
            u = build_unit(idiom, i, chapter_id, cedict, char_index)
            units.append(u)
            total += 1
            if u["pinyin"]:
                with_pinyin += 1
            if u["canonical_translations"]:
                with_translation += 1

        chapter_text = "\n".join(idioms)
        doc = {
            "chapter": {
                "id": chapter_id,
                "order": ch_num,
                "title": ch["title"],
                "summary": ch.get("summary", ch["title"]),
                "text": chapter_text,
                "character_count": sum(len(i) for i in idioms),
                "reading_unit_count": len(units),
                "reading_units": units,
                "supplemental_text": "",
                "supplemental_unit_count": 0,
                "supplemental_units": [],
            },
            "chapter_path": f"books/chengyu-catalog/chapters/{chapter_id}.json",
            "provider": "bundled-local",
            "schema_version": 2,
            "source_title": "成语目录",
            "source_url": "bundled://chengyu-catalog",
        }
        (DST / "chapters" / f"{chapter_id}.json").write_text(dump_json(doc), encoding="utf-8")
        chapters_meta.append({
            "id": chapter_id,
            "order": ch_num,
            "title": ch["title"],
            "reading_unit_count": len(units),
        })
        print(f"  ch{ch_num:02d} {ch['title'][:24]:24s}  {len(units)} idioms")

    # catalog.json
    catalog = {
        "title": "Chengyu Catalog",
        "cache_dir": "chengyu-catalog",
        "catalog_path": "books/chengyu-catalog/catalog.json",
        "chapter_count": 20,
        "chapters": chapters_meta,
        "commentary_chapter_count": 0,
        "commentary_chapters": [],
        "pedagogy_note": (
            "Pedagogy-first ordering: chapters 1-6 hand-curated core idioms by theme "
            "(study, judgment, action, collaboration, character, high-frequency story "
            "idioms); 7-20 continue from transparent/common toward more source-heavy "
            "and literary. 1,000 four-character idioms in 20 themed chapters."
        ),
        "provenance_note": (
            "Curated 1,000-idiom subset. Idioms originally derived from the "
            "MIT-licensed pwxcoo/chinese-xinhua idiom list, reordered for pedagogy. "
            "Pinyin: CC-CEDICT where available, else composed from the per-character "
            "index. Translations: CC-CEDICT ONLY (no machine translation — the prior "
            "3,000-idiom catalog had ~13% meaning-inverting errors from a GT fallback). "
            f"{with_translation}/{total} have a canonical translation; the rest are "
            "honest gaps the platform's users fill."
        ),
        "selection_note": (
            f"Stats: {with_pinyin}/{total} with pinyin ({100*with_pinyin/total:.1f}%), "
            f"{with_translation}/{total} with CC-CEDICT translation "
            f"({100*with_translation/total:.1f}%)."
        ),
        "source_url": "bundled://chengyu-catalog",
    }
    (DST / "catalog.json").write_text(dump_json(catalog), encoding="utf-8")

    print(f"\nTotals: {total} idioms")
    print(f"  pinyin:      {with_pinyin}/{total} ({100*with_pinyin/total:.1f}%)")
    print(f"  translation: {with_translation}/{total} ({100*with_translation/total:.1f}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
