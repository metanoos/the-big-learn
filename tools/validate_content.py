#!/usr/bin/env python3
"""Validate every catalog and chapter contract consumed by the reader.

This is deliberately dependency-free so it can run locally and in CI. It
checks references/counts plus the rune-indexed pinyin and word-span fields most
likely to drift when source text is edited after enrichment.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOKS_ROOT = REPO_ROOT / "content" / "books"


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: invalid JSON: {exc}")
        return None
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)}: root must be an object")
        return None
    return value


def validate_unit(path: Path, unit: Any, errors: list[str]) -> None:
    label = path.relative_to(REPO_ROOT)
    if not isinstance(unit, dict):
        errors.append(f"{label}: reading unit must be an object")
        return
    text = unit.get("text")
    if not isinstance(text, str) or not text:
        errors.append(f"{label}: unit {unit.get('id', '?')} has no text")
        return
    runes = list(text)
    pinyin = unit.get("pinyin_per_char")
    if pinyin is not None and (not isinstance(pinyin, list) or len(pinyin) != len(runes)):
        errors.append(
            f"{label}: unit {unit.get('id', '?')} pinyin_per_char has "
            f"{len(pinyin) if isinstance(pinyin, list) else 'non-list'} entries; want {len(runes)}"
        )
    translations = unit.get("canonical_translations")
    # Missing/null means an intentionally untranslated line; the Go API and
    # reader normalize it to an empty list. Any other authored shape is invalid.
    if translations is not None and not isinstance(translations, list):
        errors.append(f"{label}: unit {unit.get('id', '?')} canonical_translations must be a list")

    spans = unit.get("word_spans")
    if spans is None:
        return
    if not isinstance(spans, list):
        errors.append(f"{label}: unit {unit.get('id', '?')} word_spans must be a list")
        return
    previous_end = -1
    for span in spans:
        if not isinstance(span, dict):
            errors.append(f"{label}: unit {unit.get('id', '?')} has a non-object word span")
            continue
        start, end = span.get("start"), span.get("end")
        if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or end > len(runes):
            errors.append(f"{label}: unit {unit.get('id', '?')} has invalid word span {start}:{end}")
            continue
        if start < previous_end:
            errors.append(f"{label}: unit {unit.get('id', '?')} has overlapping word spans")
        previous_end = end
        word = span.get("word")
        if isinstance(word, str) and word != "".join(runes[start:end]):
            errors.append(
                f"{label}: unit {unit.get('id', '?')} span {start}:{end} word does not match text"
            )


def validate_chapter(
    path: Path,
    catalog_chapter: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> None:
    document = load_json(path, errors)
    if document is None:
        return
    chapter = document.get("chapter")
    label = path.relative_to(REPO_ROOT)
    if not isinstance(chapter, dict):
        errors.append(f"{label}: missing chapter object")
        return
    if chapter.get("id") != catalog_chapter.get("id"):
        errors.append(f"{label}: chapter id disagrees with catalog")
    if chapter.get("order") != catalog_chapter.get("order"):
        errors.append(f"{label}: chapter order disagrees with catalog")
    units = chapter.get("reading_units")
    if not isinstance(units, list):
        errors.append(f"{label}: reading_units must be a list")
        return
    if chapter.get("reading_unit_count") != len(units):
        errors.append(
            f"{label}: reading_unit_count={chapter.get('reading_unit_count')}; actual={len(units)}"
        )
    catalog_count = catalog_chapter.get("reading_unit_count")
    if isinstance(catalog_count, int) and catalog_count != len(units):
        # Some catalogs retain source-extraction totals that include a removed
        # supplemental unit. The chapter payload is authoritative at runtime,
        # so surface this editorial drift without failing otherwise valid data.
        warnings.append(f"{label}: catalog reading_unit_count={catalog_count}; actual={len(units)}")
    ids: set[str] = set()
    orders: set[int] = set()
    for unit in units:
        validate_unit(path, unit, errors)
        if isinstance(unit, dict):
            unit_id, order = unit.get("id"), unit.get("order")
            if isinstance(unit_id, str):
                if unit_id in ids:
                    errors.append(f"{label}: duplicate unit id {unit_id}")
                ids.add(unit_id)
            if isinstance(order, int):
                if order in orders:
                    errors.append(f"{label}: duplicate unit order {order}")
                orders.add(order)


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    catalogs = sorted(BOOKS_ROOT.glob("*/catalog.json"))
    chapters_checked = 0
    units_checked = 0

    for catalog_path in catalogs:
        catalog = load_json(catalog_path, errors)
        if catalog is None:
            continue
        book_dir = catalog_path.parent
        available = catalog.get("available", True) is not False
        chapters = catalog.get("chapters", [])
        if not isinstance(chapters, list):
            errors.append(f"{catalog_path.relative_to(REPO_ROOT)}: chapters must be a list")
            continue
        chapter_count = catalog.get("chapter_count")
        if available and chapter_count != len(chapters):
            errors.append(
                f"{catalog_path.relative_to(REPO_ROOT)}: chapter_count={chapter_count}; catalog entries={len(chapters)}"
            )
        for chapter in chapters:
            if not isinstance(chapter, dict):
                errors.append(f"{catalog_path.relative_to(REPO_ROOT)}: chapter entry must be an object")
                continue
            raw_path = chapter.get("chapter_path")
            if not isinstance(raw_path, str) or not raw_path:
                chapter_id = chapter.get("id")
                if not isinstance(chapter_id, str) or not chapter_id:
                    errors.append(f"{catalog_path.relative_to(REPO_ROOT)}: chapter entry has no id or chapter_path")
                    continue
                raw_path = f"books/{book_dir.name}/chapters/{chapter_id}.json"
            path = REPO_ROOT / "content" / raw_path
            if not path.is_file():
                errors.append(f"{catalog_path.relative_to(REPO_ROOT)}: missing {raw_path}")
                continue
            document = load_json(path, errors)
            if document and isinstance(document.get("chapter"), dict):
                units = document["chapter"].get("reading_units")
                if isinstance(units, list):
                    units_checked += len(units)
            validate_chapter(path, chapter, errors, warnings)
            chapters_checked += 1

        if available:
            referenced = set()
            for chapter in chapters:
                if not isinstance(chapter, dict):
                    continue
                raw_path = chapter.get("chapter_path")
                if not isinstance(raw_path, str) or not raw_path:
                    chapter_id = chapter.get("id")
                    if not isinstance(chapter_id, str) or not chapter_id:
                        continue
                    raw_path = f"books/{book_dir.name}/chapters/{chapter_id}.json"
                referenced.add(str((REPO_ROOT / "content" / raw_path).resolve()))
            for path in book_dir.glob("chapters/chapter-*.json"):
                if str(path.resolve()) not in referenced:
                    errors.append(f"{path.relative_to(REPO_ROOT)}: chapter file is not referenced by catalog")

    if errors:
        print(f"Content validation failed with {len(errors)} error(s):", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    if warnings:
        print(f"Content validation warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    print(
        f"Content valid: {len(catalogs)} catalogs, {chapters_checked} chapters, "
        f"{units_checked} reading units."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
