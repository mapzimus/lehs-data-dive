"""
Section 18 — Lynn Overview.

A wider community view: demographics, economy, housing, geography, history.
City-level statistics (not just tract or school). Source data:
  - US Census ACS 5-year 2023 at place level → scripts/14_download_lynn_city_stats.py
  - US Decennial Census 1790-2020 → static-but-sourced historical population
  - MassGIS for area + boundary facts
  - Lynn city + Wikipedia for static contextual facts (with date stamps)
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, data_downloads_panel
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="Lynn Overview | LEHS", page_icon="🏙️", layout="wide",
)
sidebar_attribution()

st.title("Lynn, Massachusetts — City Overview")
st.markdown(
    "A wider community view of the city Lynn English serves. Where the rest of "
    "this dashboard tracks the school, this page tracks **the place**: who "
    "lives here, what they do for work, where they came from, how much it "
    "costs to live here, and what shapes the geography. Data is most recent "
    "ACS 5-year (2019–2023 estimates) unless noted."
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

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
    st.stop()

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


# ---------------------------------------------------------------------------
# 1. Headline
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 2. Population over time (decadal census — static, well-documented)
# ---------------------------------------------------------------------------

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
                  xaxis_title="Decennial Census year",
                  title="Lynn population, 1790–2020 (US Decennial Census)")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 3. Age pyramid
# ---------------------------------------------------------------------------

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
                       title="Lynn age pyramid — ACS 2019-2023",
                       xaxis_title="Population (left = male, right = female)",
                       yaxis_title="Age band")
    fig.update_xaxes(tickformat=",.0f", tickvals=[-5000, -2500, 0, 2500, 5000],
                     ticktext=["5K", "2.5K", "0", "2.5K", "5K"])
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# 4. Race + ethnicity
# ---------------------------------------------------------------------------

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
                      title="Race / ethnicity composition (note: race and Hispanic origin overlap per Census)",
                      yaxis_title="", xaxis_title="People")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Census reports race and Hispanic origin separately, so people may "
        "appear in multiple bars (e.g., Hispanic + White-alone). The "
        "*White, non-Hispanic* bar is the single mutually-exclusive Hispanic-excluded category."
    )

st.divider()

# ---------------------------------------------------------------------------
# 5. Foreign-born population + birthplaces
# ---------------------------------------------------------------------------

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
    # Split into "regional rolls" vs specific countries for two distinct charts
    is_roll = birthplaces["country"].str.contains("total", case=False, na=False)
    specific = birthplaces[~is_roll & (birthplaces["country"] != "Foreign-born total")]
    specific = specific.sort_values("count", ascending=True).tail(15)
    fig = px.bar(specific, y="country", x="count", orientation="h",
                 color="count", color_continuous_scale="Plasma",
                 title="Top countries of birth — Lynn foreign-born residents")
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

st.divider()

# ---------------------------------------------------------------------------
# 6. Languages spoken at home
# ---------------------------------------------------------------------------

st.header("Languages spoken at home")
st.caption(
    "Census ACS C16001 — population age 5+. Lynn's language diversity directly "
    "feeds the LEHS English Learner pipeline (Pages 3 + 9)."
)
if not languages.empty:
    lang_total_row = languages[languages["language"].str.contains("Total", case=False, na=False)]
    lang_total = int(lang_total_row["count"].iloc[0]) if not lang_total_row.empty else None

    lang_show = languages[~languages["language"].str.contains("Total", case=False, na=False)].copy()
    lang_show = lang_show.sort_values("count", ascending=True)
    fig = px.bar(lang_show, y="language", x="count", orientation="h",
                 color_discrete_sequence=[LEHS_NAVY])
    fig.update_layout(**DEFAULT_LAYOUT,
                      title=f"Languages spoken at home (Lynn, pop 5+: {lang_total:,})" if lang_total else "Languages",
                      yaxis_title="", xaxis_title="Speakers")
    st.plotly_chart(fig, use_container_width=True)

    if lang_total:
        eng = lang_show[lang_show["language"].str.contains("English", case=False, na=False)]["count"].sum()
        non_eng = lang_total - eng
        st.success(
            f"**{non_eng:,} Lynn residents speak a language other than English at home** "
            f"({non_eng / lang_total:.0%} of population 5+). Spanish is by far the largest, "
            f"followed by Russian/Polish/Slavic and Arabic groups."
        )

st.divider()

# ---------------------------------------------------------------------------
# 7. Economy — income + poverty
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 8. Employment by industry
# ---------------------------------------------------------------------------

st.header("Employment by industry")
if not industries.empty:
    ind_sorted = industries.sort_values("employed", ascending=True)
    fig = px.bar(ind_sorted, y="industry", x="employed", orientation="h",
                 color="employed", color_continuous_scale="Viridis",
                 title="Civilian employed population by industry sector (ACS S2403)")
    fig.update_layout(**DEFAULT_LAYOUT, height=520, showlegend=False,
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

st.divider()

# ---------------------------------------------------------------------------
# 9. Housing
# ---------------------------------------------------------------------------

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

# Year built distribution
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
                  color="units", color_continuous_scale="Cividis",
                  title="When Lynn's housing was built (units by year-built band)")
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
            f"on the Community Context page."
        )

st.divider()

# ---------------------------------------------------------------------------
# 10. Commute
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 11. Geography
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 12. Education context (links into the rest of the dashboard)
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 13. History highlights
# ---------------------------------------------------------------------------

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

st.divider()

# ---------------------------------------------------------------------------
# 14. Related dashboard pages
# ---------------------------------------------------------------------------

st.header("Where to go next")
st.markdown(
    """
- **[School Profile](./School_Profile)** — LEHS-specific student demographics
  and the school as a snapshot of Lynn.
- **[Community Context](./Community_Context)** — tract-level Census ACS +
  EJScreen + CDC PLACES for Lynn's 22 census tracts.
- **[All Lynn Schools](./All_Lynn_Schools)** — every K-12 school in LPS,
  filterable + sortable.
- **[Lynn District Dashboard](./Lynn_District_Dashboard)** — Lynn vs.
  Gateway median vs. State median on accountability indicators.
- **[Catchment Research](./Catchment_Research)** — Maxwell's original
  geospatial work on student address + absenteeism patterns.
"""
)

# >>> auto: csv downloads <<<
data_downloads_panel({
    "Lynn city headline stats (ACS)": city,
    "Birthplaces (B05006)": birthplaces,
    "Languages spoken at home (C16001)": languages,
    "Employment by industry (S2403)": industries,
    "Commute mode (S0801)": commute,
    "Age × sex (S0101)": age_pyramid,
    "Decadal population 1790–2020": decadal,
})
