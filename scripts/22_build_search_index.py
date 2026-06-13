#!/usr/bin/env python3
"""
Build the site search index.

The dashboard has 30+ pages; browsing the grouped sidebar isn't always the
fastest way to reach a specific section. This script produces a small JSON
index — one entry per page with its title, public ``url_path``, and the list
of section headers it contains — that the Search page filters at runtime.

It reads ``Home.py`` to map each page file to its nav title + ``url_path``
(the source of truth for routing), then parses each page with ``ast`` to pull
the literal strings passed to ``st.title`` / ``st.header`` / ``st.subheader``.

Run from the repo root (and re-run whenever pages/headers change):

    python scripts/22_build_search_index.py

Output: data/search_index.json
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / "Home.py"
OUT = ROOT / "data" / "search_index.json"
HEADER_FUNCS = {"title", "header", "subheader"}


def _page_registry() -> list[dict]:
    """Parse Home.py's st.Page(...) calls → [{file, title, url_path}]."""
    tree = ast.parse(HOME.read_text(encoding="utf-8"))
    pages = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "Page"):
            continue
        file = node.args[0].value if (node.args and isinstance(node.args[0], ast.Constant)) else None
        kw = {k.arg: (k.value.value if isinstance(k.value, ast.Constant) else None)
              for k in node.keywords}
        if file:
            pages.append({"file": file, "title": kw.get("title") or file,
                          "url_path": kw.get("url_path", "")})
    return pages


def _section_headers(page_file: Path) -> list[str]:
    """Literal strings passed to st.title/header/subheader in a page."""
    try:
        tree = ast.parse(page_file.read_text(encoding="utf-8-sig"))
    except (OSError, SyntaxError):
        return []
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in HEADER_FUNCS and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)):
            text = node.args[0].value.strip()
            if text and text not in out:
                out.append(text)
    return out


def main() -> None:
    index = []
    for p in _page_registry():
        path = ROOT / p["file"]
        if not path.exists():
            continue
        index.append({
            "title": p["title"],
            "url_path": p["url_path"],
            "sections": _section_headers(path),
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    n_sections = sum(len(e["sections"]) for e in index)
    print(f"Wrote {OUT} — {len(index)} pages, {n_sections} section headers indexed.")


if __name__ == "__main__":
    main()
