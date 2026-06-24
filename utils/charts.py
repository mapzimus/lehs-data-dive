"""
Reusable Plotly chart helpers.

Every section of the dashboard should build on these so visual style stays
consistent and changes propagate everywhere.
"""

from __future__ import annotations

import io

import numpy as np
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
        width="content",
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
    LVTI_COLOR,
    LYNN_SIBLING_COLOR,
    STATE_COLOR,
    SUBGROUP_PALETTE,
)

from collections.abc import Mapping

from utils.theme import chart_tokens


class _ThemedLayout(Mapping):
    """A drop-in for the old ``DEFAULT_LAYOUT`` dict whose colors resolve from
    the active theme at access time.

    Because every call site uses ``**DEFAULT_LAYOUT`` / ``{**DEFAULT_LAYOUT}``
    (which go through ``keys()`` + ``__getitem__``), making this a live Mapping
    re-themes all ~180 charts with zero per-page edits. Margins/template/font
    family are constant; only the background and font colors follow the theme.
    """

    def _resolved(self) -> dict:
        t = chart_tokens()
        return dict(
            template=t["template"],
            font=dict(family="sans-serif", size=13, color=t["font_color"]),
            # Margins tightened per UI audit — every chart gains ~3-5% vertical
            # real estate.
            margin=dict(l=30, r=10, t=30, b=30),
            plot_bgcolor=t["plot_bgcolor"],
            paper_bgcolor=t["paper_bgcolor"],
            hoverlabel=dict(bgcolor=t["hover_bgcolor"], font_size=12),
        )

    def __getitem__(self, key):
        return self._resolved()[key]

    def __iter__(self):
        return iter(self._resolved())

    def __len__(self):
        return len(self._resolved())


DEFAULT_LAYOUT = _ThemedLayout()


# ---------------------------------------------------------------------------
# Peer-dot scatter — the shared LEHS / Lynn-siblings / Lynn-district vs.
# gateway-cloud scatter used by the Gateway Peer Comparison page AND the
# Correlation Lab. One implementation so the four named Lynn dots look the same
# everywhere: LEHS = gold star (biggest), Lynn Classical = navy circle, Lynn
# Tech = teal diamond, Lynn district = navy square, all other gateway main HS =
# the pale-grey cloud, with an OLS trendline fit to ALL points.
#
# The role names below are the canonical labels callers must put in their
# `role_col`. Two spellings of the district row are accepted ("Lynn district"
# and the legacy "LPS district") so both pages can share this without renaming
# their data.
# ---------------------------------------------------------------------------
PEER_ROLE_STYLE = {
    "LEHS":             dict(color=LEHS_GOLD, symbol="star",            size=20, line_color=LEHS_NAVY, line_width=2),
    "Lynn Classical":   dict(color=LEHS_NAVY, symbol="circle",          size=14, line_color=LEHS_GOLD, line_width=2),
    "Lynn Tech":        dict(color=LVTI_COLOR, symbol="diamond",        size=14, line_color=LEHS_NAVY, line_width=1),
    "Lynn district":    dict(color=LEHS_NAVY, symbol="square",          size=14, line_color="#FFFFFF", line_width=1),
    "LPS district":     dict(color=LEHS_NAVY, symbol="square",          size=14, line_color="#FFFFFF", line_width=1),
    "Other Gateway HS": dict(color=GATEWAY_PEER_COLOR, symbol="circle", size=9,  line_color="#FFFFFF", line_width=0),
}
# Plot the grey cloud first, then the district, then the siblings, then LEHS —
# so the named Lynn dots always paint on top of the cloud and LEHS on top of
# everything.
PEER_ROLE_ORDER = [
    "Other Gateway HS", "Lynn district", "LPS district",
    "Lynn Tech", "Lynn Classical", "LEHS",
]


