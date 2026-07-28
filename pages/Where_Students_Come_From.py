"""Where Students Come From — residential geography plus feeder middle schools & enrollment projection."""
from pathlib import Path
import streamlit as st
import pandas as pd  # noqa: E402
import json  # noqa: E402
import plotly.express as px  # noqa: E402
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.branding import page_footer, sidebar_attribution
from utils.constants import PROCESSED_DIR
from utils.constants import LEHS_SCHOOL_CODE  # noqa: E402
from utils.data_loader import load_dataset  # noqa: E402
from utils.interpret import sy_label  # noqa: E402
from utils.charts import DEFAULT_LAYOUT, csv_download  # noqa: E402
from utils.constants import LEHS_GOLD, LEHS_NAVY, SEQ_BRAND  # noqa: E402
from utils.geo_loader import tract_display_label  # noqa: E402
from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, csv_download, data_downloads_panel, with_year_gaps, span_years
from utils.constants import LEHS_SCHOOL_CODE, LEHS_NAVY, LEHS_GOLD, STATE_COLOR, LYNN_SIBLING_COLOR
from utils.data_loader import load_dataset
from utils.interpret import sy_label
st.set_page_config(page_title="Where Students Come From | LEHS", page_icon="🏘️", layout="wide")
sidebar_attribution()

st.title("Where Students Come From")
st.markdown(
    "The two pipelines that shape who walks through LEHS's doors: the "
    "**neighborhoods** students live in, and the **middle schools** that "
    "feed the school — including the enrollment projection."
)
_tab_0, _tab_1 = st.tabs(['🏘️ Where Students Live', '🏫 Feeder Schools & Projection'])

