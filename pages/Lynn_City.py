"""
Lynn — City page.

Two tabs covering Lynn the place (not just the schools):
  - Citywide      — demographics, economy, housing, geography, history at
                    the city scale. ACS place-level + decennial Census.
  - Neighborhoods — Census ACS at tract level (Lynn's 22 census tracts),
                    plus EPA EJScreen + CDC PLACES community-health layers.

Merged in reorg Phase 2 from former pages 19_Lynn_Overview.py and
9_Community_Context.py. All content preserved; cross-page link copy
updated to reflect the new parent-page layout.
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, data_downloads_panel
from utils.constants import LEHS_SCHOOL_CODE, PROCESSED_DIR
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="Lynn City | LEHS", page_icon="🏙️", layout="wide",
)
sidebar_attribution()

st.title("Lynn, Massachusetts — City")
st.markdown(
    "A wider community view of the city Lynn English serves. Where the rest "
    "of this dashboard tracks the school, this page tracks **the place**. "
    "**Citywide** is the rolled-up city profile (demographics, economy, "
    "housing, history). **Neighborhoods** drops to Lynn's 22 census tracts "
    "and the environmental + health layers that vary across them."
)

tab_city, tab_nbhds = st.tabs(["Citywide", "Neighborhoods"])

# ===========================================================================
# TAB 1 — CITYWIDE (former 19_Lynn_Overview.py)
# ===========================================================================

with tab_city:
    # -----------------------------------------------------------------------
    # Load data
    # -----------------------------------------------------------------------
    city = load_dataset("lynn_city_stats")
    birthplaces = load_dataset("lynn_birthplaces")
    languages = load_dataset("lynn_languages")
    industries = load_dataset("lynn_industries")
    commute = load_dataset("lynn_commute")
    age_pyramid = load_dataset("lynn_age_pyramid")

    if city.empty:
        st.info(
            "Lynn city-level Census data isn't loaded yet. Run "
            "`python scripts/14_download_lynn_city_stats.py` (Census API key required)."
        )
    else:
        row = city.iloc[0]

        def _num(col, default=None):
            v = row.get(col)
            if v is None or pd.isna(v):
                return default
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        def _fmt_money(v):
            return f"${v:,.0f}" if v is not None else "—"

        def _fmt_pct(v):
            return f"{v:.1f}%" if v is not None else "—"

        # -------------------------------------------------------------------
        # 1. Headline
        # -------------------------------------------------------------------
        st.header("Headline numbers")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Total population",
                      f"{int(_num('pop_total') or 0):,}",
                      help="US Census ACS 5-year 2019–2023, place-level estimate")
        with c2:
            st.metric("Median age", f"{_num('median_age'):.1f}" if _num('median_age') else "—")
        with c3:
            st.metric("Median household income", _fmt_money(_num("median_household_income")))
        with c4:
            st.metric("Foreign-born population",
                      f"{int(_num('foreign_born_total') or 0):,}",
                      delta=f"{(_num('foreign_born_total') or 0) / (_num('pop_total') or 1):.0%} of total",
                      delta_color="off")
        with c5:
            st.metric("Unemployment rate", _fmt_pct(_num("unemployment_rate")))

        st.caption(
            "**Lynn at a glance.** 10.8 sq mi of coastal city ~10 miles north of Boston. "
            "One of the most ethnically and linguistically diverse cities in New England. "
            "Founded 1629 — the fifth-oldest city in Massachusetts. Home to GE Aerospace's "
            "Lynn River Works (jet engines) and one of the largest municipal parks in the US "
            "(Lynn Woods Reservation, 2,200 acres)."
        )

        # -------------------------------------------------------------------
        # 2. Population over time (decadal census)
        # -------------------------------------------------------------------
        st.header("Population over time")
        st.caption(
            "Decadal US Census counts. Lynn grew explosively during the 19th-century "
            "shoe-manufacturing boom, peaked around 1930, contracted through the "
            "deindustrialization decades, then resumed growth in the 2000s driven "
            "by immigration."
        )
        decadal = pd.DataFrame({
            "year": [1790, 1800, 1810, 1820, 1830, 1840, 1850, 1860, 1870, 1880,
                     1890, 1900, 1910, 1920, 1930, 1940, 1950, 1960, 1970, 1980,
                     1990, 2000, 2010, 2020],
            "population": [2291, 2837, 4087, 4515, 6138, 9367, 14257, 19083, 28233, 38274,
                           55727, 68513, 89336, 99148, 102320, 98123, 99738, 94478, 90294, 78471,
                           81245, 89050, 90329, 101253],
        })
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=decadal["year"], y=decadal["population"],
                                  mode="lines+markers", line=dict(color=LEHS_NAVY, width=3),
                                  marker=dict(size=7)))
        fig.update_layout(**DEFAULT_LAYOUT,
                          yaxis_title="Total population",
                          xaxis_title="Decennial Census year")
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # 3. Age pyramid
        # -------------------------------------------------------------------
        st.header("Age + sex structure")
        if not age_pyramid.empty:
            band_order = ["0-4", "5-9", "10-14", "15-19", "20-24", "25-29", "30-34",
                          "35-39", "40-44", "45-49", "50-54", "55-59", "60-64",
                          "65-69", "70-74", "75-79", "80-84", "85+"]
            male = age_pyramid[age_pyramid["sex"] == "Male"].set_index("band").reindex(band_order)
            female = age_pyramid[age_pyramid["sex"] == "Female"].set_index("band").reindex(band_order)
            fig = go.Figure()
            fig.add_trace(go.Bar(y=band_order, x=-male["count"], orientation="h",
                                  name="Male", marker_color=LEHS_NAVY))
            fig.add_trace(go.Bar(y=band_order, x=female["count"], orientation="h",
                                  name="Female", marker_color=LEHS_GOLD))
            fig.update_layout(**DEFAULT_LAYOUT, barmode="overlay", bargap=0.05,
                               xaxis_title="Population (left = male, right = female)",
                               yaxis_title="Age band")
            # Symmetric ticks driven by the data. Round up to nearest 1K so
            # ticks land on clean numbers regardless of which band peaks.
            max_band = max(int(male["count"].max() or 0), int(female["count"].max() or 0))
            step = max(1000, ((max_band // 4) // 500 + 1) * 500)  # quarter-range, snapped to 500
            n = (max_band // step) + 1
            tickvals = [step * i for i in range(-n, n + 1)]
            ticktext = [f"{abs(v):,}" for v in tickvals]
            fig.update_xaxes(tickvals=tickvals, ticktext=ticktext,
                             range=[-step * (n + 0.2), step * (n + 0.2)])
            st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # 4. Race + ethnicity
        # -------------------------------------------------------------------
        st.header("Race + ethnicity")
        race_rows = [
            ("White (non-Hispanic)", _num("white_alone_nh")),
            ("Hispanic / Latino (any race)", _num("hispanic_any_race")),
            ("Black or African American (alone)", _num("black_alone")),
            ("Asian (alone)", _num("asian_alone")),
            ("Two or more races", _num("two_or_more")),
            ("Native Hawaiian / Pacific Islander", _num("nhpi_alone")),
            ("American Indian / Alaska Native", _num("amerindian_alone")),
            ("Other (alone)", _num("other_alone")),
        ]
        race_df = pd.DataFrame([(l, v) for l, v in race_rows if v and v > 0],
                               columns=["group", "count"])
        if not race_df.empty:
            race_df["share"] = race_df["count"] / race_df["count"].sum()
            race_df = race_df.sort_values("count", ascending=True)
            fig = px.bar(race_df, y="group", x="count", orientation="h",
                         color="group",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(**DEFAULT_LAYOUT, showlegend=False,
                              yaxis_title="", xaxis_title="People")
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Census reports race and Hispanic origin separately, so people may "
                "appear in multiple bars (e.g., Hispanic + White-alone). The "
                "*White, non-Hispanic* bar is the single mutually-exclusive Hispanic-excluded category."
            )

        # -------------------------------------------------------------------
        # 5. Foreign-born population + birthplaces
        # -------------------------------------------------------------------
        st.header("Foreign-born population — origins")
        fb_total = _num("foreign_born_total") or 0
        fb_nat = _num("foreign_born_naturalized") or 0
        pop_total = _num("pop_total") or 1

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Foreign-born total",
                      f"{int(fb_total):,}",
                      delta=f"{fb_total / pop_total:.0%} of Lynn", delta_color="off")
        with c2:
            st.metric("Naturalized citizens", f"{int(fb_nat):,}",
                      delta=f"{fb_nat / max(fb_total, 1):.0%} of foreign-born", delta_color="off")
        with c3:
            st.metric("Not yet naturalized", f"{int(fb_total - fb_nat):,}",
                      delta=f"{(fb_total - fb_nat) / max(fb_total, 1):.0%} of foreign-born",
                      delta_color="off")

        if not birthplaces.empty:
            is_roll = birthplaces["country"].str.contains("total", case=False, na=False)
            specific = birthplaces[~is_roll & (birthplaces["country"] != "Foreign-born total")]
            specific = specific.sort_values("count", ascending=True).tail(15)
            fig = px.bar(specific, y="country", x="count", orientation="h",
                         color="count", color_continuous_scale="Blues")
            fig.update_layout(**DEFAULT_LAYOUT, showlegend=False, height=520,
                              yaxis_title="", xaxis_title="Foreign-born residents",
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Lynn's Dominican community is the largest single national-origin group. "
                "Central American (Guatemalan, Salvadoran, Honduran) and Cambodian "
                "communities are also long-established. African-born population — "
                "particularly from Western Africa — has grown notably in recent ACS releases."
            )

        # -------------------------------------------------------------------
        # 6. Languages spoken at home
        # -------------------------------------------------------------------
        st.header("Languages spoken at home")
        st.caption(
            "Census ACS C16001 — population age 5+. Lynn's language diversity directly "
            "feeds the LEHS English Learner pipeline (see the ELL Pipeline page)."
        )
        if not languages.empty:
            lang_total_row = languages[languages["language"].str.contains("Total", case=False, na=False)]
            lang_total = int(lang_total_row["count"].iloc[0]) if not lang_total_row.empty else None

            lang_show = languages[~languages["language"].str.contains("Total", case=False, na=False)].copy()
            lang_show = lang_show.sort_values("count", ascending=True)
            fig = px.bar(lang_show, y="language", x="count", orientation="h",
                         color_discrete_sequence=[LEHS_NAVY])
            fig.update_layout(**DEFAULT_LAYOUT,
                              yaxis_title="", xaxis_title="Speakers")
            if lang_total:
                st.caption(f"Population age 5+: {lang_total:,}")
            st.plotly_chart(fig, use_container_width=True)

            if lang_total:
                eng = lang_show[lang_show["language"].str.contains("English", case=False, na=False)]["count"].sum()
                non_eng = lang_total - eng
                st.success(
                    f"**{non_eng:,} Lynn residents speak a language other than English at home** "
                    f"({non_eng / lang_total:.0%} of population 5+). Spanish is by far the largest, "
                    f"followed by Russian/Polish/Slavic and Arabic groups."
                )

        # -------------------------------------------------------------------
        # 7. Economy — income + poverty
        # -------------------------------------------------------------------
        st.header("Income, poverty, and inequality")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Median household income",
                      _fmt_money(_num("median_household_income")),
                      help="ACS 2019–2023 in 2023 inflation-adjusted dollars")
        with c2:
            st.metric("Mean household income", _fmt_money(_num("mean_household_income")))
        with c3:
            st.metric("Per capita income", _fmt_money(_num("per_capita_income")))
        with c4:
            st.metric("Overall poverty rate", _fmt_pct(_num("pov_rate_all_pct")))

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Child poverty rate (under 18)", _fmt_pct(_num("pov_rate_kids_under_18_pct")))
        with c2:
            st.metric("Health insurance coverage", _fmt_pct(_num("with_health_insurance_pct")))
        with c3:
            lf = _num("labor_force") or 0
            unemp = _num("unemployed") or 0
            st.metric("Civilian labor force", f"{int(lf):,}",
                      delta=f"Unemployed: {int(unemp):,}", delta_color="off")

        st.caption(
            "**Compared to MA state averages** (ACS 2023): MA median household income "
            "~$97,000 · MA poverty rate ~10% · MA child poverty ~12%. Lynn sits below "
            "state median income and above state poverty rates — a pattern shared across "
            "the 26 Gateway Cities."
        )

        # -------------------------------------------------------------------
        # 8. Employment by industry
        # -------------------------------------------------------------------
        st.header("Employment by industry")
        if not industries.empty:
            ind_sorted = industries.sort_values("employed", ascending=True)
            fig = px.bar(ind_sorted, y="industry", x="employed", orientation="h",
                         color="employed", color_continuous_scale="Blues")
            fig.update_layout(**DEFAULT_LAYOUT, height=480, showlegend=False,
                              yaxis_title="", xaxis_title="Lynn residents employed",
                              coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Largest single sector: **educational services + healthcare + social "
                "assistance** — characteristic of urban New England economies. "
                "Manufacturing remains substantial in Lynn (anchored by GE Aerospace's "
                "Lynn River Works jet-engine plant)."
            )

        st.subheader("Top employers in Lynn (curated, not exhaustive)")
        employers = pd.DataFrame([
            ("GE Aerospace — Lynn River Works",
             "Aerospace manufacturing (jet engines)", "~3,000–3,500"),
            ("Lynn Public Schools", "K-12 education (~16,000 students, ~2,400 staff)", "~2,400"),
            ("North Shore Medical Center / Mass General Brigham", "Healthcare", "~1,500+"),
            ("City of Lynn (municipal)", "Local government", "~1,000+"),
            ("Lynn Community Health Center", "Federally-Qualified Health Center (FQHC)", "~700"),
            ("North Shore Community College — Lynn campus", "Higher ed", "~250"),
            ("KIPP Academy Lynn Collegiate", "K-12 charter school", "~150"),
            ("Eastern Bank", "Regional bank HQ vicinity", "varies"),
        ], columns=["Employer", "Sector", "Approx Lynn employees"])
        st.dataframe(employers, use_container_width=True, hide_index=True)
        st.caption(
            "Sources: GE Aerospace public reporting, Lynn Public Schools workforce reports, "
            "MGB system filings, City of Lynn HR. Counts are approximate point-in-time as of "
            "early-2026 reporting cycles."
        )

        # -------------------------------------------------------------------
        # 9. Housing
        # -------------------------------------------------------------------
        st.header("Housing")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Total housing units", f"{int(_num('housing_units_total') or 0):,}")
        with c2:
            own = _num("owner_occupied") or 0
            rent = _num("renter_occupied") or 0
            total_occ = own + rent
            st.metric("% Owner-occupied", f"{own / max(total_occ, 1):.0%}",
                      delta=f"{int(own):,} units", delta_color="off")
        with c3:
            st.metric("Median home value", _fmt_money(_num("median_home_value")))
        with c4:
            st.metric("Median gross rent", _fmt_money(_num("median_gross_rent")))

        year_cols = [
            ("Built 2014 or later",    _num("built_2014_or_later")),
            ("Built 2010–2013",        _num("built_2010_to_2013")),
            ("Built 2000–2009",        _num("built_2000_to_2009")),
            ("Built 1990–1999",        _num("built_1990_to_1999")),
            ("Built 1980–1989",        _num("built_1980_to_1989")),
            ("Built 1970–1979",        _num("built_1970_to_1979")),
            ("Built 1960–1969",        _num("built_1960_to_1969")),
            ("Built 1950–1959",        _num("built_1950_to_1959")),
            ("Built 1940–1949",        _num("built_1940_to_1949")),
            ("Built 1939 or earlier",  _num("built_1939_or_earlier")),
        ]
        yr_df = pd.DataFrame([(l, v) for l, v in year_cols if v and v > 0],
                             columns=["era", "units"])
        if not yr_df.empty:
            yr_df["era"] = pd.Categorical(yr_df["era"],
                                            categories=[l for l, _ in year_cols],
                                            ordered=True)
            yr_df = yr_df.sort_values("era")
            fig = px.bar(yr_df, x="era", y="units",
                          color="units", color_continuous_scale="Blues")
            fig.update_layout(**DEFAULT_LAYOUT, showlegend=False, coloraxis_showscale=False,
                              yaxis_title="Housing units", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
            pre1940 = yr_df[yr_df["era"] == "Built 1939 or earlier"]["units"].sum()
            total = yr_df["units"].sum()
            if total:
                st.caption(
                    f"**{pre1940 / total:.0%} of Lynn's housing stock predates 1940** — "
                    f"a leading indicator of legacy lead-paint exposure risk. "
                    f"This pattern shows up in EJScreen's `PRE1960_HOUSING` indicator "
                    f"in the *Neighborhoods* tab."
                )

        # -------------------------------------------------------------------
        # 9.5 Housing market trend (Zillow ZHVI + ZORI) — Phase D
        # ACS gives a single-snapshot median; Zillow gives the time series
        # that shows whether Lynn's market is heating, cooling, or sliding
        # relative to MA + the country.
        # -------------------------------------------------------------------
        housing_trend = load_dataset("lynn_housing_trend")
        if not housing_trend.empty:
            st.subheader("Housing market — Lynn vs. MA vs. US trend")
            housing_trend["date"] = pd.to_datetime(housing_trend["date"], errors="coerce")
            housing_trend = housing_trend.dropna(subset=["date"])

            zhvi = housing_trend[housing_trend["metric"] == "ZHVI"]
            zori = housing_trend[housing_trend["metric"] == "ZORI"]

            # Latest snapshot bar
            latest_dt = housing_trend["date"].max()
            latest = housing_trend[housing_trend["date"] == latest_dt].copy()
            lynn_zhvi = latest[(latest["scope"] == "Lynn") & (latest["metric"] == "ZHVI")]
            lynn_zori = latest[(latest["scope"] == "Lynn") & (latest["metric"] == "ZORI")]

            hc1, hc2, hc3 = st.columns(3)
            if not lynn_zhvi.empty:
                with hc1:
                    st.metric(
                        f"Lynn typical home value ({latest_dt:%b %Y})",
                        f"${lynn_zhvi.iloc[0]['value']:,.0f}",
                        help="Zillow ZHVI — typical home value (33rd–67th percentile, smoothed, seasonally adjusted).",
                    )
            ma_zhvi = latest[(latest["scope"] == "Massachusetts") & (latest["metric"] == "ZHVI")]
            if not lynn_zhvi.empty and not ma_zhvi.empty:
                gap = lynn_zhvi.iloc[0]["value"] - ma_zhvi.iloc[0]["value"]
                with hc2:
                    st.metric(
                        "vs MA",
                        f"${ma_zhvi.iloc[0]['value']:,.0f}",
                        f"{gap:+,.0f} (Lynn vs MA)",
                        delta_color="normal" if gap >= 0 else "inverse",
                    )
            if not lynn_zori.empty:
                with hc3:
                    st.metric(
                        f"Lynn typical rent ({latest_dt:%b %Y})",
                        f"${lynn_zori.iloc[0]['value']:,.0f}",
                        help="Zillow ZORI — typical asking rent across SFR + condo + multifamily, smoothed.",
                    )

            # ZHVI trend
            if not zhvi.empty:
                fig = px.line(
                    zhvi.sort_values("date"),
                    x="date", y="value", color="scope",
                    color_discrete_map={
                        "Lynn": LEHS_GOLD,
                        "Massachusetts": LEHS_NAVY,
                        "United States": "#455A64",
                    },
                )
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                    yaxis_title="Typical home value (ZHVI)",
                    xaxis_title="",
                    legend_title="",
                    title="Home values — Lynn vs. Massachusetts vs. United States",
                )
                st.plotly_chart(fig, use_container_width=True)

            # ZORI trend (Lynn + US only — ZORI is not published at state level)
            if not zori.empty:
                fig = px.line(
                    zori.sort_values("date"),
                    x="date", y="value", color="scope",
                    color_discrete_map={
                        "Lynn": LEHS_GOLD,
                        "United States": "#455A64",
                    },
                )
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                    yaxis_title="Typical asking rent (ZORI)",
                    xaxis_title="",
                    legend_title="",
                    title="Rents — Lynn vs. United States",
                )
                st.plotly_chart(fig, use_container_width=True)

            st.caption(
                "Source: Zillow Research public CSVs. **ZHVI** (Zillow Home Value Index) "
                "is the typical value of a home in the 33rd–67th percentile range, "
                "smoothed and seasonally adjusted. **ZORI** (Observed Rent Index) is "
                "typical asking rent across single-family, condo, and multifamily. "
                "Rapid home-value appreciation outpacing wage growth shows up downstream "
                "as housing burden + displacement pressure on school families."
            )

        # -------------------------------------------------------------------
        # 10. Commute
        # -------------------------------------------------------------------
        st.header("How Lynn gets to work")
        if not commute.empty:
            travel = commute[commute["mode"].str.contains("travel time", case=False, na=False)]
            modes = commute[~commute["mode"].str.contains("travel time", case=False, na=False)].copy()
            if not travel.empty:
                st.metric("Mean commute time", f"{travel['pct_or_min'].iloc[0]:.1f} minutes")
            if not modes.empty:
                modes_sorted = modes.sort_values("pct_or_min", ascending=True)
                fig = px.bar(modes_sorted, y="mode", x="pct_or_min", orientation="h",
                             color="pct_or_min", color_continuous_scale="Mint",
                             title="Commute mode (% of workers age 16+)")
                fig.update_layout(**DEFAULT_LAYOUT, showlegend=False, coloraxis_showscale=False,
                                  xaxis_title="% of workers", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "**Transit:** Lynn is served by the MBTA Newburyport/Rockport commuter rail line "
            "(~20–25 min to Boston North Station from Lynn Central or River Works), plus "
            "MBTA bus routes 426, 429, 435, 436, 439, 441, 442, 448, 449, 450, 455, 459. "
            "Major car arteries: Lynnway (Route 1A), Route 107, Route 129, Western Ave."
        )

        # -------------------------------------------------------------------
        # 11. Geography
        # -------------------------------------------------------------------
        st.header("Geography + neighborhoods")
        geo_rows = pd.DataFrame([
            ("Total area",              "13.5 sq mi (10.8 land + 2.7 water)"),
            ("Population density",      f"{(_num('pop_total') or 0) / 10.8:,.0f} per sq mi (land)"),
            ("Atlantic coastline",      "~4 miles (Nahant Bay → Lynn Beach → Swampscott line)"),
            ("Highest point",           "Boston Hill (~285 ft, in Lynn Woods)"),
            ("Major water bodies",      "Sluice Pond, Flax Pond, Birch Pond, Walden Pond (Lynn), Breeds Pond"),
            ("Lynn Woods Reservation",  "2,200 acres — one of the largest municipal parks in the US"),
            ("Lynn Heritage State Park","Waterfront — restored from former shoe-mill district"),
            ("Climate",                 "Humid continental (Köppen Dfa); coastal moderation"),
            ("Founded",                 "1629 (originally 'Saugus'; renamed Lynn 1637 after King's Lynn, England)"),
            ("Incorporated as city",    "1850"),
            ("Government",              "Mayor–council (Plan B charter, 11-member city council)"),
        ], columns=["Feature", "Detail"])
        st.dataframe(geo_rows, use_container_width=True, hide_index=True)

        st.subheader("Neighborhoods (commonly recognized)")
        nbhds = pd.DataFrame([
            ("Diamond District",        "Coastal Victorian / shingle-style historic district, eastern shore"),
            ("West Lynn",                "Working/middle-class residential; Lynn English's primary catchment"),
            ("East Lynn",                "Mixed residential; includes Lynn Beach + Nahant Beach access"),
            ("Highlands",                "Northern, hilly residential close to Lynn Woods"),
            ("Wyoma Square",            "Northeast commercial/residential node"),
            ("Brickyard",                "Industrial-legacy area near the GE Aerospace plant"),
            ("Downtown / Central Square","Historic downtown, MBTA Central station, civic center"),
            ("Lynn Common area",         "Historic Lynn Common (1630s), surrounded by civic + church buildings"),
            ("Pine Hill",                "Western residential"),
        ], columns=["Neighborhood", "Notes"])
        st.dataframe(nbhds, use_container_width=True, hide_index=True)

        # -------------------------------------------------------------------
        # 12. Education context
        # -------------------------------------------------------------------
        st.header("Education context")
        st.markdown(
            """
