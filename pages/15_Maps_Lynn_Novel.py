"""Section 15 — Lynn Novel Maps: Voronoi school catchments + bivariate analysis."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.spatial import Voronoi
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union

from utils.branding import sidebar_attribution
from utils.charts import LEHS_GOLD, LEHS_NAVY
from utils.geo_loader import load_geojson, load_geodataframe
from utils.maps import DEFAULT_MAP_LAYOUT, LYNN_CENTER

st.set_page_config(
    page_title="Maps — Lynn Novel | LEHS", page_icon="🗺️", layout="wide"
)
sidebar_attribution()

st.title("Lynn Novel Maps")
st.markdown(
    "Two analyses you won't find on DESE's site: theoretical school "
    "catchments via Voronoi tessellation, and bivariate mapping that shows "
    "two demographic dimensions in one view."
)

schools = load_geodataframe("lynn_schools")
town_geo = load_geojson("lynn_town")
town_gdf = load_geodataframe("lynn_town")

if schools.empty or town_gdf.empty:
    st.warning("Lynn GIS data not yet built.")
    st.stop()

# ---------------------------------------------------------------------------
# Voronoi diagram — theoretical "nearest school" catchments
# ---------------------------------------------------------------------------

st.header("Voronoi Catchments — Theoretical 'Nearest School' Zones")
st.caption(
    "Each polygon shows the area for which the labeled school is the closest "
    "school as the crow flies. **This is NOT the official attendance zone** — "
    "Lynn Public Schools assigns students by other criteria. But the gap "
    "between 'nearest' and 'assigned' is informative."
)

filter_type = st.selectbox(
    "Filter schools",
    options=[
        "Lynn Public Schools only (grades K-12)",
        "High schools only",
        "Elementary schools only",
        "All Lynn schools",
    ],
)

# Filter the schools data based on the toggle
sub = schools.copy()
if "DIST_NAME" in sub.columns:
    sub["DIST_NAME"] = sub["DIST_NAME"].astype(str)
if filter_type == "Lynn Public Schools only (grades K-12)":
    sub = sub[sub["DIST_NAME"].str.contains("Lynn", case=False, na=False)]
elif filter_type == "High schools only":
    sub = sub[sub["GRADES"].astype(str).str.contains("12|10|11|09", na=False)]
elif filter_type == "Elementary schools only":
    sub = sub[sub["GRADES"].astype(str).str.contains("K-|01|02|03|04|05", na=False)
              & ~sub["GRADES"].astype(str).str.contains("10|11|12", na=False)]

sub = sub.dropna(subset=["lat", "lon"])
if len(sub) < 3:
    st.warning(f"Need at least 3 schools to compute Voronoi diagram, got {len(sub)}.")
else:
    # Compute Voronoi in projected coords (MA State Plane EPSG:26986) for accuracy
    sub_projected = sub.to_crs("EPSG:26986")
    points = list(zip(sub_projected.geometry.x, sub_projected.geometry.y))
    vor = Voronoi(points)

    # Build Voronoi polygons clipped to Lynn town boundary
    lynn_poly_projected = town_gdf[town_gdf["TOWN"] == "LYNN"].to_crs("EPSG:26986").geometry.union_all()

    # Helper: build polygon from Voronoi region indices
    polygons = []
    for idx in range(len(sub)):
        region_idx = vor.point_region[idx]
        region = vor.regions[region_idx]
        if -1 in region or not region:
            polygons.append(None)
            continue
        verts = [vor.vertices[i] for i in region]
        poly = Polygon(verts)
        try:
            clipped = poly.intersection(lynn_poly_projected)
            polygons.append(clipped)
        except Exception:
            polygons.append(None)

    # Build a GeoDataFrame, reproject to WGS84
    import geopandas as gpd
    vor_gdf = gpd.GeoDataFrame(
        {"NAME": sub["NAME"].values, "TOTAL_CNT": sub["TOTAL_CNT"].values,
         "EL_PCT": sub["EL_PCT"].values if "EL_PCT" in sub.columns else None,
         "geometry": polygons},
        crs="EPSG:26986",
    ).dropna(subset=["geometry"])
    vor_gdf = vor_gdf[vor_gdf.geometry.is_valid & ~vor_gdf.geometry.is_empty]
    vor_gdf = vor_gdf.to_crs("EPSG:4326")
    vor_gdf["id"] = range(len(vor_gdf))

    if not vor_gdf.empty:
        # Plotly choropleth needs a GeoJSON dict
        vor_geojson = vor_gdf.__geo_interface__

        fig = px.choropleth_mapbox(
            vor_gdf, geojson=vor_geojson,
            locations="id", featureidkey="properties.id",
            color="NAME",
            color_discrete_sequence=px.colors.qualitative.Pastel,
            hover_name="NAME",
            hover_data={"id": False, "TOTAL_CNT": ":,"},
            zoom=12, center=LYNN_CENTER, opacity=0.5,
        )

        # Add school points on top
        fig.add_trace(go.Scattermapbox(
            lat=sub["lat"], lon=sub["lon"],
            mode="markers+text",
            marker=dict(size=10, color=LEHS_NAVY),
            text=sub["NAME"].str[:20],
            textposition="top right",
            textfont=dict(size=9, color=LEHS_NAVY),
            hovertext=sub["NAME"],
            hoverinfo="text",
            name="Schools",
            showlegend=False,
        ))

        fig.update_layout(**DEFAULT_MAP_LAYOUT, showlegend=False)
        st.plotly_chart(fig, width="stretch")

        st.caption(
            f"Voronoi tessellation of {len(vor_gdf)} schools within Lynn's town boundary. "
            "Each colored polygon is the area for which the contained school is the nearest "
            "as the crow flies."
        )

st.divider()

# ---------------------------------------------------------------------------
# Bivariate scatter — two dimensions of need at once
# ---------------------------------------------------------------------------

st.header("Bivariate View — Two Dimensions at Once")
st.caption(
    "Plotted: each Lynn school as a point in (% ELL) × (% Low Income) space. "
    "The Lynn schools that fall in the upper-right corner have the highest "
    "concentrated need on both dimensions simultaneously."
)

bv = schools.dropna(subset=["EL_PCT", "LI_PCT"]).copy()
bv["highlight"] = bv["ORG_CODE"].astype(str).str.zfill(8) == "01630510"
bv["highlight_label"] = bv["highlight"].map({True: "Lynn English High", False: "Other Lynn school"})

fig = px.scatter(
    bv, x="EL_PCT", y="LI_PCT", color="highlight_label", size="TOTAL_CNT",
    text=bv["NAME"].str[:24],
    color_discrete_map={"Lynn English High": LEHS_GOLD, "Other Lynn school": LEHS_NAVY},
    hover_name="NAME",
    labels={"EL_PCT": "% English Learner", "LI_PCT": "% Low Income"},
    size_max=40,
)
fig.update_traces(textposition="top center", textfont_size=9)
fig.update_layout(
    template="simple_white",
    xaxis_tickformat=".0%", yaxis_tickformat=".0%",
    margin=dict(l=40, r=20, t=50, b=40),
    height=600,
)
# Add quadrant lines at the median
fig.add_hline(y=bv["LI_PCT"].median(), line_dash="dash", line_color="gray",
              annotation_text="Lynn median", annotation_position="right")
fig.add_vline(x=bv["EL_PCT"].median(), line_dash="dash", line_color="gray")
st.plotly_chart(fig, width="stretch")

st.caption(
    "**Quadrant interpretation:**\n"
    "- **Top-right** (high ELL, high LI): schools serving the most concentrated need.\n"
    "- **Bottom-left** (low ELL, low LI): schools with relatively lower-need populations.\n"
    "- **Off-axis**: schools where one dimension is high but the other isn't — interesting outliers."
)

st.divider()

# ---------------------------------------------------------------------------
# Still to come
# ---------------------------------------------------------------------------

st.subheader("Further analysis worth building")
st.markdown(
    """
The Lynn maps so far show *where* and *how much*. Three additional layers
would push the analysis further:

- **Climate vulnerability + school sites** — Lynn is coastal; MA Coastal Zone
  Management publishes sea-level-rise inundation projections for 2050, 2070, 2100.
  Mapping which Lynn schools are in current or projected flood zones connects
  educational infrastructure to climate adaptation planning.
- **True bivariate choropleth** (ELL × Poverty by census tract) — would use a
  9-color biscale palette to show two demographic dimensions at once.
- **MBTA transit access + isochrones** — bus routes serving LEHS, walk and
  drive-time polygons. Tells you who can reasonably reach LEHS for events,
  conferences, and after-school programs.
"""
)
