"""Corrections — an auditable log of data and labeling fixes."""

from pathlib import Path

import pandas as pd
import streamlit as st
import yaml

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.constants import PROJECT_ROOT  # PROJECT_ROOT exists in utils/constants.py

st.set_page_config(page_title="Corrections | LEHS", page_icon="📝", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Load the corrections log
# ---------------------------------------------------------------------------

_LOG_PATH = PROJECT_ROOT / "data" / "corrections.yaml"

entries: list[dict] = []
if _LOG_PATH.exists():
    parsed = yaml.safe_load(_LOG_PATH.read_text(encoding="utf-8")) or {}
    entries = parsed.get("corrections") or []

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("Corrections")
st.markdown(
    "This dashboard is a **living document**. When a number, label, or chart "
    "is corrected, the fix is logged here — with the date it shipped, the page "
    "it touched, what changed, and why. Keeping that record in the open makes "
    "the dashboard **transparent and auditable**: you can always trace how a "
    "figure got to where it is today, rather than seeing it quietly change "
    "from one visit to the next."
)

st.divider()

# ---------------------------------------------------------------------------
# The log
# ---------------------------------------------------------------------------

if not entries:
    st.info("No corrections logged yet.")
else:
    df = pd.DataFrame(entries)

    # Normalize/select the expected columns, tolerating missing optional fields.
    for col in ("date", "page", "change", "reason", "source"):
        if col not in df.columns:
            df[col] = ""
    df = df[["date", "page", "change", "reason", "source"]].fillna("")

    # Newest first. Dates are ISO strings, so a lexical sort is chronological.
    df = df.sort_values("date", ascending=False, kind="stable").reset_index(drop=True)

    st.caption(f"{len(df)} correction(s) logged.")

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "date": st.column_config.TextColumn("Date", width="small"),
            "page": st.column_config.TextColumn("Page", width="medium"),
            "change": st.column_config.TextColumn("Change", width="large"),
            "reason": st.column_config.TextColumn("Reason", width="large"),
            "source": st.column_config.TextColumn("Source", width="small"),
        },
    )

    # Readable card view beneath the table, for anyone who prefers prose
    # over a grid (and so long "change" text is never truncated).
    with st.expander("Read as cards", expanded=False):
        for row in df.itertuples(index=False):
            with st.container(border=True):
                header = f"**{row.date}** · {row.page}" if row.page else f"**{row.date}**"
                st.markdown(header)
                st.markdown(row.change)
                if row.reason:
                    st.caption(f"Why: {row.reason}")
                if row.source:
                    st.caption(f"Source: {row.source}")

st.divider()

# ---------------------------------------------------------------------------
# Cross-link + footer
# ---------------------------------------------------------------------------

crosslink_callout(
    "For the broader picture of what this dashboard can and can't show, see the "
    "data-gaps catalog.",
    "Data_Gaps",
    "See What We Still Don't Know →",
)

page_footer()