- **K–12:** Lynn Public Schools (LPS) — ~16,000 students, 22 schools, including
  **Lynn English** (LEHS), **Classical** (LCHS), **Lynn Vocational Technical
  Institute** (Lynn Tech). Two charter schools: **KIPP Academy Lynn** and
  **KIPP Academy Lynn Collegiate**.
- **Higher ed in Lynn proper:** **North Shore Community College** (Lynn campus,
  associate degrees + workforce programs).
- **Adjacent higher-ed:** **Salem State University** (Salem), **Endicott
  College** (Beverly), **UMass Lowell**, **UMass Boston** — all within ~30 min.
- See the **College & Career** page for the top destination colleges Lynn
  graduates attend (with grad rate, Pell %, demographics from IPEDS).
"""
        )

        # -------------------------------------------------------------------
        # 13. History highlights
        # -------------------------------------------------------------------
        st.header("History highlights")
        st.markdown(
            """
- **1629** — English settlers found the village of "Saugus" on Massachusett
  homelands; renamed Lynn in 1637 after King's Lynn, England.
- **1635** — first shoemaker in colonial America (Philip Kirtland) reportedly
  sets up in Lynn — beginning a 250-year run as a major shoe-manufacturing
  center.
- **1850** — Lynn incorporates as a city. Population ~14,000.
- **1880s–1890s** — peak of the shoe industry; Lynn produces more women's
  shoes than any other city in the world. Major labor organizing, including
  the 1860 New England Shoemakers' Strike, the largest strike in the US
  before the Civil War.
