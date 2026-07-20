#!/usr/bin/env python3
"""Convert Traditional Chinese → Simplified Chinese across the repo.

- Idempotent: OpenCC t2s is a no-op on already-simplified text, so files
  that are already simplified (e.g. chengyu-catalog) pass through unchanged.
- Selective per field: only Han character runs are converted; ASCII fields
  (ids, slugs, URLs, pinyin, pinyin_per_char, source_url, license,
  translator, source_title provenance strings) are preserved as-is.
"""
import json
import re
import sys
from pathlib import Path

from opencc import OpenCC

CONVERTER = OpenCC("t2s")
HAN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")

# JSON keys whose string values are pure metadata / pinyin / provenance and
# must NOT be converted (they hold transliteration or latin-only content).
# Han-bearing fields like title, text, summary, expression, _doc are converted.
SKIP_KEYS = {
    "id",
    "pinyin",
    "pinyin_source",
    "pinyin_per_char",
    "source_url",
    "source_title",
    "chapter_path",
    "license",
    "translator",
    "cache_dir",
    "catalog_path",
    "schema_version",
    "provider",
    "year",
    "source_block_chunk",
}


def conv(s: str) -> str:
    """Convert only the Han runs in a string, leaving non-Han untouched.

    OpenCC is already safe on mixed CJK+ASCII, but scoping to Han runs avoids
    any chance of touching rare latin edge cases and keeps the diff minimal.
    """
    if not isinstance(s, str) or not s:
        return s
    if not HAN.search(s):
        return s
    return HAN.sub(lambda m: CONVERTER.convert(m.group(0)), s)


def walk(obj, key=None):
    if isinstance(obj, dict):
        return {k: walk(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk(v, key) for v in obj]
    if isinstance(obj, str):
        if key in SKIP_KEYS:
            return obj
        return conv(obj)
    return obj


def convert_json(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ! JSON parse error in {path}: {e}", file=sys.stderr)
        return False
    new = walk(data)
    # Preserve trailing newline if present; sort_keys=False to keep order.
    out = json.dumps(new, ensure_ascii=False, indent=2)
    if not raw.endswith("\n") and out.endswith("\n"):
        out = out.rstrip("\n")
    elif raw.endswith("\n") and not out.endswith("\n"):
        out += "\n"
    if out != raw:
        path.write_text(out, encoding="utf-8")
        return True
    return False


def convert_text(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    new = conv(raw)
    if new != raw:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main():
    repo = Path(__file__).resolve().parents[1]
    converted = 0
    checked = 0

    # 1. All content JSON files.
    for path in sorted((repo / "content").rglob("*.json")):
        checked += 1
        if convert_json(path):
            converted += 1
            print(f"  json  {path.relative_to(repo)}")

    # 2. Web UI sources.
    for rel in [
        "apps/web/src/lib/titles.ts",
        "apps/web/src/components/NavBar.tsx",
    ]:
        p = repo / rel
        if p.exists():
            checked += 1
            if convert_text(p):
                converted += 1
                print(f"  text  {p.relative_to(repo)}")

    # 3. Go sources (Han in comments + display-name table).
    for p in sorted((repo / "services/api").rglob("*.go")):
        raw = p.read_text(encoding="utf-8")
        new = conv(raw)
        checked += 1
        if new != raw:
            p.write_text(new, encoding="utf-8")
            converted += 1
            print(f"  go    {p.relative_to(repo)}")

    # 4. Python tools (Han in source_title etc.).
    for p in sorted((repo / "tools").rglob("*.py")):
        checked += 1
        if convert_text(p):
            converted += 1
            print(f"  py    {p.relative_to(repo)}")

    # 5. Markdown docs.
    for rel in ["content/SOURCES.md", "README.md"]:
        p = repo / rel
        if p.exists():
            checked += 1
            if convert_text(p):
                converted += 1
                print(f"  md    {p.relative_to(repo)}")

    print(f"\nChecked {checked} files; converted {converted}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
