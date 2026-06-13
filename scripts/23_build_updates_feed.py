#!/usr/bin/env python3
"""
Build the "What's new" RSS feed + changelog from data/updates.yaml.

Returning visitors (and anyone who wants to follow the dashboard) get a way to
see what changed without re-checking every page. This emits:

  * updates/feed.xml      — RSS 2.0 feed
  * updates/CHANGELOG.md  — human-readable changelog

Both are committed artifacts. Because this repo is the data source but the
public site is served via the wrapper, the feed should be synced to the public
host the same way the maps are (see .github/workflows/refresh-data.yml). Until
then the feed is still valid and viewable from the repo.

Run from the repo root (and in the refresh pipeline):

    python scripts/23_build_updates_feed.py
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "updates.yaml"
OUT_DIR = ROOT / "updates"
SITE = "https://maxwellhowegis.com/Lynn-data-dive"
TITLE = "LEHS Data Dive — What's New"
DESC = "Updates to the Lynn English High School data dashboard."


def _load() -> list[dict]:
    try:
        data = yaml.safe_load(SRC.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    items = data.get("updates", [])
    # Sort newest first by date string (ISO sorts lexically).
    return sorted([i for i in items if i.get("date") and i.get("title")],
                  key=lambda i: str(i["date"]), reverse=True)


def _pubdate(date_str: str) -> str:
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        dt = datetime.now(timezone.utc)
    return format_datetime(dt)


def _build_rss(items: list[dict]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        f"<title>{escape(TITLE)}</title>",
        f"<link>{escape(SITE)}</link>",
        f"<description>{escape(DESC)}</description>",
        f"<lastBuildDate>{format_datetime(datetime.now(timezone.utc))}</lastBuildDate>",
    ]
    for it in items:
        body = " ".join(str(it.get("body", "")).split())
        guid = f"{SITE}#{it['date']}-{abs(hash(it['title'])) % 10**8}"
        parts += [
            "<item>",
            f"<title>{escape(str(it['title']))}</title>",
            f"<link>{escape(SITE)}</link>",
            f"<guid isPermaLink=\"false\">{escape(guid)}</guid>",
            f"<pubDate>{_pubdate(it['date'])}</pubDate>",
            f"<description>{escape(body)}</description>",
            "</item>",
        ]
    parts.append("</channel></rss>")
    return "\n".join(parts)


def _build_md(items: list[dict]) -> str:
    lines = ["# What's new — LEHS Data Dive", "",
             "Updates to the dashboard, newest first.", ""]
    for it in items:
        lines.append(f"### {it['date']} — {it['title']}")
        body = " ".join(str(it.get("body", "")).split())
        if body:
            lines += ["", body, ""]
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    items = _load()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "feed.xml").write_text(_build_rss(items), encoding="utf-8")
    (OUT_DIR / "CHANGELOG.md").write_text(_build_md(items), encoding="utf-8")
    print(f"Wrote updates/feed.xml + updates/CHANGELOG.md — {len(items)} entries.")


if __name__ == "__main__":
    main()