with _tab_0:
    # ==== from pages/11_Where_Students_Live.py ====
    st.header("Where Our Students Live")
    st.markdown(
        "**Where does the LEHS student body actually live?** The school's "
    "official boundary is one thing; the residential pattern of the kids "
    "who walk through the door every day is another. This page surfaces "
    "the second."
    )
    st.markdown(
        "This page focuses on the **residence pattern itself**. Two follow-on "
    "questions live on neighboring pages: *how does distance from school "
    "predict attendance?* is now part of "
    "[Discipline & Climate](/Discipline_and_Climate?embed=true), and *what is the "
    "community context around those addresses?* lives on the "
    "[Lynn page](/Lynn_City?embed=true) (Neighborhoods tab)."
    )

    # ---------------------------------------------------------------------------
    # Privacy notice — same as before; this work uses private SIS data
    # ---------------------------------------------------------------------------

    st.caption(
        "Source: Lynn Public Schools student information system, provided via a "
    "data request to the district. All maps show aggregated densities (KDE "
    "surfaces, 100m and 150m grid cells), not individual locations."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Residential density maps
    # ---------------------------------------------------------------------------

    _IMG_DIR = PROCESSED_DIR / "lehs_research"


    def _show(slug: str, caption: str = "") -> None:
        path = _IMG_DIR / f"{slug}.png"
        if not path.exists():
            st.caption(f"_(image not yet generated: {slug}.png)_")
            return
        st.image(str(path), caption=caption, width="stretch")


    st.header("Residential Density of LEHS Students")
    st.markdown(
        "Aggregated density of student residences across Lynn."
    )

    c1, c2 = st.columns(2)
    with c1:
        _show(
            "kde_heatmap",
            "KDE density surface — relative concentration of LEHS student "
        "residences across Lynn.",
        )
    with c2:
        _show(
            "grid_density_150m",
            "Raw student counts per 150m × 150m grid cell.",
        )

    st.markdown(
        "**Read this against the school's catchment map.** Lynn does not draw "
    "neighborhood-school boundaries for high school (all four comprehensive "
    "HS are city-wide). The shape above is *who actually enrolls at LEHS*, "
    "not who's assigned to it."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Which neighborhoods the density covers — and who that makes the student body.
    # The density maps above are pre-rendered surfaces (no per-tract residence
    # counts are published), so the neighborhood read is an honest interpretation
    # of the maps, paired with LEHS's real demographic profile from DESE.
    # ---------------------------------------------------------------------------



    st.subheader("Which neighborhoods — and who that makes the student body")
    st.markdown(
        "Reading the density maps above, the deepest concentrations of LEHS "
    "students sit in **central and western Lynn** — the blocks around "
    "**Lynn Common and Central Square (downtown)**, spreading west into "
    "**West Lynn** (where the school itself sits, on O'Callaghan Way) and "
    "north into the **Brickyard**. The pattern thins toward the coastal "
    "**Diamond District** and the **Highlands and Wyoma** to the north. "
    "Because Lynn runs no neighborhood-school zoning for high school, this "
    "*is* the school's community — so the people who live in those central "
    "blocks are, in effect, the people the school serves."
    )

    _enr = load_dataset("enrollment_demographics")
    if not _enr.empty:
        _lehs = _enr[_enr["ORG_CODE"].astype(str) == LEHS_SCHOOL_CODE].sort_values("SY")
        if not _lehs.empty:
            _cur = _lehs.iloc[-1]

            def _pct(v):
                return f"{v:.0%}" if pd.notna(v) else "—"

            st.markdown(f"**Who that makes the student body — LEHS, {sy_label(int(_cur['SY']))}:**")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Hispanic / Latino", _pct(_cur.get("HL_PCT")))
            m2.metric("English Learners", _pct(_cur.get("EL_PCT")))
            m3.metric("Low income", _pct(_cur.get("LI_PCT")))
            m4.metric("High needs", _pct(_cur.get("HN_PCT")))
            st.caption(
                "“High needs” counts a student in at least one of: English Learner, "
            "low income, or students with disabilities (DESE definition). "
            "Compare these against the tract indicators below to see how the "
            "neighborhoods the density map covers line up on income, "
            "foreign-born share, and health."
            )

    st.divider()

    # ---------------------------------------------------------------------------
    # Cross-reference: census tracts (placeholder + roadmap)
    # ---------------------------------------------------------------------------

    st.header("Cross-Reference: Community Context")
    st.markdown(
        "The residential pattern above sits inside a real community with its "
    "own demographic, environmental, and health profile. Below, the same "
    "22 Lynn census tracts are ranked on three indicators — eyeball them "
    "against the residence density maps above and look for **the tracts "
    "where most LEHS students live being the *same* tracts that score "
    "highest on community-burden indicators**."
    )




    _TRACTS_PATH = PROCESSED_DIR / "lynn_tracts.geojson"

    if _TRACTS_PATH.exists():
        with open(_TRACTS_PATH, encoding="utf-8") as f:
            _fc = json.load(f)
        _rows = [feat["properties"] for feat in _fc.get("features", []) if feat.get("properties")]
        _tracts_df = pd.DataFrame(_rows)

        # Public-facing neighborhood label, e.g. "West Lynn (Tract 2057)".
        if "NAMELSAD" in _tracts_df.columns:
            _tracts_df["tract_label"] = _tracts_df["NAMELSAD"].map(tract_display_label)
        elif "GEOID" in _tracts_df.columns:
            _tracts_df["tract_label"] = "Tract " + _tracts_df["GEOID"].astype(str).str[-6:]

        def _ranked_bar(col: str, label: str, fmt: str, palette: str = None):
            if col not in _tracts_df.columns:
                st.caption(f"_({label}: column not in lynn_tracts.geojson — refresh pending)_")
                return
            d = _tracts_df[["tract_label", col]].copy()
            d[col] = pd.to_numeric(d[col], errors="coerce")
            d = d.dropna(subset=[col]).sort_values(col, ascending=True)
            if d.empty:
                st.caption(f"_({label}: no non-null values yet)_")
                return
            d["text"] = d[col].apply(lambda v: fmt.format(v))
            # Bar length already encodes the value (and it's printed as a text label),
            # so a value->color gradient would be a redundant, decorative second
            # encoding. Use a single flat brand color instead.
            fig = px.bar(
                d, y="tract_label", x=col, orientation="h", text="text",
            )
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside")
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_title=label,
                yaxis_title="",
                height=480,
            )
            # Drive tickformat from data range, not column name. Columns like
            # asthma_pct / mental_distress_pct are 0-100 (CDC PLACES) while
            # foreign_born_pct is 0-1 (Census fraction) — same _pct suffix,
            # different scales. Treating both as 0-1 produces a "1230%" axis.
            col_max = d[col].max()
            if col == "median_household_income":
                fig.update_layout(xaxis_tickformat="$,.0f")
            elif col_max <= 1.5:
                # Values are a 0-1 ratio (e.g. foreign_born_pct = 0.27)
                fig.update_layout(xaxis_tickformat=".0%")
            elif fmt.endswith("%}"):
                # Values are already in percent units (e.g. asthma_pct = 12.3);
                # render as a number with a % suffix.
                fig.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig, width="stretch")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("% Foreign-born (ACS)")
            st.caption(
                "Share of residents born outside the U.S. (5-year ACS). The tract "
            "geojson ships no direct low-income column, so we report foreign-born "
            "share — a published demographic indicator — rather than inventing a "
            "poverty figure."
            )
            _ranked_bar("foreign_born_pct", "% Foreign-born", "{:.0%}", SEQ_BRAND)
        with c2:
            st.subheader("Median household income (ACS)")
            _ranked_bar("median_household_income", "$ median household income", "${:,.0f}", SEQ_BRAND)

        c3, c4 = st.columns(2)
        with c3:
            st.subheader("CDC PLACES — % adults with asthma")
            _ranked_bar("asthma_pct", "% asthma prevalence", "{:.1f}%", SEQ_BRAND)
        with c4:
            st.subheader("CDC PLACES — % adults with mental distress")
            _ranked_bar("mental_distress_pct", "% mental distress", "{:.1f}%", SEQ_BRAND)

        st.markdown(
            "**Implication.** The student-residence concentration above maps onto "
        "the city's lower-income, more-foreign-born, higher-health-burden "
        "neighborhoods (lower median household income, higher foreign-born share, "
        "higher chronic-disease and housing-cost burden). That's a structural "
        "finding: school-level interventions happen *inside* a community that "
        "already has community-level needs. See the "
        "[Lynn page](/Lynn_City?embed=true) (Neighborhoods tab) for the full "
        "statewide-comparison view of these same indicators."
        )

        st.subheader("Housing-cost burden by Lynn neighborhood")
        st.caption(
            "Share of households spending 30%+ of their income on housing "
        "(5-year ACS, severe + moderate cost burden). A high burden squeezes "
        "the same families whose children fill the residence-density maps "
        "above — leaving less slack for everything from school supplies to "
        "stable housing."
        )
        _ranked_bar(
            "severe_burden_pct",
            "% of households cost-burdened (30%+ of income on housing)",
            "{:.0%}", SEQ_BRAND,
        )

        # One-click export of the tract table behind the four charts above —
        # same attribute set the maps carry (ACS + CDC PLACES per tract).
        csv_download(
            _tracts_df,
            "lynn_tracts.csv",
            label="⬇ Download the Lynn neighborhood table (CSV)",
            key="dl_lynn_tracts",
        )
    else:
        st.info(
            "`data/processed/lynn_tracts.geojson` not found — community context "
        "overlay is unavailable. Re-run the refresh pipeline to regenerate."
        )

    st.divider()

    # ---------------------------------------------------------------------------
    # Housing affordability — what it costs to live where these students live
    # ---------------------------------------------------------------------------

    st.header("Housing affordability")
    st.markdown(
        "Where students live is shaped by what housing costs. Lynn's home values "
    "and rents are the economic backdrop behind the residence maps above. "
    "(This is affordability only — building-permit and zoning data, which would "
    "show housing *supply*, aren't in this pipeline; see "
    "[What We Don't Know](/Methodology).)"
    )

    _housing = load_dataset("lynn_housing_trend")
    if not _housing.empty:
        zhvi = _housing[(_housing["scope"] == "Lynn") & (_housing["metric"] == "ZHVI")].copy()
        zhvi["date"] = pd.to_datetime(zhvi["date"], errors="coerce")
        zhvi["value"] = pd.to_numeric(zhvi["value"], errors="coerce")
        zhvi = zhvi.dropna(subset=["date", "value"]).sort_values("date")
        if not zhvi.empty:
            fig = px.line(zhvi, x="date", y="value",
                          labels={"date": "", "value": "Typical home value"})
            fig.update_traces(line=dict(color=LEHS_NAVY, width=2.5))
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                              title="Lynn typical home value, 2000–present (Zillow ZHVI)")
            st.plotly_chart(fig, width="stretch")
            first, latest = zhvi.iloc[0], zhvi.iloc[-1]
            st.caption(
                f"Zillow's typical Lynn home value rose from about "
            f"${first['value']:,.0f} in {first['date']:%Y} to "
            f"${latest['value']:,.0f} in {latest['date']:%Y}. Source: Zillow "
            "Home Value Index (ZHVI), all homes, smoothed."
            )

    _city = load_dataset("lynn_city_stats")
    if not _city.empty:
        row = _city.iloc[0]

        def _num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        occ = _num(row.get("occupied_housing_units"))
        owner = _num(row.get("owner_occupied"))
        mhv = _num(row.get("median_home_value"))
        rent = _num(row.get("median_gross_rent"))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Median home value", f"${mhv:,.0f}" if mhv else "—")
        c2.metric("Median gross rent", f"${rent:,.0f}/mo" if rent else "—")
        if occ and owner:
            c3.metric("Owner-occupied", f"{owner / occ:.0%}")
            c4.metric("Renter-occupied", f"{1 - owner / occ:.0%}")

        # Age of the housing stock — Lynn's is notably old (a maintenance-cost and
        # lead-paint signal), so show the year-built distribution.
        built = {
            "2014+": "built_2014_or_later", "2010–13": "built_2010_to_2013",
            "2000–09": "built_2000_to_2009", "1990–99": "built_1990_to_1999",
            "1980–89": "built_1980_to_1989", "1970–79": "built_1970_to_1979",
            "1960–69": "built_1960_to_1969", "1950–59": "built_1950_to_1959",
            "1940–49": "built_1940_to_1949", "≤1939": "built_1939_or_earlier",
        }
        bdf = pd.DataFrame(
            [{"Era": k, "Units": _num(row.get(v))} for k, v in built.items()]
        ).dropna(subset=["Units"])
        if not bdf.empty:
            fig = px.bar(bdf, x="Era", y="Units", text="Units")
            fig.update_traces(marker_color=LEHS_GOLD, texttemplate="%{text:,.0f}",
                              textposition="outside", cliponaxis=False)
            fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Decade built",
                              yaxis_title="Housing units",
                              title="When Lynn's housing was built")
            st.plotly_chart(fig, width="stretch")
            acs_yr = row.get("acs_year")
            st.caption(
                "Lynn's housing stock skews old — the largest single group predates "
            "1939 — which tends to mean higher maintenance costs and more "
            "lead-paint risk in the homes these students live in."
                + (f" Source: ACS {int(acs_yr)} 5-year estimates." if acs_yr else
                   " Source: ACS 5-year estimates.")
            )

    st.divider()

    # ---------------------------------------------------------------------------
    # Methodology + author
    # ---------------------------------------------------------------------------

    with st.expander("Methodology & data sources"):
        st.markdown(
            """
**Author:** Maxwell Howe (maxwellhowegis.com).

**Source data:**
- LEHS student address records from the Lynn Public Schools student information system (provided via a data request to the district).

**Tools:**
- Geocoding: Stadia Maps via R `ggmap`.
- Spatial aggregation: KDE (kernel density estimation), 100m and 150m
  hexagonal/square grid binning.

**Aggregation:**
- Maps show aggregated densities (KDE, grid cells), not address-level points.
- Grid cells below a minimum count threshold are dropped.

**Where the rest of this research lives:**
- *Distance from school × attendance* and *geographic absenteeism hotspots*
  are now on [Discipline & Climate](/Discipline_and_Climate?embed=true) since chronic
  absence is the outcome they describe.
"""
        )

