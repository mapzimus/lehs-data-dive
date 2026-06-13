"""Stories — short, factual reads grounded in the dashboard's data."""

from pathlib import Path

import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.constants import PROJECT_ROOT

st.set_page_config(page_title="Stories | LEHS", page_icon="📖", layout="wide")
sidebar_attribution()

STORIES_DIR = PROJECT_ROOT / "content" / "stories"


def parse_story(path: Path) -> dict:
    """Parse one `*.md` story file into a dict of front-matter + body.

    Front matter is an optional `---`-delimited block of simple
    `key: value` lines at the top of the file. Parsing is dependency-free
    and tolerant: files without front matter fall back to the filename as
    the title and the whole file as the body.
    """
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text

    # A valid front-matter block starts with a `---` fence on the first
    # non-empty line and is closed by the next `---` fence.
    stripped = text.lstrip("﻿")  # tolerate a leading BOM
    lines = stripped.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                # Everything between the fences is front matter; the rest is body.
                for fm_line in lines[1:i]:
                    if not fm_line.strip() or ":" not in fm_line:
                        continue
                    key, _, value = fm_line.partition(":")
                    meta[key.strip().lower()] = value.strip()
                body = "\n".join(lines[i + 1:]).strip()
                break

    return {
        "title": meta.get("title") or path.stem.replace("-", " ").replace("_", " ").strip(),
        "date": meta.get("date", ""),
        "summary": meta.get("summary", ""),
        "link_label": meta.get("link_label", ""),
        "link_url": meta.get("link_url", ""),
        "body": body,
    }


def load_stories() -> list[dict]:
    """Read every `*.md` under STORIES_DIR, newest first."""
    if not STORIES_DIR.exists():
        return []
    stories = [parse_story(p) for p in STORIES_DIR.glob("*.md")]
    # Date strings are ISO (YYYY-MM-DD), so a reverse lexical sort is
    # chronological, newest first. Undated posts sort to the bottom.
    stories.sort(key=lambda s: s["date"], reverse=True)
    return stories


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("📖 Stories")
st.markdown(
    "Short, factual reads that walk through what the data shows about Lynn English "
    "High — one thread at a time. Each story is grounded in the dashboard's own "
    "numbers and ends by pointing to the page where you can check them yourself."
)

st.divider()

# ---------------------------------------------------------------------------
# The stories
# ---------------------------------------------------------------------------

stories = load_stories()

if not stories:
    st.info("No stories yet.")
else:
    for story in stories:
        with st.container(border=True):
            st.subheader(story["title"])
            if story["date"]:
                st.caption(story["date"])
            if story["summary"]:
                st.markdown(f"*{story['summary']}*")
            if story["body"]:
                st.markdown(story["body"])
            if story["link_label"] and story["link_url"]:
                st.markdown(f"[{story['link_label']}]({story['link_url']})")

page_footer()
