#!/usr/bin/env python3
"""Validate the Sanguo Yanyi translation layer against three failure modes:

  (A) PROSE GAP — a non-poem unit whose `canonical_translations` is empty.
      After sanguo_align.py this should be ~0. A non-zero count means Brewitt-
      Taylor returned nothing for that chapter (network/Wikisource failure)
      and prose is silently missing English.

  (B) LENGTH-DP DRIFT — a prose unit whose EN-word-count / CJK-char-count
      ratio is a >3σ outlier within its chapter. The length-DP aligner is
      length-only; an outlier this extreme usually means the DP jammed
      multiple paragraphs onto a short unit or split a long unit too thin.

  (C) LLM LEAK — a unit flagged `source: "llm"` whose index is NOT in
      `identify_poem_units`'s poem set. After generate_sanguo_poems.py
      there should be none; a hit means an LLM entry landed on prose.

Exit code 0 = no errors of class (A) or (C), regardless of (B) warnings.

  (B) CAVEAT — this metric was designed to catch length-DP's failure mode
  (semantic drift caused by length-only alignment). After running the
  semantic aligner (`tools/sanguo_align_semantic.py`), class-B outliers
  may actually INCREASE, because correct semantic alignment does not
  preserve length ratios: when Brewitt-Taylor expands a terse classical
  unit into a long English speech, or when a unit introduces an embedded
  poem that Brewitt-Taylor renders in full, the ratio spikes even though
  the alignment is correct. Spot-audits confirmed this — ch.120's final
  unit (ratio 6.1) correctly carries the 340-word closing poem that the
  Chinese 「古风一篇」 introduces. Treat class B as a *flagged for review*
  list, not a defect count. The real quality signal is the eyeball test.

Run: python3 tools/validate_sanguo.py
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SANGUO_DIR = REPO_ROOT / "content" / "books" / "sanguo-yanyi" / "chapters"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sanguo_align import identify_poem_units, reading_units  # noqa: E402


def cjk_char_count(text: str) -> int:
    return max(1, len(re.sub(r"[^\u3400-\u9fff\U00020000-\U0002ebef]", "", text)))


def en_word_count(text: str) -> int:
    return max(1, len(re.findall(r"[A-Za-z']+", text)))


def validate_chapter(path: str) -> dict:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    chapter = document["chapter"]
    order = chapter["order"]
    units = reading_units(document)
    poem_indices = identify_poem_units(units)

    stats = {
        "order": order,
        "units": len(units),
        "poems": len(poem_indices),
        "prose": len(units) - len(poem_indices),
        "prose_gaps": [],   # (unit_id, zh[:40])  — class A
        "drift_outliers": [],  # (unit_id, ratio, zh[:30], en[:60])  — class B
        "llm_leaks": [],    # (unit_id)  — class C
        "llm_total": 0,
        "human_total": 0,
    }

    # Class A + C: walk every unit.
    for i, unit in enumerate(units):
        ct = unit.get("canonical_translations", [])
        is_poem = i in poem_indices

        if not ct:
            if not is_poem:
                stats["prose_gaps"].append((unit["id"], unit["text"][:40]))
            continue

        for entry in ct:
            if entry.get("source") == "llm":
                stats["llm_total"] += 1
                if not is_poem:
                    stats["llm_leaks"].append(unit["id"])
            else:
                stats["human_total"] += 1

    # Class B: within-chapter ratio outliers (prose only, human only).
    ratios: list[float] = []
    samples: list[tuple[str, float, str, str]] = []
    for i, unit in enumerate(units):
        if i in poem_indices:
            continue
        ct = unit.get("canonical_translations", [])
        if not ct:
            continue
        entry = ct[0]
        if entry.get("source") == "llm":
            continue
        ratio = en_word_count(entry["text"]) / cjk_char_count(unit["text"])
        ratios.append(ratio)
        samples.append((unit["id"], ratio, unit["text"][:30], entry["text"][:60]))

    if len(ratios) >= 10:
        mean = statistics.mean(ratios)
        stdev = statistics.pstdev(ratios) or 0.0001
        for unit_id, ratio, zh, en in samples:
            if abs(ratio - mean) > 3 * stdev:
                stats["drift_outliers"].append((unit_id, round(ratio, 2), zh, en))

    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=120)
    parser.add_argument(
        "--show-outliers", type=int, default=5,
        help="Print this many class-B outliers per chapter (default 5)",
    )
    args = parser.parse_args(argv)

    files = sorted(glob.glob(str(SANGUO_DIR / "chapter-*.json")))
    paths = [
        f for f in files
        if args.start <= int(Path(f).stem.split("-")[1]) <= args.end
    ]
    if not paths:
        print(f"No chapters found in {SANGUO_DIR}", file=sys.stderr)
        return 1

    grand = {
        "units": 0, "poems": 0, "prose": 0,
        "prose_gap_chapters": 0, "total_prose_gaps": 0,
        "drift_chapters": 0, "total_outliers": 0,
        "llm_leak_chapters": 0, "total_llm_leaks": 0,
        "human_total": 0, "llm_total": 0,
    }
    errors = 0

    for path in paths:
        s = validate_chapter(path)
        for k in ("units", "poems", "prose", "human_total", "llm_total"):
            grand[k] += s[k]

        has_prose_gap = bool(s["prose_gaps"])
        has_outliers = bool(s["drift_outliers"])
        has_llm_leak = bool(s["llm_leaks"])

        if not (has_prose_gap or has_outliers or has_llm_leak):
            continue  # clean chapter, stay quiet

        print(f"Ch{s['order']:>3}  ({s['units']}u, {s['prose']} prose, {s['poems']} poem)")
        if has_prose_gap:
            grand["prose_gap_chapters"] += 1
            grand["total_prose_gaps"] += len(s["prose_gaps"])
            errors += 1
            print(f"  [A] PROSE GAPS ({len(s['prose_gaps'])}):")
            for uid, zh in s["prose_gaps"][:5]:
                print(f"      {uid}: {zh}")
        if has_outliers:
            grand["drift_chapters"] += 1
            grand["total_outliers"] += len(s["drift_outliers"])
            print(f"  [B] LENGTH-DRIFT OUTLIERS ({len(s['drift_outliers'])}):")
            for uid, ratio, zh, en in s["drift_outliers"][:args.show_outliers]:
                print(f"      {uid} ratio={ratio}  zh='{zh}'  en='{en}'")
        if has_llm_leak:
            grand["llm_leak_chapters"] += 1
            grand["total_llm_leaks"] += len(s["llm_leaks"])
            errors += 1
            print(f"  [C] LLM LEAKS ({len(s['llm_leaks'])}): {s['llm_leaks']}")

    print()
    print("=" * 72)
    print(f"Units: {grand['units']} total | {grand['prose']} prose | {grand['poems']} poems")
    print(
        f"Translations: {grand['human_total']} human (Brewitt-Taylor) | "
        f"{grand['llm_total']} llm"
    )
    print(
        f"[A] prose gaps:    {grand['total_prose_gaps']:>4} across "
        f"{grand['prose_gap_chapters']:>3} chapters  (ERROR)"
    )
    print(
        f"[B] drift outliers:{grand['total_outliers']:>4} across "
        f"{grand['drift_chapters']:>3} chapters  (advisory)"
    )
    print(
        f"[C] llm leaks:     {grand['total_llm_leaks']:>4} across "
        f"{grand['llm_leak_chapters']:>3} chapters  (ERROR)"
    )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
