#!/usr/bin/env python3
"""Align Brewitt-Taylor's 1925 English translation of Sanguo Yanyi to the
Chinese reading units, writing the result directly into
`canonical_translations[]` on each unit.

SOURCE
  C.H. Brewitt-Taylor, *San Kuo; or Romance of the Three Kingdoms* (Kelly &
  Walsh, Shanghai, 1925). Public domain in the US since 2021-01-01 and in
  life+70 jurisdictions since 2009. Fetched from English Wikisource:
    https://en.wikisource.org/wiki/San_Kuo/Volume_{1|2}/Chapter_{order}
  (volume 1 = chapters 1-60, volume 2 = chapters 61-120).

PORTED FROM
  da-xue/tools/import_line_translations.py (the multi-book importer) and
  da-xue/tools/fix_sanguo_alignment.py (the poem-aware patch). This file is a
  minimal, sanguo-only consolidation: it drops ~800 lines of unrelated
  multi-book parsing but keeps the exact length-DP algorithm and the exact
  poem-detection heuristic, so alignment behavior matches the upstream output.

KEY DIFFERENCE FROM UPSTREAM
  Upstream wrote `generated_annotation.layers.translation_en` (an internal
  scratch field) and relied on `clean_content.py` to promote it. That
  promotion never ran for sanguo (deferred book, `curate=False`), so in
  the-big-learn today 0% of sanguo units serve English. This script bypasses
  that broken path and writes `canonical_translations[]` directly, with full
  Brewitt-Taylor attribution. Poem/closing-formula units — for which
  Brewitt-Taylor has no English at all — get `canonical_translations: []`
  here and are filled separately by `generate_sanguo_poems.py` (labeled
  `source: "llm"`).

DETERMINISM
  Fetched HTML is snapshotted to `tools/raw/sanguo/chapter-NNN.html` on first
  fetch; subsequent runs read from disk. Pass `--refresh` to re-fetch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup


REPO_ROOT = Path(__file__).resolve().parents[1]
BOOKS_ROOT = REPO_ROOT / "content" / "books"
SANGUO_DIR = BOOKS_ROOT / "sanguo-yanyi" / "chapters"
RAW_DIR = Path(__file__).resolve().parent / "raw" / "sanguo"

# Brewitt-Taylor attribution written onto every prose entry. `source` is
# omitted from the JSON (omitempty) so the entry reads as human canon —
# matching how the Five Books' Legge entries are shaped.
HUMAN_TRANSLATION = {
    "translator": "Brewitt-Taylor",
    "year": 1925,
    "license": "public domain",
    "source_url": "https://en.wikisource.org/wiki/Romance_of_the_Three_Kingdoms",
}

WIKIMEDIA_MIN_INTERVAL_SECONDS = 0.5

PUNCT = r"[，。、；：！？\"\"''「」『』（）\s…—\-·]"

# ---------------------------------------------------------------------------
# Normalization + matching helpers (ported verbatim from import_line_translations)
# ---------------------------------------------------------------------------


def clean_ws(text: str) -> str:
    return " ".join(text.split())


def clean_translation_text(text: str) -> str:
    text = re.sub(r"\[p\.\s*\d+\]\s*", "", text)
    text = re.sub(r"\[\s*\d+\s*\]", "", text)
    text = re.sub(r"Source:.*", "", text)
    text = re.sub(r"Dictionary cache status:.*", "", text)
    return clean_ws(text)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (compatible; the-big-learn-sanguo-aligner/1.0)"
    return session


def rate_limited_get(
    session: requests.Session,
    url: str,
    *,
    timeout: int = 30,
    interval_seconds: float = 0.0,
    state_attr: str | None = None,
    max_attempts: int = 5,
) -> requests.Response:
    response = requests.Response()
    for _ in range(max_attempts):
        if state_attr:
            last_request_at = getattr(session, state_attr, 0.0)
            wait_for = interval_seconds - (time.time() - last_request_at)
            if wait_for > 0:
                time.sleep(wait_for)

        response = session.get(url, timeout=timeout)
        if state_attr:
            setattr(session, state_attr, time.time())
        if response.status_code != 429:
            return response

        retry_after = response.headers.get("retry-after")
        delay = float(retry_after) if retry_after else min(30.0, 2.0)
        time.sleep(delay)

    return response


# ---------------------------------------------------------------------------
# Brewitt-Taylor fetcher (ported verbatim, plus snapshot caching)
# ---------------------------------------------------------------------------


def fetch_sanguo_html(session: requests.Session, order: int, *, refresh: bool) -> str:
    """Return the Wikisource HTML for chapter `order`. Snapshot to RAW_DIR
    on first fetch; read from disk thereafter unless `refresh`."""
    snapshot = RAW_DIR / f"chapter-{order:03d}.html"
    if snapshot.exists() and not refresh:
        return snapshot.read_text(encoding="utf-8")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    volume = 1 if order <= 60 else 2
    url = f"https://en.wikisource.org/wiki/San_Kuo/Volume_{volume}/Chapter_{order}"
    response = rate_limited_get(
        session,
        url,
        timeout=30,
        interval_seconds=WIKIMEDIA_MIN_INTERVAL_SECONDS,
        state_attr="_wikimedia_last_request_at",
    )
    if response.status_code == 429:
        raise ValueError(f"rate limited fetching San Kuo chapter {order}")
    response.raise_for_status()
    response.encoding = "utf-8"
    snapshot.write_text(response.text, encoding="utf-8")
    return response.text


def parse_sanguo_english_paragraphs(html: str, order: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find(id="mw-content-text")
    if main is None:
        raise ValueError(f"missing mw-content-text for San Kuo chapter {order}")

    paragraphs: list[str] = []
    for paragraph in main.find_all("p"):
        text = clean_ws(paragraph.get_text(" ", strip=True))
        if not text:
            continue
        if re.fullmatch(r"CHAPTER\s+[IVXLCDM]+\.?", text):
            continue
        if text.startswith("Footnotes") or text.startswith("Notes") or text.startswith("References"):
            break
        if re.match(r"^\d+\.\s", text):
            break
        paragraphs.append(text)

    # Drop the leading chapter subtitle only (e.g. "Feast in the Garden of
    # Peaches: Brotherhood Sworn: …"). The next paragraph is the opening
    # narrative — the translation of the first prose unit — and must be kept.
    # (Previously this dropped paragraphs[:2], which discarded the opening
    # narrative and shifted every alignment by one paragraph for the chapter.)
    if len(paragraphs) >= 1:
        paragraphs = paragraphs[1:]

    cleaned: list[str] = []
    for paragraph in paragraphs:
        # Repair "A bbreviation"- / "I t"-style line wraps from the scan
        # (a single capital letter left stranded before the real first word).
        paragraph = re.sub(r"^([A-Z])\s+([a-z]+)", r"\1\2", paragraph)
        cleaned.append(clean_translation_text(paragraph))

    # Strip trailing non-content paragraphs (publisher info, "The End", etc.).
    while cleaned:
        last = cleaned[-1].strip()
        if not last:
            cleaned.pop()
            continue
        lower = last.lower()
        if lower == "the end" or lower.startswith("printed by"):
            cleaned.pop()
            continue
        if re.fullmatch(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\.?", last):
            cleaned.pop()
            continue
        break

    return [paragraph for paragraph in cleaned if paragraph]


# ---------------------------------------------------------------------------
# Length-DP aligner (ported verbatim from import_line_translations)
# ---------------------------------------------------------------------------


def split_translation(text: str, parts: int) -> list[str]:
    text = clean_ws(text)
    if parts <= 1:
        return [text]

    separators = [
        re.compile(r'(?<=[.?!])\s+(?=["\'(A-Z])'),
        re.compile(r"(?<=;)\s+|(?<=:)\s+"),
        re.compile(r"(?<=,)\s+"),
    ]

    segments = [text]
    for separator in separators:
        candidate: list[str] = []
        for segment in segments:
            candidate.extend(part.strip() for part in separator.split(segment) if part.strip())
        segments = candidate
        if len(segments) >= parts:
            break

    if len(segments) == parts:
        return segments
    if len(segments) > parts:
        return segments[: parts - 1] + [" ".join(segments[parts - 1 :])]

    return [text] * parts


def assign_english_paragraphs_by_length(
    units: list[dict],
    paragraphs: list[str],
    *,
    max_group_span: int = 6,
) -> dict[str, str]:
    """Dynamic-programming alignment of EN paragraphs onto zh reading units.

    Cost is a squared-deviation of word-count from a char-count-scaled target,
    with penalties for stuffing multiple paragraphs onto short units (which
    would otherwise happen for poem-line-shaped units — exactly the failure
    mode the prose-only pre-filter in `reassign_chapter` exists to prevent).
    """
    if not units or not paragraphs:
        return {}

    if len(paragraphs) < len(units):
        merged = " ".join(paragraphs)
        return {
            unit["id"]: piece
            for unit, piece in zip(units, split_translation(merged, len(units)))
        }

    zh_lengths = [
        max(1, len(re.sub(r"[^\u3400-\u9fff\U00020000-\U0002ebef]", "", unit["text"])))
        for unit in units
    ]
    en_lengths = [
        max(1, len(re.findall(r"[A-Za-z']+", paragraph)))
        for paragraph in paragraphs
    ]
    scale = sum(en_lengths) / max(1, sum(zh_lengths))
    prefix_sums = [0]
    for length in en_lengths:
        prefix_sums.append(prefix_sums[-1] + length)

    def segment_words(start: int, end: int) -> int:
        return prefix_sums[end] - prefix_sums[start]

    unit_count = len(units)
    paragraph_count = len(paragraphs)
    infinity = float("inf")
    dp = [[infinity] * (paragraph_count + 1) for _ in range(unit_count + 1)]
    previous: list[list[int | None]] = [
        [None] * (paragraph_count + 1) for _ in range(unit_count + 1)
    ]
    dp[0][0] = 0.0

    for unit_index in range(1, unit_count + 1):
        max_paragraph_index = paragraph_count - (unit_count - unit_index)
        for paragraph_index in range(unit_index, max_paragraph_index + 1):
            for group_span in range(1, max_group_span + 1):
                start_index = paragraph_index - group_span
                if start_index < unit_index - 1:
                    break

                words = segment_words(start_index, paragraph_index)
                target = max(8.0, zh_lengths[unit_index - 1] * scale)
                cost = ((words - target) ** 2) / target
                if group_span > 1 and zh_lengths[unit_index - 1] < 12:
                    cost += 20.0 * (group_span - 1)
                if group_span > 2 and zh_lengths[unit_index - 1] < 20:
                    cost += 10.0 * (group_span - 2)

                candidate = dp[unit_index - 1][start_index] + cost
                if candidate < dp[unit_index][paragraph_index]:
                    dp[unit_index][paragraph_index] = candidate
                    previous[unit_index][paragraph_index] = start_index

    assignments: dict[str, str] = {}
    paragraph_index = paragraph_count
    groups: list[tuple[int, int]] = []
    for unit_index in range(unit_count, 0, -1):
        start_index = previous[unit_index][paragraph_index]
        if start_index is None:
            merged = " ".join(paragraphs)
            return {
                unit["id"]: piece
                for unit, piece in zip(units, split_translation(merged, len(units)))
            }
        groups.append((start_index, paragraph_index))
        paragraph_index = start_index

    groups.reverse()
    for unit, (start_index, end_index) in zip(units, groups):
        assignments[unit["id"]] = clean_translation_text(
            " ".join(paragraphs[start_index:end_index])
        )

    return assignments


# ---------------------------------------------------------------------------
# Poem detection (ported verbatim from fix_sanguo_alignment.py)
# ---------------------------------------------------------------------------


def is_list_item(text: str) -> bool:
    """Numbered warlord/general roster line like 第X镇 — must NOT be flagged
    as a poem despite being short, or the length-DP loses its prose anchors."""
    return bool(re.match(r"第[一二三四五六七八九十百千]+[镇路]", text))


def identify_poem_units(units: list[dict]) -> set[int]:
    """Find poem / closing-formula unit indices.

    Rule: a run of 2+ consecutive short lines (clean len <= 22 chars, after
    stripping punctuation) is a poem block; an *isolated* short line is prose
    UNLESS it matches a 毕竟/未知/不知/欲知 … 且听 closing formula. List items
    break blocks and are never poems.
    """
    poem_indices: set[int] = set()
    i = 0
    while i < len(units):
        text = units[i]["text"]
        clean_len = len(re.sub(PUNCT, "", text))

        if is_list_item(text):
            i += 1
            continue

        if clean_len <= 22:
            block_start = i
            while i < len(units):
                t = units[i]["text"]
                if is_list_item(t):
                    break
                cl = len(re.sub(PUNCT, "", t))
                if cl <= 22:
                    i += 1
                else:
                    break
            block_end = i
            block_size = block_end - block_start

            if block_size >= 2:
                for j in range(block_start, block_end):
                    poem_indices.add(j)
            else:
                line = units[block_start]["text"]
                for pat in (r"毕竟.*且听", r"未知.*且听", r"不知.*且听", r"欲知.*且听"):
                    if re.search(pat, line):
                        poem_indices.add(block_start)
                        break
        else:
            i += 1

    return poem_indices


# ---------------------------------------------------------------------------
# Apply: write canonical_translations[] directly
# ---------------------------------------------------------------------------


def list_chapter_paths(start: int, end: int) -> list[Path]:
    return [
        SANGUO_DIR / f"chapter-{order:03d}.json"
        for order in range(start, end + 1)
        if (SANGUO_DIR / f"chapter-{order:03d}.json").exists()
    ]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def reading_units(document: dict) -> list[dict]:
    return document["chapter"]["reading_units"]


def make_human_entry(text: str) -> dict:
    entry = dict(HUMAN_TRANSLATION)
    entry["text"] = text
    return entry


def reassign_chapter(session: requests.Session, path: Path, *, refresh: bool) -> dict:
    """Align one chapter. Returns a stats dict; mutates + writes the file in
    place only when translations actually change."""
    document = read_json(path)
    chapter = document["chapter"]
    order = chapter["order"]
    units = reading_units(document)

    stats = {"order": order, "units": len(units), "poems": 0, "prose_filled": 0, "changed": 0}
    if not units:
        return stats

    html = fetch_sanguo_html(session, order, refresh=refresh)
    english_paragraphs = parse_sanguo_english_paragraphs(html, order)
    if not english_paragraphs:
        print(f"  Ch{order}: no English text available")
        return stats

    poem_indices = identify_poem_units(units)
    prose_units = [u for i, u in enumerate(units) if i not in poem_indices]
    stats["poems"] = len(poem_indices)

    print(
        f"  Ch{order}: {len(units)} units, "
        f"{len(poem_indices)} poems, "
        f"{len(prose_units)} prose, "
        f"{len(english_paragraphs)} EN paragraphs"
    )

    prose_assignments = (
        assign_english_paragraphs_by_length(prose_units, english_paragraphs)
        if prose_units
        else {}
    )

    changed = 0
    for i, unit in enumerate(units):
        if i in poem_indices:
            # Brewitt-Taylor has no English for verse — leave empty for the
            # labeled LLM pass (generate_sanguo_poems.py).
            if unit.get("canonical_translations"):
                unit["canonical_translations"] = []
                changed += 1
            continue

        new_text = clean_ws(prose_assignments.get(unit["id"], ""))
        if not new_text:
            continue

        new_entry = make_human_entry(new_text)
        # Idempotent: skip the write if the entry is already exactly this.
        if unit.get("canonical_translations") != [new_entry]:
            unit["canonical_translations"] = [new_entry]
            changed += 1
            stats["prose_filled"] += 1

    stats["changed"] = changed
    if changed:
        write_json(path, document)

    return stats


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1, help="First chapter")
    parser.add_argument("--end", type=int, default=120, help="Last chapter")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Re-fetch Brewitt-Taylor HTML from Wikisource instead of using the snapshot",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    session = build_session()
    paths = list_chapter_paths(args.start, args.end)
    if not paths:
        print(f"No chapters found in {SANGUO_DIR}", file=sys.stderr)
        return 1

    totals = {"units": 0, "poems": 0, "prose_filled": 0, "changed": 0, "chapters_touched": 0}
    for path in paths:
        print(f"Ch{path.stem.split('-')[1]}...", end="", flush=True)
        try:
            stats = reassign_chapter(session, path, refresh=args.refresh)
        except Exception as exc:
            print(f" error: {exc}")
            continue
        for k in ("units", "poems", "prose_filled", "changed"):
            totals[k] += stats[k]
        if stats["changed"]:
            totals["chapters_touched"] += 1
        print(f" {stats['changed']} updated")

    print(
        f"\nTotal: {totals['changed']} units updated across "
        f"{totals['chapters_touched']} chapters "
        f"({totals['units']} units total, {totals['poems']} poems detected)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
