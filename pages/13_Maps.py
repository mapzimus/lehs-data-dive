"""
Section 13 — Maps.

Consolidated map view with four tabs:
  1. Lynn Schools — every school in Lynn pinned, colored by metric
  2. Lynn Demographics — Census ACS tract choropleths with school overlay
  3. Massachusetts — statewide district choropleth, colored by chosen metric
  4. Gateway Cities — 26 gateway-city main HS pinned on the state map
"""

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
from utils.maps import DEFAULT_MAP_LAYOUT, LYNN_CENTER, MA_CENTER

st.set_page_config(page_title="Maps | LEHS", page_icon="🗺️", layout="wide")
sidebar_attribution()

st.title("Maps")
st.markdown(
    "Geographic views of Lynn schools, Lynn demographics, Massachusetts "
    "school districts statewide, and the 26 Gateway Cities."
)

# ---------------------------------------------------------------------------
# Shared data loads
# ---------------------------------------------------------------------------

schools = load_geodataframe("lynn_schools")
town_geo = load_geojson("lynn_town")
tracts_gdf = load_geodataframe("lynn_tracts")
tracts_geo = load_geojson("lynn_tracts")
ma_districts_geo = load_geojson("ma_districts_metrics")
ma_districts_gdf = load_geodataframe("ma_districts_metrics")
gateway_gdf = load_geodataframe("gateway_hs")

# Lynn town outline (used as the highlight layer in Lynn tabs)
lynn_outline = None
if town_geo.get("features"):
    lynn_outline = {
        "type": "FeatureCollection",
        "features": [
            f for f in town_geo["features"]
            if f["properties"].get("TOWN") == "LYNN"
        ],
    }

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_schools, tab_demos, tab_ma, tab_gateway = st.tabs([
    "🏫 Lynn Schools",
    "🏘️ Lynn Demographics",
    "🗺️ Massachusetts",
    "🏙️ Gateway Cities",
])

# ===========================================================================
# TAB 1 — Lynn Schools
# ===========================================================================

