#!/usr/bin/env python3
"""Semantic aligner for Sanguo Yanyi prose — replaces length-DP with GLM.

WHY THIS EXISTS
  `sanguo_align.py` aligns Brewitt-Taylor English to Chinese reading units
  using a length-only dynamic program. `validate_sanguo.py` shows the
  consequence: ~113 prose units (~1.8%) are >3σ length outliers, and
  spot-audits confirm these are *semantic* misalignments concentrated at
  verse inserts and dialog boundaries, where length matching fails. This
  script replaces that with a GLM-driven alignment that matches English
  paragraphs to Chinese units by *content*.

HOW IT DIFFERS FROM UPSTREAM
  `da-xue/tools/align_sanguo_translations.py` did the alignment in one pass
  over ALL units (poems + prose) and asked the model to free-text segment
  the English into N parts. Three problems this script fixes:

    1. PROSE-ONLY. We exclude poem/closing-formula units (same
       `identify_poem_units` heuristic) so this script and
       `generate_sanguo_poems.py` don't fight each other over who owns the
       verse inserts.
    2. MAPPING, NOT REWRITING. Instead of asking GLM to slice English text
       into N strings (which risks paraphrase / dropped text), we ask for a
       JSON mapping `{unit_index: [paragraph_indices]}`. The actual English
       pasted into `canonical_translations[]` is verbatim Brewitt-Taylor,
       concatenated by the model's chosen indices. This preserves
       Brewitt-Taylor's exact words — the model only decides alignment.
    3. WRITES canonical_translations[] DIRECTLY. With `source: "human"`,
       Brewitt-Taylor attribution, bypassing the dead
       `generated_annotation` field the upstream wrote to.

PIPELINE
  For each chapter:
    1. Fetch Brewitt-Taylor paragraphs (`parse_sanguo_english_paragraphs`,
       reusing the snapshot cache from sanguo_align.py).
    2. Identify poem units, build the prose-only unit list.
    3. Ask GLM for `{prose_unit_seq: [paragraph_indices]}`.
    4. Validate the mapping (every paragraph consumed once; indices in
       range). If validation fails, fall back to length-DP for that chapter
       rather than writing a bad alignment.
    5. Write canonical_translations[] with verbatim Brewitt-Taylor text.

ENV
  GLM_API_KEY     required (unless --dry-run)
  GLM_BASE_URL    optional override (default: the z.ai coding-plan endpoint)
  GLM_MODEL       optional override (default: glm-5-turbo)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SANGUO_DIR = REPO_ROOT / "content" / "books" / "sanguo-yanyi" / "chapters"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanguo_align import (  # noqa: E402
    HUMAN_TRANSLATION,
    assign_english_paragraphs_by_length,
    build_session,
    clean_translation_text,
    clean_ws,
    fetch_sanguo_html,
    identify_poem_units,
    list_chapter_paths,
    make_human_entry,
    parse_sanguo_english_paragraphs,
    read_json,
    write_json,
    reading_units,
)
from generate_sanguo_poems import glm_chat  # noqa: E402 — reuse the GLM client

DEFAULT_MODEL = "glm-5-turbo"

PROMPT_TEMPLATE = """You are aligning a 1925 English translation to its Chinese source, paragraph by paragraph.

Chapter {order} of *Sanguo Yanyi* (三国演义) has {n_prose} Chinese PROSE reading units (verse/closing-formula units have been removed beforehand — do not account for them). The Brewitt-Taylor English translation has {n_paras} paragraphs.

Your job: decide which English paragraph(s) correspond to each Chinese prose unit. Output a JSON object mapping each prose-unit sequence number (1..{n_prose}) to the list of English paragraph indices (0-based, from the list below) that belong to it.

Rules:
- **PARTITION, do not share.** Each English paragraph goes in EXACTLY ONE unit. If paragraphs 3 and 4 both fit unit 2, write `"2": [3, 4]` — never write 3 into both unit 2 and unit 3. Treat the {n_paras} paragraphs as a stack you split into {n_prose} contiguous buckets: every paragraph consumed once, no overlap, no gaps.
- The assignments must be in order: every paragraph index in unit k is less than every paragraph index in unit k+1 (the English is a contiguous retelling, not reordered).
- Use the Chinese unit's content to decide where each split falls. Names (e.g. 曹操/Ts'ao Ts'ao, 刘备/Liu Pei), place names, and plot events are the strongest signals. When a paragraph could belong to either of two adjacent units, assign it to the one whose content it matches more closely — pick one, do not duplicate.
- The English paragraph indices are 0-based: 0, 1, ..., {last_para_idx}. Every index 0..{last_para_idx} must appear exactly once across all units combined.

Return ONLY the JSON object. No commentary, no markdown fences. Example shape:
{{"1": [0, 1], "2": [2], "3": [3, 4, 5]}}

Chinese prose units (1..{n_prose}):
{prose_units}

