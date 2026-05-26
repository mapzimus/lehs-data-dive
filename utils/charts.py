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
            "Every visualization on this page is built from one of the datasets "
            "below. Download as CSV to do your own analysis."
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


def trend_line(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    y_label: str | None = None,
    color_map: dict | None = None,
) -> go.Figure:
    """Standard multi-line trend chart."""
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        markers=True,
        color_discrete_map=color_map or SUBGROUP_PALETTE,
        title=title,
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title=y_label or y, xaxis_title="")
    return fig


def grouped_bar(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    barmode: str = "group",
) -> go.Figure:
    """Grouped or stacked bar chart."""
    fig = px.bar(df, x=x, y=y, color=color, barmode=barmode, title=title)
    fig.update_layout(**DEFAULT_LAYOUT)
    return fig


def scatter_with_regression(
    df: pd.DataFrame,
    x: str,
    y: str,
    label_col: str | None = None,
    highlight_value: str | None = None,
    title: str = "",
) -> go.Figure:
    """Scatter plot with OLS regression line; optionally highlight one point (e.g., LEHS)."""
    fig = px.scatter(
        df,
        x=x,
        y=y,
        text=label_col,
        trendline="ols",
        title=title,
    )
    fig.update_traces(marker=dict(size=10, color=GATEWAY_PEER_COLOR))
    if label_col and highlight_value:
        mask = df[label_col] == highlight_value
        if mask.any():
            fig.add_trace(
                go.Scatter(
                    x=df.loc[mask, x],
                    y=df.loc[mask, y],
                    mode="markers+text",
                    marker=dict(size=16, color=LEHS_GOLD, line=dict(color=LEHS_NAVY, width=2)),
                    text=[highlight_value],
                    textposition="top center",
                    name=highlight_value,
                    showlegend=False,
                )
            )
    fig.update_layout(**DEFAULT_LAYOUT)
    return fig


def gap_chart(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    reference_group: str = "All Students",
    title: str = "",
) -> go.Figure:
    """Horizontal bar showing gap of each group vs. a reference group."""
    if reference_group not in df[group_col].values:
        return go.Figure()
    ref_value = df.loc[df[group_col] == reference_group, value_col].iloc[0]
    plot_df = df.copy()
    plot_df["gap"] = plot_df[value_col] - ref_value
    plot_df = plot_df[plot_df[group_col] != reference_group].sort_values("gap")
    fig = go.Figure(
        go.Bar(
            y=plot_df[group_col],
            x=plot_df["gap"],
            orientation="h",
            marker_color=[LEHS_NAVY if v >= 0 else "#D32F2F" for v in plot_df["gap"]],
        )
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        title=title or f"Gap vs. {reference_group}",
        xaxis_title=f"Difference from {reference_group}",
    )
    return fig


def small_multiples(
    df: pd.DataFrame,
    x: str,
    y: str,
    facet_col: str,
    facet_wrap: int = 3,
    title: str = "",
) -> go.Figure:
    """Small-multiples trend chart — one panel per school/group."""
    fig = px.line(
        df,
        x=x,
        y=y,
        facet_col=facet_col,
        facet_col_wrap=facet_wrap,
        markers=True,
        title=title,
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=400)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    return fig


def peer_scorecard(df: pd.DataFrame, highlight: str | None = None) -> pd.DataFrame.style:
    """Pandas Styler for a peer-comparison scorecard table."""
    styled = df.style.format(precision=1, na_rep="—")
    if highlight and highlight in df.index:
        styled = styled.apply(
            lambda row: ["background-color: #FFF4D6" if row.name == highlight else "" for _ in row],
            axis=1,
        )
    return styled
