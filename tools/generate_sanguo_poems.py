#!/usr/bin/env python3
"""Generate labeled English translations for the poem/closing-formula units in
Sanguo Yanyi that Brewitt-Taylor omits, using GLM.

WHY THIS EXISTS
  Brewitt-Taylor's 1925 translation silently drops every verse insert in the
  Chinese original — the famous opening 滚滚长江东逝水..., the embedded
  regulation poems, and the 毕竟…且听下文分解 closers. `sanguo_align.py`
  leaves those units with `canonical_translations: []`. This script fills
  them.

WHY IT IS LABELED
  The project's documented stance (build_chengyu.py provenance note, README,
  migration 005) is that machine translation is a known failure mode and is
  NOT seeded as canon. Filling these gaps with GLM reverses that stance for
  one narrow case (verse that has no PD human rendering at all). To stay
  honest, every entry written here carries `source: "llm"`, which the reader
  renders with a visible "AI-generated" badge — never presenting these as
  authoritative human canon. This is the trade-off the project owner
  accepted explicitly for the ~1,067 verse units.

PIPELINE
  For each chapter, `identify_poem_units` (imported from sanguo_align — same
  heuristic the prose aligner used to exclude these units) finds the verse
  indices. We then batch the chapter's poems into a single GLM call (giving
  each poem the preceding prose unit as narrative context) and write the
  results back into `canonical_translations[]` with the LLM provenance tag.

ENV
  GLM_API_KEY     required
  GLM_BASE_URL    optional override (default: the public GLM endpoint)
  GLM_MODEL       optional override (default: glm-4-plus)
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
SANGUO_DIR = REPO_ROOT / "content" / "books" / "sanguo-yanyi" / "chapters"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanguo_align import (  # noqa: E402
    identify_poem_units,
    list_chapter_paths,
    read_json,
    write_json,
    reading_units,
)

DEFAULT_MODEL = "glm-5-turbo"
DEFAULT_BASE_URL = "https://api.z.ai/api/anthropic"

LLM_TRANSLATION = {
    "translator": "GLM",
    "year": 2026,
    "license": "machine-generated",
    "source_url": "https://api.z.ai/",
    "source": "llm",
}

PROMPT_TEMPLATE = """You are translating classical Chinese verse from the Ming-dynasty novel *Sanguo Yanyi* (三国演义, Romance of the Three Kingdoms) into English.

For each poem or closing-formula line below, produce a faithful English verse translation. These are the lines that Brewitt-Taylor's 1925 prose translation omitted entirely, so there is no reference English to copy from — translate freshly.

Constraints:
- Translate each input as ONE English rendering. Keep verse rhythm where natural; do not pad.
- Preserve the meaning; do not invent plot details.
- Each numbered input maps to one numbered output. If an input is a 毕竟/未知/欲知 … 且听 closing formula, translate it as the conventional "But the sequel must be told in the next chapter" style formula.
- Return ONLY a JSON object mapping the input number to its translation string, e.g. {{"1": "...", "2": "..."}}. No commentary, no markdown fences.

Chapter {order} — {n} verse units:

