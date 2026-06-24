"""Search — find a page or section across the whole dashboard."""

import json
import re

import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.constants import PROJECT_ROOT
from utils.url_state import qp_get, qp_set

st.set_page_config(page_title="Search | LEHS", page_icon="🔎", layout="wide")
sidebar_attribution()

INDEX_PATH = PROJECT_ROOT / "data" / "search_index.json"

# Section headings carry decorative emoji/icon prefixes (e.g. "📊 MCAS Results");
# strip the leading non-letter/digit clutter so search results read cleanly.
_LEADING_ICON = re.compile(r"^[^0-9A-Za-z]+")


def _clean_section(text: str) -> str:
    return _LEADING_ICON.sub("", text).strip() or text


@st.cache_data(show_spinner=False)
def _load_index() -> list[dict]:
    try:
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


st.title("Search the dashboard")
st.markdown(
    "Search across every page title and section heading. Useful when you know "
    "what you're looking for but not which page it lives on."
)

index = _load_index()
if not index:
    st.info(
        "Search index not built yet. Run "
        "`python scripts/22_build_search_index.py` to generate it."
    )
    st.stop()

# Query persists in the URL so a search is shareable (?q=...).
query = st.text_input(
    "Search", value=qp_get("q", "") or "", placeholder="e.g. graduation, suspension, AP, housing…",
    key="search_q", label_visibility="collapsed",
)
qp_set("q", query or None)

q = (query or "").strip().lower()
if not q:
    st.caption(f"{len(index)} pages indexed. Start typing to search.")
    page_footer()
    st.stop()

# Rank: a page matches if the query hits its title or any section. Title hits
# rank above section-only hits; within each, more matching sections first.
results = []
for entry in index:
    title = entry.get("title", "")
    url = entry.get("url_path", "")
    sections = entry.get("sections", [])
    title_hit = q in title.lower()
    matched = [s for s in sections if q in s.lower()]
    if title_hit or matched:
        results.append({
            "title": title, "url": url, "matched": matched,
            "rank": (0 if title_hit else 1, -len(matched)),
        })

results.sort(key=lambda r: r["rank"])

if not results:
    st.warning(f"No pages or sections match “{query}”. Try a shorter or different term.")
else:
    st.caption(f"{len(results)} page(s) match “{query}”.")
    for r in results:
        with st.container(border=True):
            st.markdown(f"### [{r['title']}](/{r['url']})")
            if r["matched"]:
                bullets = "\n".join(f"- {_clean_section(s)}" for s in r["matched"][:6])
                st.markdown("Matching sections:\n" + bullets)

page_footer()