def peer_dot_scatter(
    df: pd.DataFrame,
    x: str,
    y: str,
    *,
    role_col: str = "peer_role",
    label_col: str = "School",
    x_label: str | None = None,
    y_label: str | None = None,
    x_tickformat: str | None = None,
    y_tickformat: str | None = None,
    title: str | None = None,
    trendline: bool = True,
    **layout,
) -> go.Figure:
    """Scatter with one trace per peer role so each Lynn dot gets its own marker
    shape/size/color, plus an OLS trendline fit to ALL points.

    `df` must have `x`, `y`, `role_col` (values drawn from PEER_ROLE_STYLE), and
    `label_col` (the per-point text/hover label). Roles not in PEER_ROLE_STYLE
    fall back to the "Other Gateway HS" style. Reuses DEFAULT_LAYOUT so colors
    follow the active theme.
    """
    x_title = x_label or x
    y_title = y_label or y
    fig = go.Figure()

    present_roles = set(df[role_col].dropna().unique()) if role_col in df.columns else set()
    ordered = [r for r in PEER_ROLE_ORDER if r in present_roles]
    # Any role the caller used that isn't in our fixed order gets appended so it
    # still renders (with the fallback style) rather than vanishing.
    ordered += [r for r in present_roles if r not in PEER_ROLE_ORDER]

    for role in ordered:
        sub = df[df[role_col] == role]
        if sub.empty:
            continue
        style = PEER_ROLE_STYLE.get(role, PEER_ROLE_STYLE["Other Gateway HS"])
        is_named = role != "Other Gateway HS"
        labels = sub[label_col] if label_col in sub.columns else None
        fig.add_trace(go.Scatter(
            x=sub[x], y=sub[y],
            mode="markers+text" if is_named else "markers",
            name=role,
            marker=dict(
                color=style["color"], symbol=style["symbol"], size=style["size"],
                line=dict(color=style["line_color"], width=style["line_width"]),
            ),
            # Show labels for the named Lynn dots; suppress for the grey cloud so
            # it declutters into the trendline.
            text=labels if is_named else None,
            textposition="top center", textfont=dict(size=10, color=LEHS_NAVY),
            customdata=labels,
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                + x_title + ": %{x}<br>" + y_title + ": %{y}<extra></extra>"
            ),
        ))

    if trendline:
        try:
            valid = df.dropna(subset=[x, y])
            if len(valid) >= 3:
                xs = pd.to_numeric(valid[x], errors="coerce")
                ys = pd.to_numeric(valid[y], errors="coerce")
                ok = xs.notna() & ys.notna()
                xs, ys = xs[ok], ys[ok]
                if len(xs) >= 3:
                    m, b = np.polyfit(xs, ys, 1)
                    x_fit = pd.Series([xs.min(), xs.max()])
                    fig.add_trace(go.Scatter(
                        x=x_fit, y=m * x_fit + b,
                        mode="lines", name="OLS fit",
                        line=dict(color="#90A4AE", width=2, dash="dash"),
                        showlegend=False, hoverinfo="skip",
                    ))
        except (TypeError, ValueError):
            pass

    merged_layout = {**DEFAULT_LAYOUT, **layout}
    fig.update_layout(
        **merged_layout,
        xaxis_title=x_title,
        yaxis_title=y_title,
        xaxis_tickformat=x_tickformat,
        yaxis_tickformat=y_tickformat,
        title=title,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


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


def year_axis(fig: go.Figure) -> go.Figure:
    """Force whole-year ticks on a numeric year x-axis.

    Plotly subdivides a short numeric range (e.g. five school years) into
    half-steps, producing nonsense ticks like ``2,021.5``. This pins the tick
    interval to whole years and strips the decimal + thousands-separator comma
    (``tickformat="d"``). For longer ranges it widens the interval so a 30-year
    axis isn't a wall of labels. Call it right before ``st.plotly_chart`` on any
    chart whose x is a school year (SY / COHORTYR). Categorical (string) year
    axes are unaffected, so it's safe to call unconditionally on year charts.
    """
    xs: list = []
    for tr in fig.data:
        vals = getattr(tr, "x", None)
        if vals is not None:
            xs.extend(v for v in vals if v is not None)
    dtick = 1
    try:
        numeric = [float(v) for v in xs]
        if numeric:
            span = max(numeric) - min(numeric)
            dtick = 1 if span <= 12 else (2 if span <= 24 else (5 if span <= 60 else 10))
    except (TypeError, ValueError):
        dtick = 1
    fig.update_xaxes(dtick=dtick, tickformat="d")
    return fig


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
