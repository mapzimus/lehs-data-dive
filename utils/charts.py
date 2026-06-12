"""
Reusable Plotly chart helpers.

Every section of the dashboard should build on these so visual style stays
consistent and changes propagate everywhere.
"""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def csv_download(df: pd.DataFrame, filename: str, label: str | None = None,
                  key: str | None = None) -> None:
    """Render a small CSV download button for a single dataframe.

    Keep button labels short — typical use is right under a chart or table.
    """
    if df is None or df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label or f"⬇ Download CSV ({len(df):,} rows)",
        data=csv,
        file_name=filename,
        mime="text/csv",
        key=key,
        use_container_width=False,
    )


def data_downloads_panel(datasets: dict[str, pd.DataFrame],
                          title: str = "Download underlying data") -> None:
    """Render an expander with one CSV download button per dataset.

    `datasets` maps a friendly label → DataFrame. Empty DataFrames are skipped.
    """
    non_empty = {k: v for k, v in datasets.items() if v is not None and not v.empty}
    if not non_empty:
        return
    with st.expander(f"📁 {title}"):
        st.caption(
            "Key datasets behind this page. Download as CSV to do your own analysis."
        )
        for label, df in non_empty.items():
            slug = label.lower().replace(" ", "_").replace("/", "-")
            csv_download(df, f"{slug}.csv", label=f"⬇ {label}  ({len(df):,} rows)",
                         key=f"dl_{slug}")

from utils.constants import (
    GATEWAY_PEER_COLOR,
    LEHS_NAVY,
    LEHS_GOLD,
    LYNN_SIBLING_COLOR,
    STATE_COLOR,
    SUBGROUP_PALETTE,
)

DEFAULT_LAYOUT = dict(
    template="simple_white",
    # Font color lifted to match the new pastel LEHS_NAVY token in constants.
    font=dict(family="sans-serif", size=13, color="#3F4D66"),
    # Margins tightened per UI audit — every chart gains ~3-5% vertical
    # real estate.
    margin=dict(l=30, r=10, t=30, b=30),
    plot_bgcolor="#FAFBFD",
    paper_bgcolor="rgba(0,0,0,0)",
    hoverlabel=dict(bgcolor="white", font_size=12),
)


# MCAS Grade-10 results exist for 2017, 2018, 2019, (no 2020 — COVID), 2021-2025
# in the mcas_achievement dataset (verified 2026-06-05; 2026 not yet released).
# `with_year_gaps()` reindexes to this tuple, so it MUST cover the full span or
# the earliest years are silently dropped — 2017/2018 were being lost when this
# started at 2019. 2020 is kept as an explicit member so the line BREAKS (NaN)
# at the COVID gap rather than drawing straight across it.
MCAS_YEARS = (2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025)


def with_year_gaps(
    df: pd.DataFrame,
    value_col: str,
    group_col: str | None = None,
    year_col: str = "SY",
    years: tuple[int, ...] = MCAS_YEARS,
) -> pd.DataFrame:
    """Reindex so every series has a row for every year (missing → NaN).

    Plotly line charts draw a straight segment across a skipped year unless the
    skipped year is present with a NaN value. MCAS has no 2020 (COVID) and some
    series skip 2021 — feed the result of this through px.line with
    ``connectgaps=False`` so the line BREAKS at the gap instead of implying a
    smooth trend across it.
    """
    if df.empty:
        return df
    full = list(years)
    if group_col:
        frames = []
        for key, g in df.groupby(group_col):
            g = g.drop_duplicates(subset=[year_col]).set_index(year_col).reindex(full)
            g[group_col] = key
            g[year_col] = full
            frames.append(g.reset_index(drop=True))
        return pd.concat(frames, ignore_index=True)
    g = df.drop_duplicates(subset=[year_col]).set_index(year_col).reindex(full)
    g[year_col] = full
    return g.reset_index(drop=True)


def span_years(df: pd.DataFrame, year_col: str = "SY") -> tuple[int, ...]:
    """Contiguous (min..max) year tuple covering a frame's span.

    Feed this to ``with_year_gaps(..., years=span_years(df))`` so any year with
    no row — most importantly the 2020 COVID assessment gap — becomes an explicit
    NaN and the line BREAKS there (with ``connectgaps=False``) instead of drawing
    a straight segment across it. Returns an empty tuple for an empty/garbage
    frame so callers can guard cheaply.
    """
    if df is None or df.empty or year_col not in df.columns:
        return ()
    yrs = pd.to_numeric(df[year_col], errors="coerce").dropna()
    if yrs.empty:
        return ()
    return tuple(range(int(yrs.min()), int(yrs.max()) + 1))


def year_heatmap(
    pivot: pd.DataFrame,
    *,
    colorscale,
    zmid: float | None = None,
    zmin: float | None = None,
    zmax: float | None = None,
    value_fmt: str = "{:.0f}",
    colorbar_title: str = "",
    height: int | None = None,
) -> go.Figure:
    """Heatmap from a (rows × year-columns) pivot, with the value printed in each cell.

    Missing cells (NaN) render blank — use this for a 2020 COVID gap column or
    small-n suppression (mask those cells to NaN before calling).
    """
    z = pivot.astype(float).values
    text = [
        ["" if pd.isna(v) else value_fmt.format(v) for v in row]
        for row in z
    ]
    fig = go.Figure(
        go.Heatmap(
            z=z,
            x=[str(c) for c in pivot.columns],
            y=[str(i) for i in pivot.index],
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=11),
            colorscale=colorscale,
            zmid=zmid,
            zmin=zmin,
            zmax=zmax,
            hoverongaps=False,
            xgap=2,
            ygap=2,
            colorbar=dict(title=colorbar_title, thickness=12),
        )
    )
    layout = {**DEFAULT_LAYOUT}
    if height is not None:
        layout["height"] = height
    fig.update_layout(**layout)
    fig.update_yaxes(autorange="reversed")
    return fig
