"""Section 16 — MA Statewide School Districts: colored by DESE metrics."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import LEHS_GOLD, LEHS_NAVY
from utils.geo_loader import load_geojson, load_geodataframe
from utils.maps import DEFAULT_MAP_LAYOUT, MA_CENTER

st.set_page_config(
    page_title="Maps — MA Districts | LEHS", page_icon="🗺️", layout="wide"
)
sidebar_attribution()

st.title("Massachusetts School Districts — Statewide Map")
st.markdown(
    "Every Massachusetts public school district drawn as a polygon, colored by "
    "your choice of indicator. Hover any district for its key stats; click to "
    "drill in. **Lynn is outlined in gold** wherever it appears."
)

geojson = load_geojson("ma_districts_metrics")
gdf = load_geodataframe("ma_districts_metrics")

if gdf.empty:
    st.warning("MA districts GeoJSON not yet built. Run scripts/09 + 11.")
    st.stop()

# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------

metric_choice = st.selectbox(
    "Color districts by",
    options=[
        "4-year graduation rate",
        "Per-pupil spending",
        "% English Learner",
        "% Low Income",
        "% High Needs",
        "Total enrollment",
    ],
)

metric_map = {
    "4-year graduation rate": ("grad_4yr",      "Viridis",     "{:.0%}"),
    "Per-pupil spending":     ("per_pupil",     "Viridis",     "${:,.0f}"),
    "% English Learner":      ("EL_PCT",        "Greens",      "{:.0%}"),
    "% Low Income":           ("LI_PCT",        "Reds",        "{:.0%}"),
    "% High Needs":           ("HN_PCT",        "Purples",     "{:.0%}"),
    "Total enrollment":       ("TOTAL_CNT",     "Blues",       "{:,.0f}"),
}
col_name, color_scale, fmt = metric_map[metric_choice]

# ---------------------------------------------------------------------------
# Filter to districts that have the metric
# ---------------------------------------------------------------------------

plot_df = gdf.dropna(subset=[col_name]).copy()
if plot_df.empty:
    st.warning(f"No districts have data for '{metric_choice}'.")
    st.stop()

# Only show "Operating District" type to avoid double-painting from CCUV polygons
if "TYPE" in plot_df.columns:
    plot_df = plot_df[plot_df["TYPE"].isin(["Operating District", "Public District"])]

# Need to keep numeric for color, but format hover
plot_df["hover_value"] = plot_df[col_name].apply(lambda x: fmt.format(x) if pd.notna(x) else "—")

# ---------------------------------------------------------------------------
# Choropleth
# ---------------------------------------------------------------------------

fig = px.choropleth_mapbox(
    plot_df, geojson=geojson, locations="ORG8CODE",
    featureidkey="properties.ORG8CODE",
    color=col_name, color_continuous_scale=color_scale,
    hover_name="DIST_NAME",
    hover_data={"ORG8CODE": True, "TOTAL_CNT": ":,", "EL_PCT": ":.0%",
                "LI_PCT": ":.0%", "hover_value": True, col_name: False},
    zoom=7.5, center=MA_CENTER, opacity=0.65,
)

# Outline Lynn district in gold for emphasis
lynn_features = {
    "type": "FeatureCollection",
    "features": [f for f in geojson["features"]
                 if f["properties"].get("ORG8CODE") == "01630000"],
}
if lynn_features["features"]:
    fig.update_layout(mapbox_layers=[{
        "source": lynn_features, "type": "line", "color": LEHS_GOLD,
        "line": {"width": 4}, "opacity": 1.0,
    }])

fig.update_layout(**DEFAULT_MAP_LAYOUT, height=700)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Highlight LEHS district stats
# ---------------------------------------------------------------------------

lynn_row = plot_df[plot_df["ORG8CODE"] == "01630000"]
if not lynn_row.empty:
    val = lynn_row.iloc[0][col_name]
    state_median = plot_df[col_name].median()
    diff_text = ""
    if pd.notna(val) and pd.notna(state_median):
        if isinstance(val, (int, float)):
            if val > state_median:
                diff_text = f"({(val - state_median) * (100 if val < 2 else 1):+.1f} above MA median)"
            else:
                diff_text = f"({(val - state_median) * (100 if val < 2 else 1):+.1f} below MA median)"
    st.info(f"**Lynn Public Schools** (outlined in gold): {fmt.format(val)} {diff_text}")

st.divider()

# ---------------------------------------------------------------------------
# Top / bottom 10
# ---------------------------------------------------------------------------

def _build_ranking_table(df_in: pd.DataFrame) -> pd.DataFrame:
    """Build a friendly-formatted top/bottom table, handling duplicate column names safely."""
    # De-duplicate column selection: if the metric IS already one of the base columns,
    # don't list it twice
    base_cols = ["DIST_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT"]
    if col_name not in base_cols:
        cols_wanted = ["DIST_NAME", col_name] + ["TOTAL_CNT", "EL_PCT", "LI_PCT"]
    else:
        cols_wanted = base_cols
    out = df_in[cols_wanted].copy()
    # Format
    if col_name in out.columns and col_name != "TOTAL_CNT":
        out[col_name] = out[col_name].apply(lambda x: fmt.format(x) if pd.notna(x) else "—")
    out["TOTAL_CNT"] = out["TOTAL_CNT"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    out["EL_PCT"] = out["EL_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    out["LI_PCT"] = out["LI_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    # Rename — if col_name overlaps with a base name, the friendly base name wins
    rename_map = {
        "DIST_NAME": "District",
        "TOTAL_CNT": "Enrollment",
        "EL_PCT": "% ELL",
        "LI_PCT": "% Low Income",
    }
    if col_name not in rename_map:
        rename_map[col_name] = metric_choice
    return out.rename(columns=rename_map)


st.subheader(f"Top 10 districts — {metric_choice}")
st.dataframe(_build_ranking_table(plot_df.nlargest(10, col_name)),
             width="stretch", hide_index=True)

st.subheader(f"Bottom 10 districts — {metric_choice}")
st.dataframe(_build_ranking_table(plot_df.nsmallest(10, col_name)),
             width="stretch", hide_index=True)
