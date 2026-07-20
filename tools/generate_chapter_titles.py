#!/usr/bin/env python3
"""Generate English chapter-title translations for the chapter list.

WHY THIS EXISTS
  Chapter-list rows now render the Chinese title with pinyin ruby (see
  ChapterList.tsx) and have an English slot wired via `title_en` in
  CatalogChapter. No English chapter titles existed in any catalog. This script
  fills them.

TWO KINDS OF TITLES
  Mechanical (no API — handled by rule, tagged title_en_source: "human"):
    - daodejing's 81 `第N章`        -> "Chapter N"
    - the 4 `全篇` single-chapter books -> "Complete Text"
  Generated via GLM (tagged title_en_source: "llm"):
    - lunyu, mengzi, sunzi-bingfa, shi-jing, chengyu-catalog

WHY IT IS LABELED
  Mirrors the project's established `source` discriminant on CanonicalTranslation
  ("human" vs "llm") so machine-generated titles are recorded honestly in the
  data, never laundered as authoritative. The chapter-list row itself carries
  no badge (a short label isn't canon text); the field is for audit/provenance.

ALREADY-AUTHORED BOOKS (source: "human", not produced by this script)
  lunyu, mengzi, shi-jing chapter titles were hand-authored from James Legge
  (d.1897, public domain); sunzi-bingfa from Lionel Giles (d.1912, public
  domain); chengyu-catalog translated literally. Those values live in the
  catalog files themselves. This script's GLM path remains for any future book
  whose titles have no established English tradition.

DEFERRED
  zhong-yong: 33 empty Chinese titles — needs Chinese authoring first.
  sanguo-yanyi: 120 literary couplets — separate pass.

ENV
  GLM_API_KEY     required for the GLM path (absent => use --dry-run)
  GLM_BASE_URL    optional override
  GLM_MODEL       optional override (default glm-5-turbo)

USAGE
  python3 tools/generate_chapter_titles.py --dry-run     # plan only, no API
  python3 tools/generate_chapter_titles.py               # run for real
  python3 tools/generate_chapter_titles.py --only lunyu  # one book
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BOOKS_DIR = REPO_ROOT / "content" / "books"

DEFAULT_MODEL = "glm-5-turbo"
DEFAULT_BASE_URL = "https://api.z.ai/api/anthropic"

# Books whose titles need a GLM translation. The mechanical-rule books
# (daodejing, bai-jia-xing, da-xue, qian-zi-wen, san-zi-jing) are handled by
# apply_mechanical() and never hit this list. zhong-yong + sanguo-yanyi are
# deferred (see module docstring).
GLM_BOOKS = ["lunyu", "mengzi", "sunzi-bingfa", "shi-jing", "chengyu-catalog"]

# Per-book hints so GLM uses established English names where a tradition
# exists, and a clear style where none does. Sent in the prompt header.
BOOK_HINT = {
    "lunyu": "Lunyu 论语 (Analects). Each chapter is a traditional Book (篇) with a 2-char topical name + ordinal (第N). Use the established Legge English book names where they are well known (e.g. Book I 'On Learning', Book II 'On Government'); otherwise give a concise literal label of the topic.",
    "mengzi": "Mengzi 孟子 (Mencius). Each chapter is a half (上/下) of a named section (章句). Use Legge's section names (e.g. 'King Hui of Liang', 'Gongsun Chou'); append 'Part 1' / 'Part 2' for 上/下.",
    "sunzi-bingfa": "Sunzi Bingfa 孙子兵法 (Art of War). The 13 chapters have well-known canonical English names (e.g. ch1 'Laying Plans' / 'Assessment', ch3 'Attack by Stratagem'). Use the established Giles-style names.",
    "shi-jing": "Shi Jing 诗经 (Book of Songs). Each chapter is a section (国风·周南 = 'Airs of the States · Zhou Nan'). Use Legge's section naming; keep the '·' as ' · ' between the two parts.",
    "chengyu-catalog": "Chengyu Catalog 成语目录. These are modern curated thematic category labels, not source-text headings. Translate literally and concisely (e.g. 'Beginner · Learning & Accumulation').",
}

PROMPT_TEMPLATE = """You are producing concise English labels for the chapter titles of a classical Chinese text, for display in a reader's chapter list.

Book: {book_hint}

For each numbered title below, produce ONE English chapter label. Constraints:
- Use the established English chapter name from the relevant translation tradition (Legge for Confucian classics, Giles for Sunzi) where one exists and is well known; otherwise translate literally.
- Keep it short — a chapter-list label, not a sentence. No trailing period, no quotation marks.
- Each numbered input maps to one numbered output.
- Return ONLY a JSON object mapping the input number to its English label, e.g. {{"1": "On Learning", "2": "On Government"}}. No commentary, no markdown fences.

{entries}
"""


# ---------------------------------------------------------------------------
# catalog IO (key-order-preserving)
# ---------------------------------------------------------------------------


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    # indent=2 matches every catalog.json on disk; ensure_ascii=False keeps
    # CJK inline. We mutate the loaded dict in place, so key order is preserved.
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# mechanical rules
# ---------------------------------------------------------------------------

NUMERIC_RE = re.compile(r"^第\s*(\d+)\s*章$")


def apply_mechanical(title: str) -> str | None:
    """Return a rule-derived English title, or None if no rule matches."""
    m = NUMERIC_RE.match(title.strip())
    if m:
        return f"Chapter {int(m.group(1))}"
    if title.strip() == "全篇":
        return "Complete Text"
    return None


# ---------------------------------------------------------------------------
# GLM client (urllib — matches generate_sanguo_poems.py precedent)
# ---------------------------------------------------------------------------


def glm_chat(messages: list[dict], *, model: str, max_tokens: int) -> str:
    """Call the GLM endpoint (Anthropic Messages API shape)."""
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        raise ValueError("GLM_API_KEY is not set")
    base_url = os.environ.get("GLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    payload = json.dumps(
        {"model": model, "max_tokens": max_tokens, "messages": messages}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GLM HTTP {exc.code}: {detail}") from exc

    try:
        blocks = body["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        if not text:
            raise RuntimeError(f"empty content blocks: {body!r:.500}")
        return text.strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"unexpected GLM response shape: {body!r:.500}") from exc


def extract_json_object(text: str) -> dict | None:
    """Pull a JSON object out of an LLM response, tolerating fences/prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# per-book generation