with tab_schools:
    st.header("All Schools in Lynn")
    st.markdown(
        "Each marker is a school inside Lynn city limits, including private "
        "and charter schools (not just Lynn Public Schools). LEHS is "
        "highlighted in gold by default."
    )

    if schools.empty:
        st.warning("Lynn schools GeoJSON not built. Run `scripts/09` + `scripts/11`.")
    else:
        # Compute concentrated need
        need_df = schools.copy()
        for col in ["EL_PCT", "LI_PCT", "SWD_PCT"]:
            need_df[col] = pd.to_numeric(need_df[col], errors="coerce")
        need_df["need_index"] = need_df[["EL_PCT", "LI_PCT", "SWD_PCT"]].mean(axis=1)
        need_df["is_lehs"] = need_df["ORG_CODE"].astype(str).str.zfill(8) == "01630510"
        need_df["marker_size"] = (need_df["TOTAL_CNT"].fillna(200) / 80).clip(8, 30)

        color_choice = st.selectbox(
            "Color schools by",
            options=["LEHS vs. others", "Need Index (ELL + LI + SPED)", "% English Learner",
                     "% Low Income", "Total enrollment"],
            key="lynn_schools_color",
        )

        if color_choice == "LEHS vs. others":
            need_df["label"] = need_df["is_lehs"].map({True: "Lynn English High", False: "Other Lynn school"})
            fig = px.scatter_mapbox(
                need_df, lat="lat", lon="lon", color="label",
                color_discrete_map={"Lynn English High": LEHS_GOLD, "Other Lynn school": LEHS_NAVY},
                size="marker_size", size_max=30,
                hover_name="NAME",
                hover_data={"TYPE_DESC": True, "GRADES": True, "TOTAL_CNT": ":,",
                            "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                            "lat": False, "lon": False, "marker_size": False,
                            "label": False, "is_lehs": False},
                zoom=12.5, center=LYNN_CENTER,
            )
        else:
            col_map = {
                "Need Index (ELL + LI + SPED)": ("need_index", "Reds"),
                "% English Learner": ("EL_PCT", "Greens"),
                "% Low Income": ("LI_PCT", "Purples"),
                "Total enrollment": ("TOTAL_CNT", "Blues"),
            }
            col, scale = col_map[color_choice]
            plot = need_df.dropna(subset=[col]).copy()
            fig = px.scatter_mapbox(
                plot, lat="lat", lon="lon",
                color=col, color_continuous_scale=scale,
                size="marker_size", size_max=30,
                hover_name="NAME",
                hover_data={"TYPE_DESC": True, "TOTAL_CNT": ":,",
                            "EL_PCT": ":.0%", "LI_PCT": ":.0%", "SWD_PCT": ":.0%",
                            "need_index": ":.0%",
                            "lat": False, "lon": False, "marker_size": False},
                zoom=12.5, center=LYNN_CENTER,
            )

        # Lynn outline + carto-positron clean basemap
        layers = []
        if lynn_outline:
            layers.append({"source": lynn_outline, "type": "line", "color": LEHS_NAVY,
                           "line": {"width": 3}, "opacity": 1.0})
        fig.update_layout(**DEFAULT_MAP_LAYOUT, height=600, mapbox_layers=layers)
        st.plotly_chart(fig, width="stretch")

        # School table
        st.subheader("Lynn schools — full list")
        cols = ["NAME", "TYPE_DESC", "GRADES", "TOTAL_CNT", "EL_PCT", "LI_PCT"]
        cols = [c for c in cols if c in schools.columns]
        tbl = schools[cols].rename(columns={
            "NAME": "School", "TYPE_DESC": "Type", "GRADES": "Grades",
            "TOTAL_CNT": "Enrollment", "EL_PCT": "% ELL", "LI_PCT": "% Low Income",
        })
        if "Enrollment" in tbl:
            tbl["Enrollment"] = tbl["Enrollment"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—"
            )
        for c in ["% ELL", "% Low Income"]:
            if c in tbl:
                tbl[c] = tbl[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
        st.dataframe(tbl.sort_values("School"), width="stretch", hide_index=True)

# ===========================================================================
# TAB 2 — Lynn Demographics
# ===========================================================================

with tab_demos:
    st.header("Lynn — Census Tract Demographics")
    st.markdown(
        "Each of Lynn's 22 census tracts colored by your chosen Census ACS "
        "5-year (2019–2023) indicator. Lynn school dots overlaid for context."
    )

    if tracts_gdf.empty:
        st.warning("Lynn tracts not built. Run `scripts/09` + `scripts/10` + `scripts/11`.")
    else:
        metric_choice = st.radio(
            "Indicator",
            options=[
                "% non-English at home",
                "Median household income",
                "% Foreign-born",
                "% with Bachelor's or higher",
                "% Severely rent-burdened",
            ],
            horizontal=True,
            key="lynn_demos_metric",
        )

        metric_map = {
            "% non-English at home":     ("non_english_pct",         "Greens",  (0, 0.6),  "{:.0%}"),
            "Median household income":   ("median_household_income", "Greens",  None,       "${:,.0f}"),
            "% Foreign-born":            ("foreign_born_pct",        "Purples", (0, 0.6),  "{:.0%}"),
            "% with Bachelor's or higher":("bachelors_or_higher_pct","Blues",   (0, 0.7),  "{:.0%}"),
            "% Severely rent-burdened":  ("severe_burden_pct",       "Reds",    (0, 0.7),  "{:.0%}"),
        }
        col, scale, rng, fmt = metric_map[metric_choice]

        if col not in tracts_gdf.columns:
            st.warning(f"Column `{col}` not present.")
        else:
            plot = tracts_gdf.copy()
            plot[col] = pd.to_numeric(plot[col], errors="coerce")
            plot = plot.dropna(subset=[col])
            plot["NAMELSAD"] = plot["NAMELSAD"].astype(str)
            plot["display"] = plot[col].apply(lambda x: fmt.format(x))

            fig = px.choropleth_mapbox(
                plot, geojson=tracts_geo,
                locations="GEOID", featureidkey="properties.GEOID",
                color=col, color_continuous_scale=scale, range_color=rng,
                hover_name="NAMELSAD",
                hover_data={"GEOID": False, "display": True, col: False},
                zoom=12, center=LYNN_CENTER, opacity=0.7,
                labels={col: metric_choice},
            )

            # Add school dots on top
            if not schools.empty:
                school_pts = schools.dropna(subset=["lat", "lon"]).copy()
                school_pts["is_lehs"] = school_pts["ORG_CODE"].astype(str).str.zfill(8) == "01630510"
                fig.add_trace(go.Scattermapbox(
                    lat=school_pts["lat"], lon=school_pts["lon"],
                    mode="markers",
                    marker=dict(
                        size=[16 if l else 8 for l in school_pts["is_lehs"]],
                        color=[LEHS_GOLD if l else LEHS_NAVY for l in school_pts["is_lehs"]],
                        opacity=0.9,
                    ),
                    hovertext=school_pts["NAME"],
                    hoverinfo="text",
                    name="Lynn schools",
                    showlegend=False,
                ))

            layers = []
            if lynn_outline:
                layers.append({"source": lynn_outline, "type": "line", "color": LEHS_NAVY,
                               "line": {"width": 2.5}, "opacity": 1.0})
            fig.update_layout(**DEFAULT_MAP_LAYOUT, height=600, mapbox_layers=layers)
            st.plotly_chart(fig, width="stretch")

            # Quick stats
            vals = plot[col].dropna()
            c1, c2, c3, c4 = st.columns(4)
            with c1: st.metric("Tracts shown", f"{len(vals)}")
            with c2: st.metric("Min", fmt.format(vals.min()))
            with c3: st.metric("Median", fmt.format(vals.median()))
            with c4: st.metric("Max", fmt.format(vals.max()))

            st.caption(
                "**Note**: tract-level Census language data is collapsed into 13 "
                "categories. Granular B16001 (Khmer, Portuguese, etc.) is suppressed "
                "at tract resolution by Census for privacy."
            )

# ===========================================================================
# TAB 3 — Massachusetts
# ===========================================================================

with tab_ma:
    st.header("Massachusetts School Districts")
    st.markdown(
        "Every Massachusetts public school district as a polygon, colored by "
        "your chosen indicator. Lynn Public Schools is outlined in gold."
    )

    if ma_districts_gdf.empty or not ma_districts_geo.get("features"):
        st.warning("MA districts GeoJSON not built. Run `scripts/09` + `scripts/11`.")
    else:
        ma_metric_choice = st.selectbox(
            "Color districts by",
            options=[
                "4-year graduation rate",
                "Per-pupil spending",
                "% English Learner",
                "% Low Income",
                "% High Needs",
                "Total enrollment",
            ],
            key="ma_districts_metric",
        )

        ma_metric_map = {
            "4-year graduation rate": ("grad_4yr",  "Viridis",  "{:.0%}"),
            "Per-pupil spending":     ("per_pupil", "Viridis",  "${:,.0f}"),
            "% English Learner":      ("EL_PCT",    "Greens",   "{:.0%}"),
            "% Low Income":           ("LI_PCT",    "Reds",     "{:.0%}"),
            "% High Needs":           ("HN_PCT",    "Purples",  "{:.0%}"),
            "Total enrollment":       ("TOTAL_CNT", "Blues",    "{:,.0f}"),
        }
        ma_col, ma_scale, ma_fmt = ma_metric_map[ma_metric_choice]

        # Build plot DF: filter to operating districts and drop nulls for the metric
        plot_ma = ma_districts_gdf.copy()
        if "TYPE" in plot_ma.columns:
            # The shapefile has districts AND charter collaborative polygons (CCUVs).
            # Operating Districts are the real school districts.
            plot_ma = plot_ma[plot_ma["TYPE"].isin(["Operating District", "Public District"])]
        plot_ma[ma_col] = pd.to_numeric(plot_ma[ma_col], errors="coerce")
        plot_ma = plot_ma.dropna(subset=[ma_col])

        if plot_ma.empty:
            st.warning(f"No districts have data for '{ma_metric_choice}'.")
        else:
            plot_ma["DIST_NAME"] = plot_ma["DIST_NAME"].fillna("(unnamed)")
            plot_ma["display_value"] = plot_ma[ma_col].apply(
                lambda x: ma_fmt.format(x) if pd.notna(x) else "—"
            )
            # Pre-format secondary hover fields so missing values render as "—"
            for c, formatter in [
                ("TOTAL_CNT", lambda x: f"{int(x):,}" if pd.notna(x) else "—"),
                ("EL_PCT",    lambda x: f"{x:.0%}" if pd.notna(x) else "—"),
                ("LI_PCT",    lambda x: f"{x:.0%}" if pd.notna(x) else "—"),
            ]:
                if c in plot_ma.columns:
                    plot_ma[f"{c}_disp"] = plot_ma[c].apply(formatter)

            fig = px.choropleth_mapbox(
                plot_ma, geojson=ma_districts_geo,
                locations="ORG8CODE", featureidkey="properties.ORG8CODE",
                color=ma_col, color_continuous_scale=ma_scale,
                hover_name="DIST_NAME",
                hover_data={
                    "ORG8CODE": False, ma_col: False,
                    "display_value": True,
                    "TOTAL_CNT_disp": True if "TOTAL_CNT_disp" in plot_ma.columns else False,
                    "EL_PCT_disp": True if "EL_PCT_disp" in plot_ma.columns else False,
                    "LI_PCT_disp": True if "LI_PCT_disp" in plot_ma.columns else False,
                },
                zoom=7.5, center=MA_CENTER, opacity=0.7,
                labels={
                    "display_value": ma_metric_choice,
                    "TOTAL_CNT_disp": "Enrollment",
                    "EL_PCT_disp": "% ELL",
                    "LI_PCT_disp": "% Low Income",
                },
            )

            # Outline Lynn district in gold
            lynn_feature = {
                "type": "FeatureCollection",
                "features": [
                    f for f in ma_districts_geo["features"]
                    if f["properties"].get("ORG8CODE") == "01630000"
                ],
            }
            if lynn_feature["features"]:
                fig.update_layout(mapbox_layers=[{
                    "source": lynn_feature, "type": "line", "color": LEHS_GOLD,
                    "line": {"width": 4}, "opacity": 1.0,
                }])

            fig.update_layout(**DEFAULT_MAP_LAYOUT, height=650)
            st.plotly_chart(fig, width="stretch")

            # LEHS callout
            lynn_row = plot_ma[plot_ma["ORG8CODE"] == "01630000"]
            if not lynn_row.empty:
                val = lynn_row.iloc[0][ma_col]
                state_median = plot_ma[ma_col].median()
                if pd.notna(val) and pd.notna(state_median):
                    diff = val - state_median
                    # Convert to friendly delta text
                    if ma_col.endswith("_PCT") or ma_col == "grad_4yr":
                        delta_text = f"{diff * 100:+.1f} pts vs MA median ({state_median:.0%})"
                    elif ma_col == "per_pupil":
                        delta_text = f"{diff:+,.0f} vs MA median (${state_median:,.0f})"
                    else:
                        delta_text = f"{diff:+,.0f} vs MA median ({state_median:,.0f})"
                    st.info(
                        f"**Lynn Public Schools** (gold outline): {ma_fmt.format(val)}  "
                        f"·  {delta_text}"
                    )

            # Top / bottom 5 (smaller than before to keep page tight)
            def _make_table(df_in: pd.DataFrame) -> pd.DataFrame:
                base = ["DIST_NAME"]
                if ma_col not in ["TOTAL_CNT", "EL_PCT", "LI_PCT"]:
                    base.append(ma_col)
                base += ["TOTAL_CNT", "EL_PCT", "LI_PCT"]
                out = df_in[base].copy()
                if ma_col in out.columns and ma_col != "TOTAL_CNT":
                    out[ma_col] = out[ma_col].apply(lambda x: ma_fmt.format(x) if pd.notna(x) else "—")
                out["TOTAL_CNT"] = out["TOTAL_CNT"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
                out["EL_PCT"] = out["EL_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
                out["LI_PCT"] = out["LI_PCT"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
                rename = {"DIST_NAME": "District", "TOTAL_CNT": "Enrollment",
                          "EL_PCT": "% ELL", "LI_PCT": "% Low Income"}
                if ma_col not in rename:
                    rename[ma_col] = ma_metric_choice
                return out.rename(columns=rename)

            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Top 5 — {ma_metric_choice}**")
                st.dataframe(
                    _make_table(plot_ma.nlargest(5, ma_col)),
                    width="stretch", hide_index=True,
                )
            with c2:
                st.markdown(f"**Bottom 5 — {ma_metric_choice}**")
                st.dataframe(
                    _make_table(plot_ma.nsmallest(5, ma_col)),
                    width="stretch", hide_index=True,
                )

            st.caption(
                f"Showing **{len(plot_ma)}** Operating Districts statewide that "
                f"have data for `{ma_col}` (excludes collaboratives and charter "
                f"resource polygons)."
            )

# ===========================================================================
# TAB 4 — Gateway Cities
# ===========================================================================

with tab_gateway:
    st.header("Gateway Cities")
    st.markdown(
        "The 26 Massachusetts Gateway Cities — state-designated post-industrial "
        "cities with high need and high potential. Each city's main "
        "comprehensive HS is pinned. Lynn highlighted in gold."
    )

    if gateway_gdf.empty:
        st.warning("Gateway HS GeoJSON not built. Run `scripts/09` + `scripts/11`.")
    else:
        # Enrich with current-year enrollment for hover/sorting
        peers_path = PROCESSED_DIR / "_peer_schools.json"
        peers = json.loads(peers_path.read_text()) if peers_path.exists() else {}

        enr = load_dataset("enrollment_demographics")
        latest_enr = (
            enr.sort_values("SY").groupby("ORG_CODE").tail(1)[
                ["ORG_CODE", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HL_PCT"]
            ] if not enr.empty else pd.DataFrame()
        )
        if not latest_enr.empty:
            latest_enr["ORG_CODE"] = latest_enr["ORG_CODE"].astype(str).str.zfill(8)

        g = gateway_gdf.copy()
        g["school_code_dese"] = g["school_code_dese"].astype(str).str.zfill(8)
        if not latest_enr.empty:
            g = g.merge(
                latest_enr.rename(columns={"ORG_CODE": "school_code_dese"}),
                on="school_code_dese", how="left",
            )
        g["is_lehs"] = g["school_code_dese"] == "01630510"
        g["label"] = g["is_lehs"].map({True: "Lynn English High", False: "Other Gateway HS"})
        g["marker_size"] = (g.get("TOTAL_CNT", pd.Series([500] * len(g))).fillna(500) / 100).clip(10, 40)

        color_choice = st.selectbox(
            "Color the gateway HS by",
            options=["LEHS vs others", "% English Learner", "% Low Income", "Total enrollment"],
            key="gateway_color",
        )

        if color_choice == "LEHS vs others":
            fig = px.scatter_mapbox(
                g, lat="lat", lon="lon",
                color="label",
                color_discrete_map={"Lynn English High": LEHS_GOLD, "Other Gateway HS": LEHS_NAVY},
                size="marker_size", size_max=40, text="city",
                hover_name="NAME",
                hover_data={"city": True, "TOTAL_CNT": ":,",
                            "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                            "lat": False, "lon": False, "marker_size": False, "label": False},
                zoom=7, center=MA_CENTER,
            )
        else:
            col_map = {
                "% English Learner": "EL_PCT",
                "% Low Income":      "LI_PCT",
                "Total enrollment":  "TOTAL_CNT",
            }
            cname = col_map[color_choice]
            plot = g.dropna(subset=[cname]).copy()
            fig = px.scatter_mapbox(
                plot, lat="lat", lon="lon",
                color=cname, color_continuous_scale="Viridis",
                size="marker_size", size_max=40, text="city",
                hover_name="NAME",
                hover_data={"city": True, "TOTAL_CNT": ":,",
                            "EL_PCT": ":.0%", "LI_PCT": ":.0%",
                            "lat": False, "lon": False, "marker_size": False},
                zoom=7, center=MA_CENTER,
            )

        fig.update_traces(textposition="top center", textfont=dict(size=10))
        fig.update_layout(**DEFAULT_MAP_LAYOUT, height=600)
        st.plotly_chart(fig, width="stretch")

        # Scorecard table
        st.subheader("All 26 Gateway HS — at a glance")
        cols = ["city", "NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HL_PCT"]
        cols = [c for c in cols if c in g.columns]
        tbl = g[cols].rename(columns={
            "city": "City", "NAME": "School", "TOTAL_CNT": "Enrollment",
            "EL_PCT": "% ELL", "LI_PCT": "% Low Income", "HL_PCT": "% Hispanic/Latino",
        })
        if "Enrollment" in tbl:
            tbl["Enrollment"] = tbl["Enrollment"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—"
            )
        for c in ["% ELL", "% Low Income", "% Hispanic/Latino"]:
            if c in tbl:
                tbl[c] = tbl[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

        def _highlight_lynn(row):
            return ["background-color: #FFF4D6"] * len(row) if row.get("City") == "Lynn" else [""] * len(row)

        if "City" in tbl:
            st.dataframe(
                tbl.sort_values("City").style.apply(_highlight_lynn, axis=1),
                width="stretch", hide_index=True,
            )
        else:
            st.dataframe(tbl, width="stretch", hide_index=True)