- **1892** — Thomson-Houston (predecessor to General Electric) opens the Lynn
  River Works. Lynn becomes one of GE's two original "plants" alongside
  Schenectady, NY.
- **1981** — last shoe factory (Vamp Co.) closes; the city's signature 19th-c.
  industry effectively ends.
- **1980s–1990s** — major demographic shift as Dominican, Cambodian,
  Vietnamese, and Salvadoran communities establish themselves.
- **2010s–2020s** — Latin American (especially Central American + Caribbean)
  and African (especially West African) immigration drives renewed population
  growth, surpassing 100,000 in the 2020 Census.
- **2024** — GE Aviation officially renames the segment **GE Aerospace**;
  Lynn River Works continues as a major military and commercial jet-engine
  facility.
"""
        )

        # -------------------------------------------------------------------
        # 14. Related dashboard pages
        # -------------------------------------------------------------------
        st.header("Where to go next")
        st.markdown(
            """
- **[School Profile](/School_Profile?embed=true)** — LEHS-specific student demographics
  and the school as a snapshot of Lynn.
- **Neighborhoods tab** (above) — tract-level Census ACS + EJScreen + CDC PLACES
  for Lynn's 22 census tracts.
- **[Lynn District page](/Lynn_District?embed=true)** — *All Schools* tab lists every
  K-12 school in LPS, filterable and sortable; *Snapshot* tab shows Lynn vs.
  Gateway median vs. State median on accountability indicators.
