#!/usr/bin/env python3
"""
Extract translatable UI strings and audit translation coverage.

Scans ``pages/`` + ``utils/`` for ``t("…")`` / ``t('…')`` calls (the i18n helper
in ``utils/i18n.py``), collects every English source string, and:

  * refreshes ``lang/en.json`` (the source catalog — identity map, handy as the
    canonical list of strings to translate), and
  * reports coverage for each non-English catalog in ``lang/`` (how many source
    strings have a translation), listing the missing ones.

Exit code is non-zero if any catalog is below ``--threshold`` coverage, so this
can later gate CI. Run from the repo root::

    python scripts/20_extract_i18n.py                 # report only
    python scripts/20_extract_i18n.py --write-en      # also refresh lang/en.json
    python scripts/20_extract_i18n.py --threshold 0.9 # fail under 90% es coverage

Only literal string arguments are extracted; ``t(variable)`` calls can't be seen
statically and are skipped (keep UI strings as literals at the call site).
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["pages", "utils"]
LANG_DIR = ROOT / "lang"


def _string_args_of_t(tree: ast.AST) -> set[str]:
    """Every literal first-arg passed to a call named ``t``."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        is_t = (isinstance(fn, ast.Name) and fn.id == "t") or (
            isinstance(fn, ast.Attribute) and fn.attr == "t"
        )
        if not is_t or not node.args:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.add(first.value)
    return found


def extract_strings() -> set[str]:
    strings: set[str] = set()
    for d in SCAN_DIRS:
        for py in sorted((ROOT / d).glob("*.py")):
            try:
                # utf-8-sig tolerates a leading BOM (some pages carry one).
                tree = ast.parse(py.read_text(encoding="utf-8-sig"))
            except SyntaxError as e:
                print(f"  [WARN] skip {py.name}: {e}")
                continue
            strings |= _string_args_of_t(tree)
    return strings


def load_catalog(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-en", action="store_true", help="refresh lang/en.json")
    ap.add_argument("--threshold", type=float, default=0.0,
                    help="fail if any es catalog covers < this fraction (0–1)")
    args = ap.parse_args()

    LANG_DIR.mkdir(exist_ok=True)
    sources = extract_strings()
    print(f"Found {len(sources)} translatable string(s) across {SCAN_DIRS}.")

    if args.write_en:
        en = {s: s for s in sorted(sources)}
        (LANG_DIR / "en.json").write_text(
            json.dumps(en, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote lang/en.json ({len(en)} strings).")

    worst = 1.0
    for cat_path in sorted(LANG_DIR.glob("*.json")):
        if cat_path.stem in ("en",):
            continue
        cat = {k: v for k, v in load_catalog(cat_path).items() if not k.startswith("_")}
        translated = [s for s in sources if s in cat]
        missing = sorted(s for s in sources if s not in cat)
        cov = len(translated) / len(sources) if sources else 1.0
        worst = min(worst, cov)
        print(f"\n{cat_path.name}: {len(translated)}/{len(sources)} = {cov:.0%} covered")
        if missing:
            print(f"  {len(missing)} missing — first 15:")
            for s in missing[:15]:
                print(f"    · {s!r}")

    if args.threshold and worst < args.threshold:
        print(f"\nFAIL: lowest coverage {worst:.0%} < threshold {args.threshold:.0%}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
