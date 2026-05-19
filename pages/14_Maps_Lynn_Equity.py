"""Section 14 — Lynn Equity Maps: tract-level ACS demographics + school-level need."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import LEHS_GOLD, LEHS_NAVY
from utils.geo_loader import load_geojson, load_geodataframe
from utils.maps import DEFAULT_MAP_LAYOUT, LYNN_CENTER

st.set_page_config(
    page_title="Maps — Lynn Equity | LEHS", page_icon="🗺️", layout="wide"
)
sidebar_attribution()

st.title("Lynn Equity Maps")
st.markdown(
    "Where need lives in Lynn, geographically — combining Census ACS tract-level "
    "demographics with school-level need indicators."
)

schools = load_geodataframe("lynn_schools")
tracts_gdf = load_geodataframe("lynn_tracts")
tracts_json = load_geojson("lynn_tracts")
town = load_geojson("lynn_town")

if schools.empty or tracts_gdf.empty:
    st.warning("Lynn GIS data not yet built.")
    st.stop()

# Lynn town outline for overlay
lynn_outline = None
if town.get("features"):
    lynn_outline = {
        "type": "FeatureCollection",
        "features": [f for f in town["features"] if f["properties"].get("TOWN") == "LYNN"],
    }

# Lynn schools as points layer
lps_schools = schools[
    schools["DIST_NAME"].astype(str).str.contains("Lynn", case=False, na=False)
].copy() if "DIST_NAME" in schools.columns else schools

# ---------------------------------------------------------------------------
# Tab interface for different choropleths
# ---------------------------------------------------------------------------

tab_econ, tab_lang, tab_school, tab_combo = st.tabs([
    "💰 Economic / housing",
    "🌐 Linguistic landscape",
    "🏫 School-level need",
    "🔗 Combined view",
])

# ---------------------------------------------------------------------------
# TAB 1: Economic + housing
# ---------------------------------------------------------------------------

with tab_econ:
    st.subheader("Economic & Housing Indicators — Lynn Census Tracts")

    metric_choice = st.radio(
        "Show",
        options=[
            "Median household income",
            "% Foreign-born",
            "% with Bachelor's or higher",
            "% Severely rent-burdened (30%+ income)",
        ],
        horizontal=True,
    )

    metric_map = {
        "Median household income":               ("median_household_income", "Greens",  "${:,.0f}",  None,           False),
        "% Foreign-born":                        ("foreign_born_pct",        "Purples", "{:.0%}",    (0, 0.6),       False),
        "% with Bachelor's or higher":           ("bachelors_or_higher_pct", "Blues",   "{:.0%}",    (0, 0.7),       False),
        "% Severely rent-burdened (30%+ income)":("severe_burden_pct",       "Reds",    "{:.0%}",    (0, 0.7),       False),
    }
    col, scale, fmt, rng, _ = metric_map[metric_choice]

    if col not in tracts_gdf.columns:
        st.warning(f"Column {col} not present in tract data.")
    else:
        plot_df = tracts_gdf.copy()
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")
        plot_df = plot_df.dropna(subset=[col])
        plot_df["display"] = plot_df[col].apply(lambda x: fmt.format(x) if pd.notna(x) else "—")
        plot_df["NAMELSAD"] = plot_df["NAMELSAD"].astype(str)

        fig = px.choropleth_mapbox(
            plot_df, geojson=tracts_json,
            locations="GEOID", featureidkey="properties.GEOID",
            color=col, color_continuous_scale=scale,
            range_color=rng,
            hover_name="NAMELSAD",
            hover_data={"GEOID": False, "display": True, col: False},
            zoom=12, center=LYNN_CENTER, opacity=0.7,
            labels={col: metric_choice},
        )
        if lynn_outline:
            fig.update_layout(mapbox_layers=[{
                "source": lynn_outline, "type": "line", "color": LEHS_NAVY,
                "line": {"width": 3}, "opacity": 1.0,
            }])
        fig.update_layout(**DEFAULT_MAP_LAYOUT, height=550)
        st.plotly_chart(fig, width="stretch")

        # Stats
        vals = plot_df[col].dropna()
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("Tracts shown", f"{len(vals)}")
        with c2: st.metric("Min", fmt.format(vals.min()))
        with c3: st.metric("Median", fmt.format(vals.median()))
        with c4: st.metric("Max", fmt.format(vals.max()))

# ---------------------------------------------------------------------------
# TAB 2: Linguistic landscape
# ---------------------------------------------------------------------------

with tab_lang:
    st.subheader("Linguistic Landscape — Lynn Census Tracts")

    if "non_english_pct" not in tracts_gdf.columns:
        st.warning("Language data not loaded. Run scripts/10 + 11.")
    else:
        st.caption(
            "Share of Lynn residents (age 5+) who speak a language other than English at home. "
            "Spanish is the dominant non-English language across every Lynn tract — "
            "but the share varies dramatically (10% to 50%+ depending on neighborhood)."
        )

        plot_df = tracts_gdf.copy()
        # Force numeric — GeoJSON round-trip can preserve as strings
        plot_df["non_english_pct"] = pd.to_numeric(plot_df["non_english_pct"], errors="coerce")
        plot_df["dominant_non_english_count"] = pd.to_numeric(
            plot_df["dominant_non_english_count"], errors="coerce"
        )
        plot_df["lang_total"] = pd.to_numeric(plot_df["lang_total"], errors="coerce")
        plot_df = plot_df.dropna(subset=["non_english_pct"])
        plot_df["NAMELSAD"] = plot_df["NAMELSAD"].astype(str)
        plot_df["display_pct"] = plot_df["non_english_pct"].apply(lambda x: f"{x:.0%}")
        plot_df["display_count"] = plot_df["dominant_non_english_count"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "—"
        )

        fig = px.choropleth_mapbox(
            plot_df, geojson=tracts_json,
            locations="GEOID", featureidkey="properties.GEOID",
            color="non_english_pct", color_continuous_scale="Greens",
            range_color=(0, 0.6),
            hover_name="NAMELSAD",
            hover_data={"GEOID": False, "display_pct": True, "dominant_non_english": True,
                        "display_count": True, "non_english_pct": False,
                        "dominant_non_english_count": False},
            zoom=12, center=LYNN_CENTER, opacity=0.7,
            labels={"non_english_pct": "% non-English at home"},
        )
        if lynn_outline:
            fig.update_layout(mapbox_layers=[{
                "source": lynn_outline, "type": "line", "color": LEHS_NAVY,
                "line": {"width": 3}, "opacity": 1.0,
            }])
        fig.update_layout(**DEFAULT_MAP_LAYOUT, height=550)
        st.plotly_chart(fig, width="stretch")

        # Top tracts by non-English share
        top_tracts = plot_df.nlargest(5, "non_english_pct")[
            ["NAMELSAD", "non_english_pct", "dominant_non_english_count", "lang_total"]
        ].copy()
        top_tracts["% non-English"] = top_tracts["non_english_pct"].apply(lambda x: f"{x:.0%}")
        top_tracts["Spanish speakers"] = top_tracts["dominant_non_english_count"].apply(
            lambda x: f"{int(x):,}"
        )
        top_tracts["Total pop 5+"] = top_tracts["lang_total"].apply(
            lambda x: f"{int(x):,}"
        )
        st.markdown("**Top 5 Lynn tracts by share speaking a non-English language**")
        st.dataframe(
            top_tracts[["NAMELSAD", "Total pop 5+", "Spanish speakers", "% non-English"]].rename(
                columns={"NAMELSAD": "Tract"}
            ),
            width="stretch", hide_index=True,
        )

        st.info(
            "**Note**: Tract-level Census language data is collapsed into 13 categories "
            "(Spanish, French/Haitian, Russian/Slavic, Chinese, Vietnamese, Tagalog, Arabic, etc.). "
            "The more granular B16001 table (with Khmer/Cambodian, Portuguese, etc. broken out) "
            "is suppressed at tract resolution by the Census Bureau for privacy reasons."
        )

# ---------------------------------------------------------------------------
# TAB 3: School-level need
# ---------------------------------------------------------------------------

with tab_school:
    st.subheader("Concentrated Need by Lynn School")
    st.caption(
        "Need Index = average of (% ELL, % Low Income, % SPED). "
        "Higher = more concentrated student need."
    )

    need_df = schools.copy()
    for col in ["EL_PCT", "LI_PCT", "SWD_PCT"]:
        need_df[col] = pd.to_numeric(need_df[col], errors="coerce")
    need_df["need_index"] = need_df[["EL_PCT", "LI_PCT", "SWD_PCT"]].mean(axis=1)
    need_df = need_df.dropna(subset=["need_index"])
    need_df["marker_size"] = (need_df["TOTAL_CNT"].fillna(200) / 80).clip(8, 30)

    fig = px.scatter_mapbox(
        need_df, lat="lat", lon="lon",
        color="need_index", color_continuous_scale="Reds",
        size="marker_size", size_max=30,
        hover_name="NAME",
        hover_data={"TOTAL_CNT": ":,", "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                    "SWD_PCT": ":.0%", "need_index": ":.0%",
                    "lat": False, "lon": False, "marker_size": False},
        zoom=12.5, center=LYNN_CENTER,
        labels={"need_index": "Need Index"},
    )
    if lynn_outline:
        fig.update_layout(mapbox_layers=[{
            "source": lynn_outline, "type": "line", "color": LEHS_NAVY,
            "line": {"width": 2.5},
        }])
    fig.update_layout(**DEFAULT_MAP_LAYOUT, height=550)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# TAB 4: Combined — schools on top of tracts
# ---------------------------------------------------------------------------

with tab_combo:
    st.subheader("Schools Overlaid on Community Context")
    st.caption(
        "Tract choropleth = Census ACS demographic. School dots = Lynn schools "
        "colored by need index. Lets you see how school-level need aligns "
        "(or doesn't) with neighborhood demographics."
    )

    bg_choice = st.selectbox(
        "Background (tract choropleth)",
        options=["% non-English at home", "Median household income",
                 "% Foreign-born", "% Bachelor's or higher"],
    )

    bg_map = {
        "% non-English at home":      ("non_english_pct",         "Greens",  (0, 0.6)),
        "Median household income":    ("median_household_income", "Greens",  None),
        "% Foreign-born":             ("foreign_born_pct",        "Purples", (0, 0.6)),
        "% Bachelor's or higher":     ("bachelors_or_higher_pct", "Blues",   (0, 0.7)),
    }
    col, scale, rng = bg_map[bg_choice]

    plot_tracts = tracts_gdf.copy()
    plot_tracts[col] = pd.to_numeric(plot_tracts[col], errors="coerce")
    plot_tracts = plot_tracts.dropna(subset=[col])

    fig = px.choropleth_mapbox(
        plot_tracts, geojson=tracts_json,
        locations="GEOID", featureidkey="properties.GEOID",
        color=col, color_continuous_scale=scale,
        range_color=rng,
        hover_name="NAMELSAD",
        zoom=12, center=LYNN_CENTER, opacity=0.55,
        labels={col: bg_choice},
    )

    # School dots
    need_df = schools.copy()
    for c in ["EL_PCT", "LI_PCT", "SWD_PCT"]:
        need_df[c] = pd.to_numeric(need_df[c], errors="coerce")
    need_df["need_index"] = need_df[["EL_PCT", "LI_PCT", "SWD_PCT"]].mean(axis=1)
    need_df = need_df.dropna(subset=["need_index", "lat", "lon"])

    fig.add_trace(go.Scattermapbox(
        lat=need_df["lat"], lon=need_df["lon"],
        mode="markers",
        marker=dict(
            size=(need_df["TOTAL_CNT"].fillna(200) / 80).clip(8, 24),
            color=need_df["need_index"], colorscale="Reds",
            showscale=False, opacity=0.95,
            allowoverlap=True,
        ),
        hovertext=need_df["NAME"] + "<br>Need: " + need_df["need_index"].apply(lambda x: f"{x:.0%}"),
        hoverinfo="text",
        name="Schools (sized = enrollment, color = need)",
    ))

    fig.update_layout(**DEFAULT_MAP_LAYOUT, height=600)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Lynn's neighbors comparison
# ---------------------------------------------------------------------------

st.header("Lynn in the Region")
st.caption(
    "Lynn (median household income ~$73k, ~25% foreign-born) sits next to "
    "Swampscott (~$120k, ~12% foreign-born), Lynnfield, and Saugus — towns "
    "with dramatically different demographic profiles. The school district "
    "boundary is a sharp demographic line. The [MA Districts](/Maps_MA_Districts) "
    "page shows this regional contrast at statewide scale."
)