with _tab_1:
    # ==== from pages/Feeder_Middle_Schools.py ====
    # ---------------------------------------------------------------------------
    # The three Lynn middle schools that feed the district's high schools.
    # These appear in enrollment_demographics ONLY — the processed MCAS panel kept
    # only Lynn HIGH schools, so Grade-8 MCAS for these feeders is not available
    # and is deliberately not shown.
    # ---------------------------------------------------------------------------

    FEEDERS = {
        "01630405": "Breed Middle",
        "01630420": "Pickering Middle",
        "01630305": "Thurgood Marshall Mid",
    }
    FEEDER_ORDER = ["Breed Middle", "Pickering Middle", "Thurgood Marshall Mid"]
    FEEDER_COLORS = {
        "Breed Middle": LEHS_NAVY,
        "Pickering Middle": LEHS_GOLD,
        "Thurgood Marshall Mid": LYNN_SIBLING_COLOR,
    }

    # Grades projected forward. LEHS is a pure 9–12 school, so its TOTAL_CNT equals
    # the sum of G9–G12 — that lets the cohort model's projected total line up
    # directly with the historical TOTAL_CNT line.
    HS_GRADES = ["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]
    PROJ_YEARS = 3        # roll the model forward this many school years
    RATIO_PAIRS = 4       # average progression over this many recent year-pairs
    # Uncertainty cone: zero width at the last KNOWN year (we aren't guessing a
    # number we already have), widening to ±MAX_BAND by the final projected year.
    MAX_BAND = 0.20       # ±20% at the far end of the projection


    def _num(series: pd.Series) -> pd.Series:
        return pd.to_numeric(series, errors="coerce")


    # ---------------------------------------------------------------------------
    # Load + slice
    # ---------------------------------------------------------------------------

    enroll = load_dataset("enrollment_demographics")

    feeder_rows = pd.DataFrame()
    if not enroll.empty and "ORG_CODE" in enroll.columns:
        feeder_rows = enroll[enroll["ORG_CODE"].astype(str).isin(FEEDERS)].copy()
        feeder_rows["SY"] = _num(feeder_rows["SY"])

    lehs = pd.DataFrame()
    if not enroll.empty and "ORG_CODE" in enroll.columns:
        lehs = enroll[enroll["ORG_CODE"].astype(str) == LEHS_SCHOOL_CODE].copy()
        lehs["SY"] = _num(lehs["SY"])
        for c in HS_GRADES + ["TOTAL_CNT"]:
            if c in lehs.columns:
                lehs[c] = _num(lehs[c]).fillna(0)
        lehs = lehs.sort_values("SY").reset_index(drop=True)

    # ---------------------------------------------------------------------------
    # Header + framing
    # ---------------------------------------------------------------------------

    st.header("🎒 Feeder Middle Schools & Enrollment Outlook")
    st.markdown(
        "Before students arrive at Lynn's high schools, they spend their middle-school "
    "years at one of the district's three large middle schools — **Breed**, "
    "**Pickering**, and **Thurgood Marshall**. This page profiles those feeder schools "
    "and then takes a data-driven look at where **Lynn English (LEHS)** enrollment is "
    "heading over the next few years."
    )
    st.caption(
        "The projection here is a simple **grade-progression model** built on public, "
    "aggregate enrollment counts — not a roster-level forecast. It cannot see individual "
    "students, school choice, or migration. Treat it as a transparent baseline, not a "
    "precise prediction. [What we don't know →](/Methodology)"
    )

    if feeder_rows.empty and lehs.empty:
        st.warning(
            "Enrollment data is unavailable, so neither the feeder snapshot nor the "
        "projection can be shown right now."
        )
        page_footer()
        st.stop()

    # ---------------------------------------------------------------------------
    # 1) Feeder snapshot (latest SY)
    # ---------------------------------------------------------------------------

    st.header("Feeder middle schools — latest snapshot")

    feeder_snapshot = pd.DataFrame()
    feeder_year = None
    if not feeder_rows.empty:
        feeder_year = int(feeder_rows["SY"].max())
        latest = feeder_rows[feeder_rows["SY"] == feeder_year].copy()
        rows = []
        for code in FEEDERS:  # preserve order
            r = latest[latest["ORG_CODE"].astype(str) == code]
            if r.empty:
                continue
            r = r.iloc[0]
            gi = lambda c: int(_num(pd.Series([r.get(c)])).fillna(0).iloc[0])
            pc = lambda c: _num(pd.Series([r.get(c)])).iloc[0]
            rows.append({
                "School": FEEDERS[code],
                "Grade 6": gi("G6_CNT"),
                "Grade 7": gi("G7_CNT"),
                "Grade 8": gi("G8_CNT"),
                "Total enrollment": gi("TOTAL_CNT"),
                "% English Learners": pc("EL_PCT"),
                "% Low Income": pc("LI_PCT"),
                "% Students with Disabilities (SWD)": pc("SWD_PCT"),
                "% Hispanic/Latino": pc("HL_PCT"),
            })
        feeder_snapshot = pd.DataFrame(rows)

    if feeder_snapshot.empty:
        st.info("No feeder-school enrollment found in the dataset for the latest year.")
    else:
        st.caption(
            f"School year {sy_label(feeder_year)} (SY{feeder_year}). Percent figures from DESE "
        "are stored as fractions and shown here as percentages."
        )

        counts_tbl = feeder_snapshot[["School", "Grade 6", "Grade 7", "Grade 8", "Total enrollment"]].copy()
        st.dataframe(
            counts_tbl.style.format({c: "{:,}" for c in ["Grade 6", "Grade 7", "Grade 8", "Total enrollment"]}),
            width="stretch", hide_index=True,
        )

        # Grouped bar of G6/G7/G8 by school.
        long = counts_tbl.melt(
            id_vars="School", value_vars=["Grade 6", "Grade 7", "Grade 8"],
            var_name="Grade", value_name="Students",
        )
        long["School"] = pd.Categorical(long["School"], categories=FEEDER_ORDER, ordered=True)
        long = long.sort_values(["School", "Grade"])
        fig = px.bar(
            long, x="Grade", y="Students", color="School", barmode="group",
            title=f"Current middle-grade enrollment by school (SY{feeder_year})",
            color_discrete_map=FEEDER_COLORS, category_orders={"School": FEEDER_ORDER},
            text="Students",
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(**DEFAULT_LAYOUT, height=360, xaxis_title=None,
                          yaxis_title="Students", legend_title_text="")
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "These Grade-8 students are the near-term pipeline into Lynn's 9th grades. "
        "Note that students choose among **LEHS, Classical, Lynn Tech (LVTI), and Douglass**, "
        "so not all of them feed LEHS specifically."
        )

        # Demographic mini-table (fractions → percentages).
        demo_tbl = feeder_snapshot[
            ["School", "% English Learners", "% Low Income", "% Students with Disabilities (SWD)", "% Hispanic/Latino"]
        ].copy()
        st.dataframe(
            demo_tbl.style.format(
                {c: "{:.0%}" for c in ["% English Learners", "% Low Income", "% Students with Disabilities (SWD)", "% Hispanic/Latino"]}
            ),
            width="stretch", hide_index=True,
        )
        st.caption(
            "Student-population profile of the three feeder schools. All three serve "
        "high shares of low-income, English-learner, and Hispanic/Latino students — "
        "context for the populations entering Lynn's high schools."
        )

    # ---------------------------------------------------------------------------
    # 2) LEHS enrollment trend (last ~10 years)
    # ---------------------------------------------------------------------------

    st.header("LEHS enrollment over time")

    if lehs.empty:
        st.info("No LEHS enrollment history available.")
    else:
        trend = lehs[lehs["SY"].notna()].copy()
        trend["SY"] = trend["SY"].astype(int)
        recent = trend[trend["SY"] >= trend["SY"].max() - 10].copy()

        # Total enrollment line, with explicit year gaps so any skipped year breaks.
        tot = recent[["SY", "TOTAL_CNT"]].copy()
        tot_gapped = with_year_gaps(tot, "TOTAL_CNT", year_col="SY", years=span_years(tot))
        fig_tot = go.Figure()
        fig_tot.add_trace(go.Scatter(
            x=tot_gapped["SY"], y=tot_gapped["TOTAL_CNT"], mode="lines+markers",
            name="Total enrollment", line=dict(color=LEHS_NAVY, width=3), connectgaps=False,
        ))
        fig_tot.update_layout(**DEFAULT_LAYOUT, height=340, title="LEHS total enrollment",
                              xaxis_title=None, yaxis_title="Students", showlegend=False)
        st.plotly_chart(fig_tot, width="stretch")

        # Grade-level lines G9–G12.
        grade_labels = {"G9_CNT": "Grade 9", "G10_CNT": "Grade 10",
                        "G11_CNT": "Grade 11", "G12_CNT": "Grade 12"}
        grade_colors = {"Grade 9": LEHS_GOLD, "Grade 10": LEHS_NAVY,
                        "Grade 11": LYNN_SIBLING_COLOR, "Grade 12": STATE_COLOR}
        fig_g = go.Figure()
        yrs = span_years(recent)
        for col, label in grade_labels.items():
            sub = recent[["SY", col]].rename(columns={col: "val"})
            sub_g = with_year_gaps(sub, "val", year_col="SY", years=yrs)
            fig_g.add_trace(go.Scatter(
                x=sub_g["SY"], y=sub_g["val"], mode="lines+markers", name=label,
                line=dict(color=grade_colors[label], width=2), connectgaps=False,
            ))
        fig_g.update_layout(**DEFAULT_LAYOUT, height=360, title="LEHS enrollment by grade (G9–G12)",
                            xaxis_title=None, yaxis_title="Students", legend_title_text="")
        st.plotly_chart(fig_g, width="stretch")

        # Factual note on the recent decline.
        if len(trend) >= 2:
            last_two = trend.tail(2)
            y_prev, y_last = int(last_two["SY"].iloc[0]), int(last_two["SY"].iloc[1])
            t_prev = int(last_two["TOTAL_CNT"].iloc[0])
            t_last = int(last_two["TOTAL_CNT"].iloc[1])
            st.caption(
                f"Total LEHS enrollment moved from {t_prev:,} in SY{y_prev} to {t_last:,} in "
            f"SY{y_last} ({t_last - t_prev:+,}). The grade lines show where that change "
            "concentrated — incoming 9th-grade cohorts have been smaller in the most "
            "recent years."
            )

    # ---------------------------------------------------------------------------
    # 3) LEHS enrollment projection — grade-progression / cohort-survival model
    # ---------------------------------------------------------------------------

    st.header("LEHS enrollment projection")

    proj_table = pd.DataFrame()
    ratios = None
    g9_incoming = None

    # Need enough consecutive year-pairs to estimate progression ratios robustly.
    hist = lehs[lehs["SY"].notna()].copy() if not lehs.empty else pd.DataFrame()
    if not hist.empty:
        hist["SY"] = hist["SY"].astype(int)
        hist = hist.drop_duplicates(subset="SY").sort_values("SY").set_index("SY")
        years = list(hist.index)
        pairs = [(y, y + 1) for y in years if (y + 1) in hist.index]
    else:
        years, pairs = [], []

    if len(pairs) < 2:
        st.info(
            "There is not enough consecutive LEHS enrollment history to build a reliable "
        "grade-progression projection, so the projection is skipped. The snapshot and "
        "trend above still reflect the latest available data."
        )
    else:
        use_pairs = pairs[-RATIO_PAIRS:]

        def _avg_ratio(num_col: str, den_col: str) -> float:
            vals = []
            for y0, y1 in use_pairs:
                den = hist.loc[y0, den_col]
                if den and den > 0:
                    vals.append(hist.loc[y1, num_col] / den)
            return float(np.mean(vals)) if vals else 1.0

        # Year-over-year grade-progression (cohort-survival) ratios.
        r10 = _avg_ratio("G10_CNT", "G9_CNT")   # G10(y+1) / G9(y)
        r11 = _avg_ratio("G11_CNT", "G10_CNT")  # G11(y+1) / G10(y)
        r12 = _avg_ratio("G12_CNT", "G11_CNT")  # G12(y+1) / G11(y)
        ratios = {"G9→G10": r10, "G10→G11": r11, "G11→G12": r12}

        # Incoming G9: hold flat at the recent average of LEHS G9 counts (last 3
        # years). Simple and defensible — the recent average is more robust than
        # any single noisy year, and we do not project the feeders' choice split.
        recent_g9 = [hist.loc[y, "G9_CNT"] for y in years[-3:] if hist.loc[y, "G9_CNT"] > 0]
        g9_incoming = float(np.mean(recent_g9)) if recent_g9 else float(hist.loc[years[-1], "G9_CNT"])

        last_year = years[-1]
        g9 = hist.loc[last_year, "G9_CNT"]
        g10 = hist.loc[last_year, "G10_CNT"]
        g11 = hist.loc[last_year, "G11_CNT"]
        g12 = hist.loc[last_year, "G12_CNT"]

        proj_rows = []
        for i in range(1, PROJ_YEARS + 1):
            new_g10 = g9 * r10
            new_g11 = g10 * r11
            new_g12 = g11 * r12
            new_g9 = g9_incoming
            g9, g10, g11, g12 = new_g9, new_g10, new_g11, new_g12
            total = g9 + g10 + g11 + g12
            proj_rows.append({
                "School year": sy_label(last_year + i),
                "SY": last_year + i,
                "Grade 9": round(g9), "Grade 10": round(g10),
                "Grade 11": round(g11), "Grade 12": round(g12),
                "Projected total": round(total),
            })
        proj_table = pd.DataFrame(proj_rows)

        # ----- Projection chart: historical total + dashed projection + band -----
        hist_total = hist.reset_index()[["SY", "TOTAL_CNT"]].copy()
        hist_recent = hist_total[hist_total["SY"] >= last_year - 10]

        proj_x = [last_year] + list(proj_table["SY"])
        proj_y = [hist.loc[last_year, "TOTAL_CNT"]] + list(proj_table["Projected total"])
        # Cone, not a constant band: the first point is the last KNOWN year, so its
        # half-width is 0 (no uncertainty on a number we already have); each year
        # out widens linearly to ±MAX_BAND at the final projected year.
        n_steps = len(proj_table)
        half = [MAX_BAND * i / n_steps if n_steps else 0.0 for i in range(len(proj_x))]
        band_hi = [v * (1 + h) for v, h in zip(proj_y, half)]
        band_lo = [v * (1 - h) for v, h in zip(proj_y, half)]

        fig_p = go.Figure()
        # Shaded uncertainty cone (drawn first so lines sit on top).
        fig_p.add_trace(go.Scatter(
            x=proj_x + proj_x[::-1], y=band_hi + band_lo[::-1], fill="toself",
            fillcolor="rgba(92,116,166,0.15)", line=dict(width=0),
            name=f"Uncertainty range (0 now → ±{int(MAX_BAND*100)}% by {int(proj_x[-1])})",
            hoverinfo="skip",
        ))
        fig_p.add_trace(go.Scatter(
            x=hist_recent["SY"], y=hist_recent["TOTAL_CNT"], mode="lines+markers",
            name="Historical total", line=dict(color=LEHS_NAVY, width=3),
        ))
        fig_p.add_trace(go.Scatter(
            x=proj_x, y=proj_y, mode="lines+markers", name="Projected total",
            line=dict(color=LEHS_GOLD, width=3, dash="dash"),
        ))
        fig_p.update_layout(**DEFAULT_LAYOUT, height=400,
                            title="LEHS total enrollment — history and 3-year projection",
                            xaxis_title=None, yaxis_title="Students", legend_title_text="")
        st.plotly_chart(fig_p, width="stretch")
        st.caption(
            f"Solid line: actual LEHS total enrollment. Dashed line: grade-progression "
        f"projection. The shaded cone is pinned at the known {sy_label(int(last_year))} "
        f"enrollment and widens to **±{int(MAX_BAND*100)}%** by {int(proj_x[-1])} — an "
        "**illustrative** sensitivity range that grows with distance, not a statistical "
        "confidence interval."
        )

        # Projection ratios + incoming assumption, stated plainly.
        st.markdown(
            f"**Progression ratios** (averaged over the last {len(use_pairs)} year-pairs): "
        f"Grade 9→10 = **{r10:.2f}**, Grade 10→11 = **{r11:.2f}**, "
        f"Grade 11→12 = **{r12:.2f}**. **Incoming Grade 9** is held at the recent "
        f"3-year average of **{g9_incoming:.0f}** students per year."
        )

        # Small table of projected totals.
        show = proj_table[["School year", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "Projected total"]]
        st.dataframe(
            show.style.format({c: "{:,}" for c in ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "Projected total"]}),
            width="stretch", hide_index=True,
        )

    # ---------------------------------------------------------------------------
    # 4) Methodology + cross-link
    # ---------------------------------------------------------------------------

    st.subheader("How the projection works")
    st.markdown(
        "This is a **grade-progression (cohort-survival) model**, the simplest standard "
    "approach to short-term enrollment forecasting:\n\n"
    "- For each grade transition, we compute the ratio of next year's grade count to "
    "this year's grade below it (e.g. Grade 10 next year ÷ Grade 9 this year), and "
    "average it over the most recent year-pairs to smooth out noise.\n"
    "- Incoming **Grade 9** is held flat at the recent multi-year average, since the "
    "size of each entering class depends on choices among Lynn's high schools that "
    "this model cannot predict.\n"
    "- We then roll the current grades forward three years.\n\n"
    "Real enrollment depends on **school choice, family migration, housing, and program "
    "or policy changes** that aggregate counts simply cannot see. The numbers above are "
    "a transparent baseline for capacity planning — not a roster-level forecast."
    )

    crosslink_callout(
        "This projection is a simple model on aggregate counts — see the limits of what the data can tell us.",
        "Methodology", "What we don't know →",
    )

    # ---------------------------------------------------------------------------
    # 5) Data downloads + footer
    # ---------------------------------------------------------------------------

    data_downloads_panel({
        "Feeder snapshot": feeder_snapshot,
        "LEHS enrollment projection": proj_table,
    })

page_footer()
