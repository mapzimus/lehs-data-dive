"""
Reusable map helpers for the dashboard's GIS pages.

Uses Plotly Express mapbox functions with the OpenStreetMap tile style
(no API key required).
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.charts import LEHS_GOLD, LEHS_NAVY

# Lynn approximate centroid
LYNN_CENTER = {"lat": 42.4668, "lon": -70.9495}
MA_CENTER = {"lat": 42.25, "lon": -71.8}

DEFAULT_MAP_HEIGHT = 600

# Clean cartographic style — light gray background, town outlines visible,
# no topography/ocean depth/POI clutter from OSM.
# Other options: "white-bg" (totally blank), "carto-darkmatter" (dark mode).
# Note: 'height' deliberately NOT included so callers can override per page.
DEFAULT_MAP_LAYOUT = dict(
    mapbox_style="carto-positron",
    margin=dict(l=0, r=0, t=40, b=0),
    font=dict(family="sans-serif", size=12, color="#0A1F44"),
)


def school_points_map(
    df: pd.DataFrame,
    *,
    lat: str = "lat",
    lon: str = "lon",
    size: str | None = None,
    color: str | None = None,
    color_continuous_scale: str = "Viridis",
    hover_name: str | None = None,
    hover_data: dict | list | None = None,
    title: str = "",
    zoom: int = 12,
    center: dict = LYNN_CENTER,
    highlight: dict | None = None,
) -> go.Figure:
    """Scatter map of school points. `highlight` is {'col': col_name, 'value': value}."""
    plot_df = df.copy()
    if highlight:
        plot_df["_highlight"] = plot_df[highlight["col"]] == highlight["value"]
        color_arg = "_highlight"
        color_map = {True: LEHS_GOLD, False: LEHS_NAVY}
        fig = px.scatter_mapbox(
            plot_df, lat=lat, lon=lon, color=color_arg,
            color_discrete_map=color_map,
            size=size, hover_name=hover_name, hover_data=hover_data,
            zoom=zoom, center=center, title=title,
        )
    else:
        fig = px.scatter_mapbox(
            plot_df, lat=lat, lon=lon,
            color=color, color_continuous_scale=color_continuous_scale,
            size=size, hover_name=hover_name, hover_data=hover_data,
            zoom=zoom, center=center, title=title,
        )
    fig.update_layout(**DEFAULT_MAP_LAYOUT)
    return fig


def choropleth_map(
    df: pd.DataFrame,
    geojson: dict,
    *,
    locations: str,            # column in df matching feature ID
    featureidkey: str,         # path in geojson, e.g. "properties.GEOID"
    color: str,
    color_continuous_scale: str = "Viridis",
    range_color: tuple | None = None,
    hover_name: str | None = None,
    hover_data: dict | list | None = None,
    title: str = "",
    zoom: int = 12,
    center: dict = LYNN_CENTER,
    opacity: float = 0.65,
) -> go.Figure:
    """Choropleth on map tiles. Use for census tracts, town polygons, district polygons."""
    fig = px.choropleth_mapbox(
        df, geojson=geojson, locations=locations, featureidkey=featureidkey,
        color=color, color_continuous_scale=color_continuous_scale,
        range_color=range_color,
        hover_name=hover_name, hover_data=hover_data,
        zoom=zoom, center=center, opacity=opacity, title=title,
    )
    fig.update_layout(**DEFAULT_MAP_LAYOUT)
    return fig


def add_outline_layer(fig: go.Figure, geojson: dict, color: str = "#0A1F44",
                       width: float = 2.5, opacity: float = 1.0) -> go.Figure:
    """Add a polygon-outline layer to a map (e.g., Lynn town boundary on top)."""
    if not fig.layout.mapbox.layers:
        fig.layout.mapbox.layers = []
    layers = list(fig.layout.mapbox.layers or [])
    layers.append({
        "source": geojson,
        "type": "line",
        "color": color,
        "line": {"width": width},
        "opacity": opacity,
    })
    fig.update_layout(mapbox_layers=layers)
    return fig


def lynn_school_marker_size(enrollment: float | None) -> float:
    """Scale enrollment to a reasonable marker size (8-30 range)."""
    if enrollment is None or pd.isna(enrollment):
        return 10
    # Lynn schools range from ~150 to ~2000 students
    return max(8, min(30, 8 + (float(enrollment) / 100)))
