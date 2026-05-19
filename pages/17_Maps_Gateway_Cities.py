"""Section 17 — Gateway Cities Map: 26 MA gateway cities + main HS pinned."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import LEHS_GOLD, LEHS_NAVY
from utils.constants import PROCESSED_DIR
from utils.data_loader import load_dataset
from utils.geo_loader import load_geojson, load_geodataframe
from utils.maps import DEFAULT_MAP_LAYOUT, MA_CENTER

st.set_page_config(
    page_title="Maps — Gateway Cities | LEHS", page_icon="🗺️", layout="wide"
)
sidebar_attribution()

st.title("Gateway Cities Map")
st.markdown(
    "The 26 Massachusetts Gateway Cities — post-industrial cities the state "
    "designates as having both high need and high potential. Each city's "
    "main comprehensive HS is pinned. Lynn is highlighted in gold."
)

gateway_gdf = load_geodataframe("gateway_hs")
districts_geojson = load_geojson("ma_districts_metrics")

if gateway_gdf.empty:
    st.warning("Gateway HS GeoJSON not yet built. Run scripts/09 + 11.")
    st.stop()

# Bring in enrollment + DART data to enrich the hover tooltip
peers_path = PROCESSED_DIR / "_peer_schools.json"
peers = json.loads(peers_path.read_text()) if peers_path.exists() else {}
city_to_code = {city: info["school_code"]
                for city, info in peers.get("gateway_main_hs", {}).items()
                if info.get("school_code")}

enrollment = load_dataset("enrollment_demographics")
latest_enr = enrollment.sort_values("SY").groupby("ORG_CODE").tail(1)[
    ["ORG_CODE", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HL_PCT"]
] if not enrollment.empty else pd.DataFrame()

gateway_gdf["school_code_dese"] = gateway_gdf["school_code_dese"].astype(str).str.zfill(8)
latest_enr["ORG_CODE"] = latest_enr["ORG_CODE"].astype(str).str.zfill(8)
gateway_gdf = gateway_gdf.merge(
    latest_enr.rename(columns={"ORG_CODE": "school_code_dese"}),
    on="school_code_dese", how="left",
)

# Highlight LEHS
gateway_gdf["is_lehs"] = gateway_gdf["school_code_dese"] == "01630510"
gateway_gdf["highlight_label"] = gateway_gdf["is_lehs"].map(
    {True: "Lynn English High", False: "Other Gateway HS"}
)
gateway_gdf["marker_size"] = (gateway_gdf["TOTAL_CNT"].fillna(500) / 100).clip(10, 40)

# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

color_choice = st.selectbox(
    "Color the gateway HS by",
    options=["LEHS vs others", "% English Learner", "% Low Income", "Total enrollment"],
)

if color_choice == "LEHS vs others":
    fig = px.scatter_mapbox(
        gateway_gdf, lat="lat", lon="lon",
        color="highlight_label",
        color_discrete_map={"Lynn English High": LEHS_GOLD, "Other Gateway HS": LEHS_NAVY},
        size="marker_size", size_max=40,
        text="city",
        hover_name="NAME",
        hover_data={"city": True, "TOTAL_CNT": ":,",
                    "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                    "lat": False, "lon": False, "marker_size": False,
                    "highlight_label": False},
        zoom=7, center=MA_CENTER,
        labels={"highlight_label": "School"},
    )
    fig.update_layout(legend_title_text="")
else:
    col_map = {
        "% English Learner": "EL_PCT",
        "% Low Income": "LI_PCT",
        "Total enrollment": "TOTAL_CNT",
    }
    cname = col_map[color_choice]
    plot_df = gateway_gdf.dropna(subset=[cname]).copy()
    fig = px.scatter_mapbox(
        plot_df, lat="lat", lon="lon",
        color=cname,
        color_continuous_scale="Viridis",
        size="marker_size", size_max=40,
        text="city",
        hover_name="NAME",
        hover_data={"city": True, "TOTAL_CNT": ":,",
                    "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                    "lat": False, "lon": False, "marker_size": False},
        zoom=7, center=MA_CENTER,
    )

fig.update_traces(textposition="top center", textfont=dict(size=10))
fig.update_layout(**DEFAULT_MAP_LAYOUT, height=650)

# Optional: outline gateway-city districts
if districts_geojson.get("features"):
    gateway_codes = set(city_to_code.values())
    # Build set of gateway DISTRICT codes (first 4 chars of school code + "0000")
    gateway_district_codes = set()
    for code in gateway_codes:
        if code:
            gateway_district_codes.add(code[:4] + "0000")
    gateway_district_features = {
        "type": "FeatureCollection",
        "features": [
            f for f in districts_geojson["features"]
            if (f["properties"].get("ORG8CODE") or "") in gateway_district_codes
        ],
    }
    if gateway_district_features["features"]:
        fig.update_layout(mapbox_layers=[{
            "source": gateway_district_features, "type": "line", "color": LEHS_NAVY,
            "line": {"width": 1.5}, "opacity": 0.4,
        }])

st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Scorecard table
# ---------------------------------------------------------------------------

st.header("All 26 Gateway HS — at a glance")

display = gateway_gdf[["city", "NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HL_PCT"]].copy()
display = display.rename(columns={
    "city": "City", "NAME": "School", "TOTAL_CNT": "Enrollment",
    "EL_PCT": "% ELL", "LI_PCT": "% Low Income", "HL_PCT": "% Hispanic/Latino",
})
display["Enrollment"] = display["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
for c in ["% ELL", "% Low Income", "% Hispanic/Latino"]:
    display[c] = display[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

def highlight_lehs(row):
    if row["City"] == "Lynn":
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)

st.dataframe(display.sort_values("City").style.apply(highlight_lehs, axis=1),
             width="stretch", hide_index=True)
