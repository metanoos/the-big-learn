#!/usr/bin/env python3
"""Attach verbatim origin links to chengyu units.

For each of the 1,000 chengyu, search a curated set of *origin-source* books
(classical philosophy we ship) for the first reading unit whose Chinese text
contains the 4-character idiom verbatim. Where found, attach:

    "origin": {
        "book": "lunyu",
        "chapter": 2,            # bare integer, matches /books/lunyu/2#line-N
        "line": 11,              # the origin unit's `order`
        "snippet": "子曰：「温故而知新…」"  # ~80-char context, no round-trip needed
    }

to the chengyu unit. Idempotent: re-runs clear stale `origin` fields before
re-attaching. Unmatched idioms simply get no `origin`.

WHY THIS IS A SEPARATE SCRIPT, not part of build_chengyu.py
----------------------------------------------------------
build_chengyu.py wipes content/books/chengyu-catalog/ on each run and reads
from a sibling source repo (agent-skill-the-big-learn) that isn't always
present locally. This script reads the *committed* JSON and augments it in
place, so it works wherever the catalog is checked out and survives a
build_chengyu.py re-run by being re-run itself afterwards.

WHY ORIGIN-SOURCE BOOKS ONLY
----------------------------
A verbatim hit is not always an origin. Sanguo Yanyi uses 78 of the matched
idioms but coined almost none of them — labeling those "Origin: Sanguo Yanyi"
would be wrong. So we search only books that are themselves plausible origin
sources: the v1 classics + Sunzi (a genuine source for military idioms).
Sanguo, San Zi Jing, and Qian Zi Wen are deliberately excluded. This drops
coverage to ~5-6% but every shipped link is defensible — the same honest-gap
pattern the catalog uses for missing glosses.

Priority order matters: when an idiom appears in multiple source books, the
earlier-listed book wins (lunyu before mengzi before daodejing...).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BOOKS_DIR = REPO / "content" / "books"

# Origin-source books in priority order. See module docstring for the rationale.
ORIGIN_BOOKS = ["lunyu", "mengzi", "daodejing", "zhong-yong", "da-xue", "sunzi-bingfa"]

# Human-facing book names for the log only (the card UI has its own lookup).
BOOK_LABEL = {
    "lunyu": "Lunyu 论语",
    "mengzi": "Mengzi 孟子",
    "daodejing": "Daodejing 道德经",
    "zhong-yong": "Zhong Yong 中庸",
    "da-xue": "Da Xue 大学",
    "sunzi-bingfa": "Sunzi Bingfa 孙子兵法",
}

CHAPTER_NUM = re.compile(r"chapter-(\d+)")


def reading_units(book: str):
    """Yield (book, chapter_num, unit_order, unit_text) for every reading unit
    in the book, in chapter-then-order sequence."""
    chdir = BOOKS_DIR / book / "chapters"
    for cf in sorted(chdir.glob("chapter-*.json")):
        m = CHAPTER_NUM.search(cf.stem)
        chapter_num = int(m.group(1)) if m else 0
        d = json.loads(cf.read_text())
        for u in d.get("chapter", {}).get("reading_units", []) or []:
            yield book, chapter_num, u.get("order", 0), u.get("text", "")


def build_origin_index(idioms: set[str]):
    """For each idiom, find the first verbatim hit across ORIGIN_BOOKS (in
    priority order). Returns {idiom: {book, chapter, line, snippet}}.

    Per-book priority is enforced by scanning one book fully before the next:
    an idiom found in lunyu is never overwritten by a later mengzi hit.
    """
    index: dict[str, dict] = {}
    for book in ORIGIN_BOOKS:
        for _, chapter_num, order, text in reading_units(book):
            if not text:
                continue
            for idiom in idioms:
                if idiom in index:
                    continue  # earlier-priority book already won
                if idiom in text:
                    snippet = text.strip()
                    if len(snippet) > 80:
                        snippet = snippet[:79] + "…"
                    index[idiom] = {
                        "book": book,
                        "chapter": chapter_num,
                        "line": order,
                        "snippet": snippet,
                    }
    return index


def main() -> None:
    chdir = BOOKS_DIR / "chengyu-catalog" / "chapters"
    chapter_files = sorted(chdir.glob("chapter-*.json"))

    idioms: set[str] = set()
    units_by_file: list[tuple[Path, list[dict]]] = []
    for cf in chapter_files:
        d = json.loads(cf.read_text())
        units = d.setdefault("chapter", {}).setdefault("reading_units", [])
        # Clear stale origins first so re-runs are clean.
        for u in units:
            u.pop("origin", None)
            if u.get("text"):
                idioms.add(u["text"])
        units_by_file.append((cf, units))

    print(f"scanning {len(idioms)} idioms across {len(ORIGIN_BOOKS)} origin-source books…")
    index = build_origin_index(idioms)

    attached = 0
    per_book: dict[str, int] = {}
    for cf, units in units_by_file:
        changed = False
        for u in units:
            origin = index.get(u.get("text", ""))
            if origin:
                u["origin"] = origin
                attached += 1
                per_book[origin["book"]] = per_book.get(origin["book"], 0) + 1
                changed = True
        if changed:
            d = json.loads(cf.read_text())
            d["chapter"]["reading_units"] = units
            cf.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n")

    print(f"attached origins: {attached} / {len(idioms)} idioms "
          f"({100 * attached // max(1, len(idioms))}%)")
    for book in ORIGIN_BOOKS:
        n = per_book.get(book, 0)
        if n:
            print(f"  {BOOK_LABEL[book]:24s} {n}")
    unmatched = len(idioms) - attached
    print(f"  unmatched (no verbatim origin in shipped classics): {unmatched}")
    print("\nNote: coverage grows as roadmap texts (Shi Jing, Zuozhuan, Zhuangzi) ship.")


if __name__ == "__main__":
    main()