{entries}
"""


# ---------------------------------------------------------------------------
# GLM client (urllib — no new dependency; matches tools/_cedict.py precedent)
# ---------------------------------------------------------------------------


def glm_chat(messages: list[dict], *, model: str, max_tokens: int) -> str:
    """Call the GLM coding-plan endpoint (Anthropic Messages API shape).

    The active provider in ~/.zcode/v2/config.json is `zai-coding-plan`:
    base URL https://api.z.ai/api/anthropic, kind=anthropic, model glm-5-turbo.
    That endpoint speaks the Anthropic Messages protocol (x-api-key header,
    /v1/messages path, response content[0].text), NOT OpenAI chat completions.
    """
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        raise ValueError("GLM_API_KEY is not set (required to generate poems)")
    base_url = os.environ.get("GLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }).encode("utf-8")
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
        with urllib.request.urlopen(request, timeout=180) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"GLM HTTP {exc.code}: {detail}") from exc

    # Anthropic Messages response shape: {content: [{type: "text", text: "..."}]}
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
        # Strip ```json or ``` fence.
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
# Per-chapter generation
# ---------------------------------------------------------------------------


def make_prompt(order: int, poem_units: list[tuple[int, dict, dict | None]]) -> str:
    """Build the prompt. Each poem gets the preceding prose unit as context."""
    lines = []
    for n, (_unit_idx, unit, prev) in enumerate(poem_units, start=1):
        ctx = ""
        if prev and prev.get("canonical_translations"):
            ctx = f"\n   [context — preceding prose EN: {prev['canonical_translations'][0]['text'][:200]}]"
        lines.append(f"[{n}] {unit['text']}{ctx}")
    return PROMPT_TEMPLATE.format(order=order, n=len(poem_units), entries="\n".join(lines))


def make_llm_entry(text: str) -> dict:
    entry = dict(LLM_TRANSLATION)
    entry["text"] = text
    return entry


def generate_chapter(model: str, path: Path, *, dry_run: bool) -> dict:
    document = read_json(path)
    chapter = document["chapter"]
    order = chapter["order"]
    units = reading_units(document)
    stats = {"order": order, "poems": 0, "filled": 0, "changed": 0}

    if not units:
        return stats

    poem_indices = identify_poem_units(units)
    if not poem_indices:
        print(f"  Ch{order}: no poems")
        return stats
    stats["poems"] = len(poem_indices)

    # For each poem, also surface the previous unit (usually prose) for context.
    poem_units: list[tuple[int, dict, dict | None]] = []
    sorted_indices = sorted(poem_indices)
    for idx in sorted_indices:
        prev = units[idx - 1] if idx > 0 else None
        poem_units.append((idx, units[idx], prev))

    prompt = make_prompt(order, poem_units)
    if dry_run:
        print(f"  Ch{order}: would translate {len(poem_units)} poems (dry-run)")
        stats["filled"] = len(poem_units)
        return stats

    response_text = glm_chat(
        [{"role": "user", "content": prompt}],
        model=model,
        max_tokens=4096,
    )
    parsed = extract_json_object(response_text)
    if not isinstance(parsed, dict):
        print(f"  Ch{order}: FAILED to parse GLM response as JSON object")
        print(f"    raw: {response_text[:300]}")
        return stats

    changed = 0
    # Map "1".."N" back to unit indices; tolerate either str or int keys.
    for n, (idx, unit, _prev) in enumerate(poem_units, start=1):
        translation = parsed.get(str(n)) or parsed.get(n)
        if not isinstance(translation, str) or not translation.strip():
            print(f"  Ch{order} poem {n} (unit idx {idx}): no translation returned")
            continue
        new_entry = make_llm_entry(translation.strip())
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
    parser.add_argument("--dry-run", action="store_true", help="Print plan without calling GLM or writing")
    args = parser.parse_args(argv)

    if not args.dry_run and not os.environ.get("GLM_API_KEY"):
        print("GLM_API_KEY is not set. Use --dry-run to plan without calling GLM.", file=sys.stderr)
        return 2

    paths = list_chapter_paths(args.start, args.end)
    if not paths:
        print(f"No chapters found in {SANGUO_DIR}", file=sys.stderr)
        return 1

    totals = {"poems": 0, "filled": 0, "changed": 0, "chapters_touched": 0}
    for path in paths:
        order = int(path.stem.split("-")[1])
        print(f"Ch{order}...", end="", flush=True)
        try:
            stats = generate_chapter(args.model, path, dry_run=args.dry_run)
        except Exception as exc:
            print(f" error: {exc}")
            # Back off before the next chapter on a likely rate-limit / transient.
            time.sleep(5)
            continue
        for k in ("poems", "filled", "changed"):
            totals[k] += stats[k]
        if stats["changed"]:
            totals["chapters_touched"] += 1
        print(f" {stats['filled']}/{stats['poems']} poems filled")
        if not args.dry_run:
            time.sleep(1)  # gentle on the API between chapters

    print(
        f"\nTotal: {totals['filled']}/{totals['poems']} poems filled, "
        f"{totals['changed']} units written across {totals['chapters_touched']} chapters"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