- **[Where Students Live](/Where_Students_Live?embed=true)** — Maxwell's original
  geospatial work on student address + absenteeism patterns.
"""
        )

        data_downloads_panel({
            "Lynn city headline stats (ACS)": city,
            "Birthplaces (B05006)": birthplaces,
            "Languages spoken at home (C16001)": languages,
            "Employment by industry (S2403)": industries,
            "Commute mode (S0801)": commute,
            "Age × sex (S0101)": age_pyramid,
            "Decadal population 1790–2020": decadal,
        })


# ===========================================================================
# TAB 2 — NEIGHBORHOODS (former 9_Community_Context.py)
# ===========================================================================

with tab_nbhds:
    # -----------------------------------------------------------------------
    # School-level proxies (LEHS itself)
    # -----------------------------------------------------------------------
    st.header("LEHS — Student Composition (as a community mirror)")
    st.caption(
        "These are LEHS student-level figures, not Census. They reflect Lynn's "
        "community demographics because the school's catchment overlaps the city."
    )

    enrollment = load_dataset("enrollment_demographics")
    lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY") \
        if not enrollment.empty else pd.DataFrame()

    if not lehs.empty:
        latest = lehs.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.metric("% First Language Not English", f"{latest['FLNE_PCT']:.0%}")
        with c2: st.metric("% Hispanic/Latino",            f"{latest['HL_PCT']:.0%}")
        with c3: st.metric("% Low Income",                 f"{latest['LI_PCT']:.0%}")
        with c4: st.metric("% English Learner",            f"{latest['EL_PCT']:.0%}")

    st.divider()

    # -----------------------------------------------------------------------
    # Lynn census tracts — ACS data
    # -----------------------------------------------------------------------
    tracts_path = PROCESSED_DIR / "lynn_tracts.geojson"
    if not tracts_path.exists():
        st.info("Census ACS data is temporarily unavailable. Please check back later.")
    else:
        tracts = gpd.read_file(tracts_path)
        for col in ["median_household_income", "foreign_born_pct", "bachelors_or_higher_pct",
                    "severe_burden_pct", "non_english_pct", "lang_total", "pop_total"]:
            if col in tracts.columns:
                tracts[col] = pd.to_numeric(tracts[col], errors="coerce")

        acs_cols = ["median_household_income", "foreign_born_pct",
                    "bachelors_or_higher_pct", "non_english_pct"]
        has_acs = any(c in tracts.columns for c in acs_cols)

        st.header("Census ACS — Lynn's 22 Census Tracts")
        st.caption(
            "5-year ACS estimates (2019–2023). Lynn has 22 census tracts; each is a "
            "neighborhood-scale unit of ~3–6K residents. Variation across these "
            "tracts shows how Lynn is not demographically uniform."
        )

        if not has_acs:
            st.info(
                "Tract-level ACS data (median income, foreign-born, education, language) "
                "is not yet bundled into `lynn_tracts.geojson`. Run "
                "`scripts/10_download_census_acs.py` (requires `CENSUS_API_KEY`) followed "
                "by `scripts/11_build_lynn_geo.py` to populate these overlays. "
                "Environmental-justice and CDC PLACES health metrics below are unaffected."
            )
        else:
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                if "median_household_income" in tracts.columns:
                    med_inc = tracts["median_household_income"].median()
                    st.metric("Median household income (Lynn median tract)", f"${med_inc:,.0f}")
            with c2:
                if "foreign_born_pct" in tracts.columns:
                    fb = tracts["foreign_born_pct"].mean()
                    st.metric("Avg % Foreign-born", f"{fb:.0%}")
            with c3:
                if "bachelors_or_higher_pct" in tracts.columns:
                    ba = tracts["bachelors_or_higher_pct"].mean()
                    st.metric("Avg % Bachelor's or higher (age 25+)", f"{ba:.0%}")
            with c4:
                if "non_english_pct" in tracts.columns:
                    nm = tracts["non_english_pct"].mean()
                    st.metric("Avg % non-English at home", f"{nm:.0%}")

            st.caption(
                "**Massachusetts state averages for comparison**: median household income "
                "~$96,500 · foreign-born ~17% · bachelor's+ ~46% · non-English at home ~26%. "
                "Lynn's tracts skew significantly lower-income and more foreign-born, with "
                "substantially higher non-English-at-home share."
            )

            # -------------------------------------------------------------------
            # Distribution of each variable across the 22 tracts
            # -------------------------------------------------------------------
            st.header("Variation Across Lynn's Census Tracts")
            st.caption("Each row is one census tract. Bars show how much spread there is across the city.")

            metrics = [
                ("median_household_income", "Median household income", "${:,.0f}", "Greens"),
                ("foreign_born_pct",        "% Foreign-born",          "{:.0%}",   "Purples"),
                ("non_english_pct",         "% Non-English at home",   "{:.0%}",   "Greens"),
                ("bachelors_or_higher_pct", "% Bachelor's or higher",  "{:.0%}",   "Blues"),
                ("severe_burden_pct",       "% Severely rent-burdened","{:.0%}",   "Reds"),
            ]

            for col, label, fmt, palette in metrics:
                if col not in tracts.columns:
                    continue
                sub = tracts.dropna(subset=[col]).copy()
                if sub.empty:
                    continue
                sub["label"] = sub[col].apply(lambda x: fmt.format(x))
                sub = sub.sort_values(col, ascending=True)

                st.subheader(label)
                fig = px.bar(
                    sub, y="NAMELSAD", x=col, orientation="h",
                    text="label", color=col, color_continuous_scale=palette,
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    xaxis_title=label,
                    yaxis_title="",
                    coloraxis_showscale=False,
                    height=480,
                )
                if "_pct" in col:
                    fig.update_layout(xaxis_tickformat=".0%")
                elif col == "median_household_income":
                    fig.update_layout(xaxis_tickformat="$,.0f")
                st.plotly_chart(fig, use_container_width=True)

            # -------------------------------------------------------------------
            # Languages spoken at home — the linguistic landscape
            # -------------------------------------------------------------------
            if "non_english_pct" in tracts.columns:
                st.header("Linguistic Landscape")
                st.caption(
                    "Census ACS at tract level publishes the COLLAPSED language table (13 groups). "
                    "Across all 22 Lynn tracts, Spanish is the dominant non-English language. "
                    "Granular breakouts (Khmer/Cambodian, Portuguese, Arabic) are suppressed by "
                    "Census at tract resolution but are available at the city level (see the "
                    "*Citywide* tab above)."
                )
                lang_share = pd.DataFrame({
                    "Group": ["English only", "Non-English"],
                    "Total speakers (age 5+)": [
                        tracts["lang_total"].fillna(0).sum() * (1 - tracts["non_english_pct"].mean()),
                        tracts["lang_total"].fillna(0).sum() * tracts["non_english_pct"].mean(),
                    ],
                })
                fig = px.pie(
                    lang_share, names="Group", values="Total speakers (age 5+)",
                    color="Group",
                    color_discrete_map={"English only": LEHS_NAVY, "Non-English": LEHS_GOLD},
                    hole=0.55,
                )
                fig.update_traces(textinfo="percent+label", textfont_size=12)
                fig.update_layout(**DEFAULT_LAYOUT, height=380)
                st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # Map link
        # -------------------------------------------------------------------
        st.subheader("See the same data geographically")
        st.markdown(
            """