# ---------------------------------------------------------------------------


def make_prompt(slug: str, chapters: list[dict]) -> str:
    lines = [
        f"[{c['order']}] {c['title']}" for c in chapters if c.get("title", "").strip()
    ]
    return PROMPT_TEMPLATE.format(
        book_hint=BOOK_HINT.get(slug, slug),
        entries="\n".join(lines),
    )


def process_book(
    slug: str, *, model: str, dry_run: bool
) -> dict:
    """Fill title_en (and title_en_source) for one book's catalog chapters."""
    path = BOOKS_DIR / slug / "catalog.json"
    if not path.exists():
        print(f"  {slug}: catalog not found, skipping")
        return {"mechanical": 0, "llm": 0, "skipped": 0}
    doc = read_json(path)
    chapters = doc.get("chapters", [])
    stats = {"mechanical": 0, "llm": 0, "skipped": 0}

    needs_glm: list[dict] = []
    for c in chapters:
        title = (c.get("title") or "").strip()
        if not title:
            stats["skipped"] += 1
            continue
        # Respect an existing hand-authored title_en — never clobber human work.
        # We still backfill title_en_source so provenance is recorded.
        existing = (c.get("title_en") or "").strip()
        mech = apply_mechanical(title)
        if mech is not None:
            # Mechanical-rule chapter (第N章 / 全篇). Fill the English if absent;
            # otherwise keep the existing value (e.g. a curated "The Complete Text").
            if not existing:
                c["title_en"] = mech
            c["title_en_source"] = "human"
            stats["mechanical"] += 1
        elif existing:
            # Non-mechanical title that already has a hand-authored English
            # (rare today). Record provenance as human and don't send to GLM.
            c["title_en_source"] = "human"
        else:
            needs_glm.append(c)

    if needs_glm and slug in GLM_BOOKS:
        prompt = make_prompt(slug, needs_glm)
        if dry_run:
            print(f"  {slug}: {len(needs_glm)} titles -> GLM (dry-run)")
            print(f"    prompt excerpt: {prompt[:200]}...")
        else:
            try:
                resp = glm_chat(
                    [{"role": "user", "content": prompt}],
                    model=model,
                    max_tokens=2048,
                )
                parsed = extract_json_object(resp)
            except Exception as exc:
                print(f"  {slug}: GLM error: {exc}")
                parsed = None

            if isinstance(parsed, dict):
                for c in needs_glm:
                    val = parsed.get(str(c["order"])) or parsed.get(c["order"])
                    if isinstance(val, str) and val.strip():
                        c["title_en"] = val.strip()
                        c["title_en_source"] = "llm"
                        stats["llm"] += 1
                    else:
                        print(
                            f"  {slug} ch{c['order']}: no translation returned, leaving title_en unset"
                        )
            else:
                print(f"  {slug}: failed to parse GLM response; no GLM titles written")
    elif needs_glm:
        # Book not in GLM_BOOKS and no mechanical rule — leave for separate work
        # (e.g. sanguo-yanyi). Don't error; just report.
        print(f"  {slug}: {len(needs_glm)} titles need translation but book not in GLM_BOOKS — deferred")

    # Write back if we set anything new. We always write in dry-run's absence
    # only when something actually changed (mechanical or GLM). For dry-run we
    # never write.
    if not dry_run and (stats["mechanical"] or stats["llm"]):
        write_json(path, doc)
    return stats


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only",
        action="append",
        help="Limit to specific book slug (repeatable). Default: all available books.",
    )
    parser.add_argument("--model", default=os.environ.get("GLM_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Apply mechanical rules and print the GLM plan without calling GLM or writing files.",
    )
    args = parser.parse_args(argv)

    if not args.dry_run and not os.environ.get("GLM_API_KEY"):
        print(
            "GLM_API_KEY is not set. Use --dry-run to plan without calling GLM.",
            file=sys.stderr,
        )
        return 2

    # Determine the book set: every available book, so the mechanical rules
    # apply uniformly (daodejing + the 全篇 books). GLM only fires for GLM_BOOKS.
    slugs = []
    for entry in sorted(BOOKS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        cat = entry / "catalog.json"
        if not cat.exists():
            continue
        doc = read_json(cat)
        if not doc.get("available", True):
            continue
        if args.only and entry.name not in args.only:
            continue
        slugs.append(entry.name)

    if not slugs:
        print("No books to process.", file=sys.stderr)
        return 1

    print(f"Processing {len(slugs)} book(s){' (dry-run)' if args.dry_run else ''}:")
    totals = {"mechanical": 0, "llm": 0, "skipped": 0}
    for slug in slugs:
        stats = process_book(slug, model=args.model, dry_run=args.dry_run)
        for k in totals:
            totals[k] += stats[k]
        if not args.dry_run:
            time.sleep(1)  # gentle on the API between books

    print(
        f"\nTotal: {totals['mechanical']} mechanical, "
        f"{totals['llm']} GLM-generated, {totals['skipped']} skipped (empty title)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