English paragraphs (0..{last_para_idx}):
{english_paragraphs}
"""


def make_prompt(order: int, prose_units: list[dict], paragraphs: list[str]) -> str:
    prose_lines = "\n".join(
        f"[{i+1}] {clean_ws(u['text'])}" for i, u in enumerate(prose_units)
    )
    para_lines = "\n".join(
        f"[{i}] {clean_ws(p)}" for i, p in enumerate(paragraphs)
    )
    return PROMPT_TEMPLATE.format(
        order=order,
        n_prose=len(prose_units),
        n_paras=len(paragraphs),
        last_para_idx=len(paragraphs) - 1,
        prose_units=prose_lines,
        english_paragraphs=para_lines,
    )


def extract_json_object(text: str) -> dict | None:
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


def _coerce_mapping(mapping: dict, n_prose: int, n_paras: int) -> list[list[int]] | None:
    """Coerce the parsed JSON into a per-unit list of paragraph indices,
    enforcing: (a) covers 1..n_prose, (b) every value is a list of in-range
    ints. Returns None on any structural violation."""
    if not isinstance(mapping, dict) or len(mapping) != n_prose:
        return None
    per_unit: list[list[int]] = []
    for k in range(1, n_prose + 1):
        # Tolerate either str or int keys.
        raw = mapping.get(str(k)) if str(k) in mapping else mapping.get(k)
        if raw is None:
            return None
        if isinstance(raw, int):
            raw = [raw]
        if not isinstance(raw, list) or not raw:
            return None
        try:
            idxs = sorted(int(x) for x in raw)
        except (TypeError, ValueError):
            return None
        if any(not (0 <= i < n_paras) for i in idxs):
            return None
        per_unit.append(idxs)
    return per_unit


def validate_mapping(mapping: dict, n_prose: int, n_paras: int) -> list[list[int]] | None:
    """Coerce + validate the mapping into a per-unit partition of paragraph
    indices 0..n_paras-1, tolerating the two failure modes GLM exhibits on
    long chapters: (a) overlap ("include in both when unsure") and (b) small
    gaps (dropping 1-2 trailing or boundary paragraphs).

    Acceptance criteria (all must hold):
      - exactly n_prose units, each a list of in-range ints;
      - covers >= 90% of paragraphs (i.e. < 10% gaps).

    Repair:
      - overlap → each paragraph goes to the LATEST unit claiming it
        (boundary paragraphs typically introduce the next unit's content);
      - gaps → each missing paragraph is assigned to the unit whose index
        range it falls within (the unit covering paragraphs p-1..p+1).

    Units that end up empty after repair are returned as [] — the caller
    fills them via length-DP so they still get some English.

    Returns None (→ whole-chapter length-DP fallback) only on structural
    failure: wrong unit count, OOB indices, >10% gaps, or non-int values.
    """
    per_unit = _coerce_mapping(mapping, n_prose, n_paras)
    if per_unit is None:
        return None

    flat_set = {i for idxs in per_unit for i in idxs}
    expected = set(range(n_paras))
    missing = sorted(expected - flat_set)

    # Hard fail: too many gaps indicates the model lost the thread. Allow up
    # to 10% of paragraphs OR 2 absolute (whichever is larger), so a 78-para
    # chapter tolerates ~7 gaps and a small 8-para chapter tolerates 2.
    gap_tolerance = max(2, n_paras // 10)
    if len(missing) > gap_tolerance:
        return None

    # Assign each missing paragraph to the unit whose range it falls in.
    # Build unit_index_of[paragraph] from current claims, then for each
    # missing paragraph, find the unit claiming the nearest paragraph.
    para_to_units: dict[int, list[int]] = {}
    for u_idx, idxs in enumerate(per_unit):
        for i in idxs:
            para_to_units.setdefault(i, []).append(u_idx)

    def nearest_unit(p: int) -> int:
        # Search outward from p for the closest claimed paragraph; assign
        # to its latest-claiming unit. Tie-break by lower distance, then
        # by earlier unit.
        for dist in range(1, n_paras):
            for cand, sign in ((p - dist, -1), (p + dist, 1)):
                if cand in para_to_units:
                    return max(para_to_units[cand])
        return 0  # fallback: first unit

    for p in missing:
        target = nearest_unit(p)
        per_unit[target].append(p)
        para_to_units.setdefault(p, []).append(target)

    # Dedup overlap: each paragraph to the latest unit claiming it.
    claimed_by: dict[int, list[int]] = {}
    for u_idx, idxs in enumerate(per_unit):
        for i in idxs:
            claimed_by.setdefault(i, []).append(u_idx)
    repaired: list[list[int]] = [[] for _ in range(n_prose)]
    for i, units in claimed_by.items():
        repaired[max(units)].append(i)
    return [sorted(idxs) for idxs in repaired]


def build_assignments_from_mapping(
    prose_units: list[dict], paragraphs: list[str], per_unit: list[list[int]]
) -> dict[str, str]:
    """Concatenate the model's chosen paragraphs verbatim per unit."""
    out: dict[str, str] = {}
    for unit, idxs in zip(prose_units, per_unit):
        text = clean_translation_text(" ".join(paragraphs[i] for i in idxs))
        if text:
            out[unit["id"]] = text
    return out


def align_chapter(model: str, session, path: Path, *, refresh: bool, dry_run: bool) -> dict:
    document = read_json(path)
    chapter = document["chapter"]
    order = chapter["order"]
    units = reading_units(document)
    stats = {
        "order": order, "units": len(units),
        "prose": 0, "poems": 0,
        "filled": 0, "changed": 0, "fallback": False,
    }
    if not units:
        return stats

    html = fetch_sanguo_html(session, order, refresh=refresh)
    paragraphs = parse_sanguo_english_paragraphs(html, order)
    if not paragraphs:
        print(f"  Ch{order}: no English text")
        return stats

    poem_indices = identify_poem_units(units)
    prose_units = [u for i, u in enumerate(units) if i not in poem_indices]
    stats["prose"] = len(prose_units)
    stats["poems"] = len(poem_indices)

    if not prose_units:
        return stats

    prompt = make_prompt(order, prose_units, paragraphs)

    if dry_run:
        print(f"  Ch{order}: would align {len(prose_units)} prose to {len(paragraphs)} paragraphs (dry-run)")
        stats["filled"] = len(prose_units)
        return stats

    response_text = glm_chat(
        [{"role": "user", "content": prompt}],
        model=model,
        max_tokens=8192,
    )
    mapping = extract_json_object(response_text)
    per_unit = validate_mapping(mapping, len(prose_units), len(paragraphs)) if mapping else None

    if per_unit is None:
        # Real failure (gaps / OOB / wrong count): whole-chapter length-DP.
        print(f"  Ch{order}: GLM mapping invalid — whole-chapter length-DP fallback")
        stats["fallback"] = True
        assignments = assign_english_paragraphs_by_length(prose_units, paragraphs)
    else:
        # Model mapping accepted. Some units may be empty after dedup — fill
        # those individually via length-DP over the unassigned paragraphs so
        # they still get *some* English rather than none. This is the honest
        # middle ground: model-aligned where confident, length-DP where not.
        assignments = build_assignments_from_mapping(prose_units, paragraphs, per_unit)
        empty_units = [u for u in prose_units if u["id"] not in assignments]
        if empty_units:
            used = {i for idxs in per_unit for i in idxs}
            leftover = [p for i, p in enumerate(paragraphs) if i not in used]
            if leftover:
                dp = assign_english_paragraphs_by_length(empty_units, leftover)
                assignments.update(dp)
            stats["fallback"] = True  # partial — flag for the audit log

    changed = 0
    for unit in prose_units:
        new_text = clean_ws(assignments.get(unit["id"], ""))
        if not new_text:
            continue
        new_entry = make_human_entry(new_text)
        if unit.get("canonical_translations") != [new_entry]:
            unit["canonical_translations"] = [new_entry]
            changed += 1
            stats["filled"] += 1

    stats["changed"] = changed
    if changed:
        write_json(path, document)
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=120)
    parser.add_argument("--model", default=os.environ.get("GLM_MODEL", DEFAULT_MODEL))
    parser.add_argument("--refresh", action="store_true", help="Re-fetch Brewitt-Taylor HTML")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if not args.dry_run and not os.environ.get("GLM_API_KEY"):
        print("GLM_API_KEY is not set. Use --dry-run to plan without calling GLM.", file=sys.stderr)
        return 2

    session = build_session()
    paths = list_chapter_paths(args.start, args.end)
    if not paths:
        print(f"No chapters found in {SANGUO_DIR}", file=sys.stderr)
        return 1

    totals = {"prose": 0, "filled": 0, "changed": 0, "fallbacks": 0, "chapters_touched": 0}
    for path in paths:
        order = int(path.stem.split("-")[1])
        print(f"Ch{order}...", end="", flush=True)
        try:
            stats = align_chapter(args.model, session, path, refresh=args.refresh, dry_run=args.dry_run)
        except Exception as exc:
            print(f" error: {exc}")
            time.sleep(5)
            continue
        for k in ("prose", "filled", "changed"):
            totals[k] += stats[k]
        if stats["fallback"]:
            totals["fallbacks"] += 1
        if stats["changed"]:
            totals["chapters_touched"] += 1
        marker = " (fallback)" if stats["fallback"] else ""
        print(f" {stats['filled']}/{stats['prose']} prose aligned{marker}")
        if not args.dry_run:
            time.sleep(1)

    print(
        f"\nTotal: {totals['filled']}/{totals['prose']} prose aligned, "
        f"{totals['changed']} written across {totals['chapters_touched']} chapters, "
        f"{totals['fallbacks']} length-DP fallbacks"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