The **[Maps section](/Maps?embed=true)** of this dashboard opens the Lynn map, where
each tract is rendered as a polygon colored by any of these indicators.
Click any tract for the full detail panel.

For the statewide cartographic comparison, see the
[Massachusetts Education Atlas](https://maxwellhowegis.com/ma-atlas/) — every
public school district in MA colored by 40+ metrics including these community
indicators (where data is available at scale).
"""
        )

        # -------------------------------------------------------------------
        # Environmental Justice (EPA EJScreen) + Population Health (CDC PLACES)
        # -------------------------------------------------------------------
        st.header("Environmental justice + community health")
        st.caption(
            "EPA EJScreen tracks pollution exposure and demographic indices; CDC PLACES "
            "publishes tract-level prevalence of chronic disease and behavioral health. "
            "Joined onto Lynn's 22 tracts in scripts/11_build_lynn_geo.py."
        )

        ej_cols = [("ENV_INDEX", "Env burden index"),
                   ("PM25", "PM2.5"),
                   ("OZONE", "Ozone"),
                   ("PRE1960_HOUSING", "% Housing built pre-1960 (lead-paint era)")]
        ej_present = [(c, l) for c, l in ej_cols if c in tracts.columns and tracts[c].notna().any()]

        if ej_present:
            st.subheader("EPA EJScreen — environmental burden")
            cols = st.columns(min(4, len(ej_present)))
            for (col, label), st_col in zip(ej_present, cols):
                with st_col:
                    val = pd.to_numeric(tracts[col], errors="coerce").mean()
                    if pd.notna(val):
                        st.metric(f"Lynn mean — {label}", f"{val:.1f}")
            if "ENV_INDEX" in tracts.columns and tracts["ENV_INDEX"].notna().any():
                ej_sub = tracts.dropna(subset=["ENV_INDEX"]).sort_values("ENV_INDEX")
                fig = px.bar(ej_sub, y="NAMELSAD", x="ENV_INDEX", orientation="h",
                             color="ENV_INDEX", color_continuous_scale="Reds",
                             title="Environmental burden index by Lynn tract")
                fig.update_layout(**DEFAULT_LAYOUT, height=480,
                                  xaxis_title="Index (higher = more burden)",
                                  yaxis_title="", coloraxis_showscale=False)
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "EPA EJScreen data not yet populated — the ingest tries 3 known EPA "
                "URLs (some have moved post-2025). See scripts/12_download_community_health.py."
            )

        places_cols = [("asthma_pct", "Asthma"),
                        ("mental_distress_pct", "Mental distress"),
                        ("obesity_pct", "Obesity"),
                        ("smoking_pct", "Smoking"),
                        ("high_bp_pct", "High blood pressure"),
                        ("diabetes_pct", "Diabetes")]
        pl_present = [(c, l) for c, l in places_cols if c in tracts.columns and tracts[c].notna().any()]

        if pl_present:
            st.subheader("CDC PLACES — chronic-disease prevalence")
            st.caption("Crude prevalence (% of adults), most recent release. Source: CDC PLACES.")
            cols = st.columns(min(3, len(pl_present)))
            for i, (col, label) in enumerate(pl_present):
                with cols[i % 3]:
                    val = pd.to_numeric(tracts[col], errors="coerce").mean()
                    if pd.notna(val):
                        st.metric(f"Lynn mean — {label}", f"{val:.1f}%")
            leaders = [c for c, _ in pl_present if c in ("asthma_pct", "mental_distress_pct")]
            if leaders:
                long = tracts[["NAMELSAD"] + leaders].melt(
                    id_vars="NAMELSAD", var_name="metric", value_name="pct")
                long["pct"] = pd.to_numeric(long["pct"], errors="coerce")
                long = long.dropna(subset=["pct"])
                if not long.empty:
                    fig = px.bar(long.sort_values("pct"), y="NAMELSAD", x="pct",
                                  color="metric", barmode="group", orientation="h",
                                  title="Asthma + mental distress by Lynn tract")
                    fig.update_layout(**DEFAULT_LAYOUT, height=520,
                                      xaxis_title="% prevalence", yaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("CDC PLACES data did not populate — check scripts/12_download_community_health.py.")

        data_downloads_panel({
            "Enrollment & demographics": enrollment,
        })
