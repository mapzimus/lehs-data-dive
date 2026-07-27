"""About the Data — methodology & sources, data 101, known gaps, corrections log."""
from __future__ import annotations

import streamlit as st
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, year_axis
from utils.constants import SEQ_BRAND
from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.constants import LEHS_NAVY
from utils.constants import PROJECT_ROOT  # PROJECT_ROOT exists in utils/constants.py
st.set_page_config(page_title="About the Data | LEHS", page_icon="📚", layout="wide")
sidebar_attribution()

st.title("About the Data")
st.markdown(
    "Everything about how this dashboard is built: where the numbers come "
    "from, how to read the charts, what the data *cannot* show, and a public "
    "log of every correction shipped. Pick a tab below."
)
_tab_0, _tab_1, _tab_2, _tab_3 = st.tabs(['📚 Methodology & Sources', '📖 Data 101', "🔎 What We Don't Know", '📝 Corrections'])

with _tab_0:
    # ==== from pages/99_Methodology.py ====
    st.header("Methodology & Data Sources")
    st.markdown(
        "Every number in this dashboard traces back to a public source. The "
    "dashboard is built on **50+ processed datasets drawn from ~10 public "
    "sources**. This page lists those sources, defines the common data "
    "fields, and spells out the suppression rules and important caveats."
    )

    st.header("About this dashboard")
    st.markdown(
        """
**What it is.** A free, public data dashboard about **Lynn English High
School** (LEHS) — the largest comprehensive high school in Lynn,
Massachusetts. It pulls together enrollment, MCAS, coursework, English
Learner, college-and-career, accountability, staffing, finance, discipline,
and neighborhood-context data that are normally scattered across a dozen
state and federal websites, and presents them in one place.

**Why it exists.** Most of this information is public but hard to find, hard
to compare year-over-year, and dense with agency jargon. The goal is to make
LEHS's story legible to the people with a stake in it — **students, families,
teachers, school leaders, and community members** — without requiring a
spreadsheet or a glossary of DESE codes.

**Who built it.** Built and maintained by **Maxwell Howe**
([maxwellhowegis.com](https://maxwellhowegis.com)) as an independent project.
It is **not** an official publication of Lynn Public Schools or the
Massachusetts Department of Elementary and Secondary Education; every figure
traces back to the public sources listed below so you can check the work
yourself.
"""
    )

    st.divider()

    # The whole reference family now lives on this page as tabs.
    st.info(
        "**The reference family:** this tab covers *sources, fields, and "
    "caveats*. For how to read the charts see the **Data 101** tab, and for "
    "the honest limits of what's measurable see **What We Don't Know**."
    )

    # Annual PDF download — built by scripts/13_build_annual_report.py
    _pdf_path = Path(__file__).resolve().parent.parent / "reports" / "state_of_lehs_2026.pdf"
    if _pdf_path.exists():
        with open(_pdf_path, "rb") as _f:
            st.download_button(
                "📄 Download the State of LEHS 2026 (PDF)",
                data=_f.read(),
                file_name="state_of_lehs_2026.pdf",
                mime="application/pdf",
            )

    st.header("Data sources")

    sources = [
        ("E2C Hub", "educationtocareer.data.mass.gov",
         "Socrata-hosted DESE open data — MCAS, graduation, AP, enrollment, attendance, finance, staffing, plans, pathways, postsecondary"),
        ("DESE Profiles statereport", "profiles.doe.mass.edu/statereport/",
         "Bulk CSVs — discipline, VOCAL climate, accountability, ACCESS for ELLs (the state English-proficiency test for English Learners), detailed staffing"),
        ("DESE accountability workbooks", "doe.mass.edu/accountability/lists-tools",
         "Five annual xlsx workbooks behind the State Accountability page — determinations, criterion-referenced indicator detail, targets, and percentile research files (full breakdown below)"),
        ("Civil Rights Data Collection (CRDC)", "civilrightsdata.ed.gov",
         "Federal biennial — granular discipline by race × disability × gender, restraint, school-based arrests, AP offerings, athletic participation"),
        ("IPEDS", "nces.ed.gov/ipeds",
         "Federal postsecondary — grad rates and outcomes at the colleges Lynn grads attend"),
        ("Census ACS 5-year", "data.census.gov",
         "Lynn community context — income, language, parental education, housing"),
        ("Census SAIPE", "census.gov/programs-surveys/saipe",
         "School district child poverty estimates"),
        ("EPA EJScreen", "ejscreen.epa.gov",
         "Environmental justice indicators around the school"),
        ("CDC PLACES", "cdc.gov/places",
         "Local adult health indicators"),
        ("MA Department of Higher Education", "mass.edu",
         "Public postsecondary enrollment, retention, awards"),
        ("MaxPreps", "maxpreps.com",
         "Season-by-season Athletics records (team results, standings) powering the Athletics page — complemented by a hand-curated history file (assets/curated/lehs_athletics_history.yaml: Hall of Fame, Manning Bowl, legacy coaches)"),
        ("DESE local files", "—",
         "reporting-element4.xlsx (former-EL MCAS), state.docx (the WIDA ACCESS 2025 English-proficiency test results)"),
    ]

    for name, url, desc in sources:
        st.markdown(f"**{name}** — `{url}`")
        st.caption(desc)
        st.markdown("")

    st.subheader("DESE accountability workbooks")

    st.markdown(
        """
The **[State Accountability](/Accountability?embed=true)** page is built from
**five public DESE workbooks** published on the accountability
[lists-and-tools page](https://www.doe.mass.edu/accountability/lists-tools/)
(`doe.mass.edu/accountability/lists-tools`). They are downloaded by
`scripts/19_download_accountability_detail.py` and processed into parquet by
`scripts/16_process_dese_profiles.py`:

1. **`accountability-data-{year}.xlsx`** — one row per school: overall
   classification, the 1–99 accountability percentile, criterion-referenced
   target percentages, federal designation, and any low-performing student
   groups → `accountability_summary.parquet`.
2. **`criterion-referenced-percentage-{year}.xlsx`** — every indicator ×
   student group, with prior and current value, change, target, N, points
   earned, rating, and the rating reason. The HS sheet carries schools →
   `accountability_indicators.parquet`; the middle/high-school (MSHS) sheet carries the state and
   district rows used as benchmarks → `accountability_benchmarks.parquet`.
3. **`accountability-targets-{year}.xlsx`** — baselines plus this-year and
   next-year targets with annual increments, per school × student group →
   `accountability_targets.parquet`. Note the direction: **dropout and
   chronic-absenteeism targets decrease** — they are reduction targets, so a
   lower number is the goal.
4. / 5. **`school-percentile-{year}.xlsx`** and
   **`student-group-percentile-{year}.xlsx`** — the statewide percentile
   build-up per indicator. Percentiles blend **three years of data, weighted
   15% / 25% / 60%** (oldest → newest) → `accountability_percentiles.parquet`.

**How DESE scores it (the short version).** Each indicator earns **0–4
points** per student group. Points are weighted by category — for *All
Students*: Achievement 40, Growth 20, HS completion 20, English-language
proficiency (ELP) 10, Additional indicators 10; for the *Lowest Performing* group:
67.5 / 22.5 / 10 (no HS-completion or English-language-proficiency weight). The **annual**
criterion-referenced percentage is the weighted share of possible points;
the **cumulative** figure blends prior year × 40% with current year × 60%;
a cumulative percentage of **75% or higher reads as "meeting targets."**

**Suppression and lag caveats specific to these files:** DESE blanks small-n
cells before publication; implausible placeholder scaled scores (outside the
400–600 MCAS range) are nulled at ingest; and some indicators lag a year
behind the determination year — graduation, dropout, and extended
engagement.
"""
    )

    st.divider()

    st.header("Naming conventions")

    st.markdown(
        """
The dashboard uses three distinct scopes of "Lynn." Read these
consistently:

- **LEHS** — Lynn English High School. The single school this dashboard is
  about (ORG_CODE `01630510`).
- **Lynn district** / **LPS** — Lynn Public Schools, the K-12 district
  that contains LEHS plus 25 other schools — 26 in all (DIST_CODE
  `01630000`).
- **Lynn** (alone) — the city/place of Lynn, Massachusetts. Used for
  Census, demographics, geography.
- **Lynn Classical** / **Lynn Tech** / **Frederick Douglass** /
  **Harold Durgin** — specific Lynn sibling high schools, always spelled
  out by name.

When a chart contrasts LEHS with another scope, the legend says which
scope. "Lynn" alone never refers to LEHS.
"""
    )

    st.divider()

    st.header("Field glossary — the columns you'll meet")

    st.markdown(
        """
The processed datasets share a small set of DESE field names. The ones
worth knowing:

- **`ORG_CODE`** — the 8-digit code for a single organization (school or
  district). LEHS is `01630510`; the Lynn district is `01630000`. Every
  row ties to one `ORG_CODE`.
- **`ORG_TYPE`** — whether a row describes a `School`, a `District`, or
  the `State`. The same metric is reported at all three levels, so this
  is how a school number is told apart from its district rollup.
- **`SY`** — the **school year**, stored as the spring/ending calendar
  year. `SY = 2026` means the **2025–26** school year (the latest in the
  data); `SY = 2024` means 2023–24, ending June 2024.
- **`STU_GRP`** — the **student group** a row covers: `All Students`, or
  a subgroup such as `English Learner`, `Low Income`, `Students w/
  Disabilities`, or a race/ethnicity. Subgroup rows are what power the
  gap charts — and what get suppressed below n=10 (see caveats).

Other recurring fields (`DIST_CODE`, `TOTAL_CNT`, `*_PCT`, `*_CNT`) follow
the same pattern: a district code, a count, or a percentage of the row's
student group.
"""
    )

    st.divider()

    st.header("Peer cohort framework")

    st.markdown(
        """
The dashboard uses three peer-comparison cohorts, each in its dedicated
home so the rest of the pages can stay LEHS-focused:

1. **Lynn sibling high schools** (LEHS vs. Lynn Classical, Lynn Tech,
   Frederick Douglass, Harold Durgin) — the same-district, same-policies
   comparison. Lives on the **[Lynn Schools](/Lynn_Schools?embed=true)** page under
   the Compare group. Differences here isolate school-level practices
   (curriculum, discipline policy, English Learner programming) from city-wide
   demographics. Where surviving chart contrasts on other pages (Finance,
   Discipline) include Classical alongside LEHS, Lynn Tech is included
   too.
2. **Lynn Public Schools as a whole** — district context, 26 schools.
   Shown on the **[Lynn District](/Lynn_District?embed=true)** *Snapshot* tab and
   referenced on other pages where the district benchmark adds context.
3. **26 Massachusetts Gateway Cities** — main comprehensive HS of each
   peer city. Shown on the **[Gateway Cities](/Gateway_Peer_Comparison?embed=true)**
   page and as a scatter cloud on the
   **[Cross-Topic Explorer](/Correlation_Lab?embed=true)**. This is the
   across-cities benchmark.

LEHS-focused pages (School Profile, MCAS, Courses & Academics, English
Learners, College & Career, Success After HS, Teachers & Workforce,
Finance, Discipline & Climate, Where Students Live)
lead with LEHS's own story. School-to-school comparison lives on the
Compare → Lynn Schools page; cross-city comparison lives on Compare →
Gateway Cities.
"""
    )

    st.divider()

    st.header("Important caveats")

    st.markdown(
        """
- **Suppression**: DESE suppresses student-group cells with fewer than 10 students. These show as blank.
- **Definitions change**: "Economically Disadvantaged" (2015–2021) vs. "Low Income" (pre-2015 and 2022+) use different formulas. See [DESE Researcher's Guide](https://www.doe.mass.edu/infoservices/research/guide.html).
- **Earnings data paused**: Average Earnings of HS Graduates by Industry — DESE paused updates in 2025 due to a methodology issue affecting students who didn't attend MA public postsecondary institutions.
- **VOCAL participation**: not all schools participate every year — LEHS coverage is noted where it appears.
- **ACS geography**: We use whole-city Lynn ACS rather than a precise LEHS catchment area. The catchment is roughly the eastern half of the city but exact boundaries are not published.
- **CRDC frequency**: Federal CRDC data is biennial. The latest public-use release reflects the **2021-22** school year — a pandemic-recovery year. Its support-staff ratios live on [Teachers & Workforce](/Teachers_and_Workforce?embed=true), advanced-course offerings on [Courses & Academics](/Courses_and_Academics?embed=true), and disaggregated discipline on [Discipline & Climate](/Discipline_and_Climate?embed=true). The public-use file applies small random perturbations to protect privacy, so counts are approximate.
- **Correlation ≠ causation**: The Correlation Lab surfaces patterns. Confirming cause-and-effect requires more than this dashboard can show.
"""
    )

    st.divider()

    st.header("How to reproduce / refresh")

    st.code(
        """
# Clone + set up Python env
git clone https://github.com/mapzimus/lehs-data-dive
cd lehs-data-dive
conda env create -f dev/environment.yml
conda activate lehs

# Pull every source dataset
python scripts/01_download_e2c.py        # MA DESE E2C Hub (~1.7 GB raw CSVs)
python scripts/09_download_massgis.py    # MassGIS shapefiles
CENSUS_API_KEY=your-key python scripts/10_download_census_acs.py
python scripts/19_download_accountability_detail.py  # DESE accountability workbooks (5 xlsx)

# Filter + process
python scripts/08_build_master_panel.py  # → data/processed/*.parquet
python scripts/11_build_lynn_geo.py      # → data/processed/*.geojson
python scripts/16_process_dese_profiles.py  # → accountability_*.parquet

# Run the dashboard locally
streamlit run Home.py
""",
        language="bash",
    )

    st.markdown(
        """
**Live versions:**
- **Dashboard** — https://maxwellhowegis.com/lynndata/
- **MA Education Atlas** (standalone statewide map) — https://maxwellhowegis.com/ma-atlas/
- **Source code** — https://github.com/mapzimus/lehs-data-dive
"""
    )

with _tab_1:
    # ==== from pages/Data_Literacy.py ====
    # ---------------------------------------------------------------------------
    # Hero
    # ---------------------------------------------------------------------------

    st.header("Data 101 — Reading the Charts")
    st.markdown(
        "This dashboard is full of numbers, percentages, and graphs. If you've "
    "never opened a dashboard before, **this is the page to start on**. "
    "No background required — by the end you'll know what every chart on "
    "the site is trying to tell you."
    )

    st.info(
        "📚 **Who this is for:** Anyone new to data — especially LEHS and "
    "Lynn Public Schools students who want to understand the numbers "
    "about their own school. Teachers and curious community members "
    "welcome too. You can skip around using the sections below."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 1 — What's a dataset?
    # ---------------------------------------------------------------------------

    st.header("1. What is a dataset?")

    st.markdown(
        """
A **dataset** is just a table — like a really big spreadsheet. Each
**row** is a *thing* you're tracking. Each **column** is a *fact* about
that thing. Here's a tiny example, the kind of row you'd see in the
real enrollment dataset behind this dashboard:
"""
    )

    demo_dataset = pd.DataFrame(
        {
            "School Year": ["2023–24", "2024–25", "2025–26"],
            "School": ["Lynn English High"] * 3,
            "Total Students": [1_690, 1_705, 1_727],
            "% English Learners": ["38%", "40%", "42%"],
            "% Low Income": ["72%", "74%", "75%"],
        }
    )
    st.dataframe(demo_dataset, hide_index=True, width="stretch")

    st.markdown(
        """
- Three **rows**, one per school year.
- Five **columns**, each measuring something different.
- The actual dataset behind the [School Profile](/School_Profile?embed=true) page
  has thousands of rows like these going back to 1992 — but the
  shape is the same.

**A database** is the bigger thing: a *collection of related datasets*
all kept together. This dashboard sits on top of **50+ datasets across
~10 public sources** — MA DESE, the US Census, federal civil-rights
data, athletics records, and original LPS research. Each chart you'll
see is a way of *looking at* one or more of those tables.
"""
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 2 — Chart types (the main event)
    # ---------------------------------------------------------------------------

    st.header("2. Chart types and what each one is for")

    st.markdown(
        "Different chart types answer different questions. Pick the wrong "
    "chart and the story gets lost. Here are the ones this dashboard "
    "uses most — with a tiny example of each."
    )

    # --- Bar chart ---
    st.subheader("📊 Bar chart — *comparing categories*")

    bc_df = pd.DataFrame(
        {
            "School": ["LEHS", "Classical", "Tech", "Frederick Douglass", "Harold Durgin"],
            "Enrollment": [1_727, 1_513, 1_566, 364, 98],
        }
    )
    fig = px.bar(
        bc_df, x="School", y="Enrollment", text="Enrollment",
        color_discrete_sequence=[LEHS_NAVY],
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**DEFAULT_LAYOUT, height=320, showlegend=False)
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
- **Use when:** comparing a value across discrete categories (here:
  schools).
- **What to look for:** which bar is tallest, how the bars rank, how
  big the gaps are between bars.
- **In this dashboard:** every page that ranks schools, subjects, or
  subgroups uses a bar chart.

👀 **See it in action:** the [Lynn Schools](/Lynn_Schools?embed=true) page is
wall-to-wall bar charts comparing LEHS to its four sibling high schools.
"""
    )

    # --- Line chart ---
    st.subheader("📈 Line chart — *change over time*")

    yrs = list(range(2017, 2026))
    line_df = pd.DataFrame(
        {
            "Year": yrs * 2,
            "Subject": ["ELA"] * len(yrs) + ["Math"] * len(yrs),
            "% Meeting + Exceeding": [
                0.44, 0.45, 0.47, None, 0.42, 0.46, 0.48, 0.50, 0.51,
                0.32, 0.33, 0.35, None, 0.28, 0.31, 0.34, 0.36, 0.38,
            ],
        }
    ).dropna()
    fig = px.line(
        line_df, x="Year", y="% Meeting + Exceeding",
        color="Subject", markers=True,
        color_discrete_map={"ELA": LEHS_NAVY, "Math": LEHS_GOLD},
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=320, yaxis_tickformat=".0%")
    year_axis(fig)
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
- **Use when:** showing how a value *changes* across time.
- **What to look for:** the slope (going up or down?), sharp jumps
  (something happened that year), gaps (data wasn't collected — note
  the missing 2020 point above, when COVID cancelled MCAS).
- **In this dashboard:** MCAS trends, enrollment over decades,
  graduation rates by cohort year.

👀 **See it in action:** [MCAS](/Academic_Performance?embed=true)
opens with multi-year MCAS line charts — including that real 2020 gap.
"""
    )

    # --- Histogram ---
    st.subheader("📉 Histogram — *how things are distributed*")

    rng = np.random.default_rng(seed=42)
    hist_data = rng.normal(loc=70, scale=12, size=400)
    hist_data = np.clip(hist_data, 30, 100)
    fig = px.histogram(
        pd.DataFrame({"Test Score": hist_data}),
        x="Test Score", nbins=20, color_discrete_sequence=[LEHS_NAVY],
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=320, yaxis_title="# of students")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
- **Use when:** you want to see the *shape* of a single column of
  numbers — where most values cluster, how spread out they are, where
  the outliers sit.
- **What to look for:** the peak (the **mode**, most common value),
  the spread (narrow = consistent, wide = lots of variation), the
  tails (a few students way below or way above the rest).
- **Histogram ≠ bar chart**: a bar chart compares categories (apples
  vs. oranges). A histogram chops a *single number* into ranges and
  shows how many values fall in each range.
- **In this dashboard:** MCAS achievement-level distributions, school
  enrollment-size distributions across all MA gateway cities.
"""
    )

    # --- Scatter plot ---
    st.subheader("🔵 Scatter plot — *relationship between two things*")

    scatter_df = pd.DataFrame(
        {
            "% Low Income": np.linspace(0.20, 0.90, 26)
            + rng.normal(0, 0.04, 26),
            "% Meeting + Exceeding (ELA)": np.linspace(0.65, 0.30, 26)
            + rng.normal(0, 0.06, 26),
            "City": [
                "Brockton", "Chelsea", "Chicopee", "Everett", "Fall River",
                "Fitchburg", "Haverhill", "Holyoke", "Lawrence", "Leominster",
                "Lowell", "Lynn", "Malden", "Methuen", "New Bedford",
                "Peabody", "Pittsfield", "Quincy", "Revere", "Salem",
                "Springfield", "Taunton", "Westfield", "Worcester",
                "Attleboro", "Barnstable",
            ],
        }
    )
    fig = px.scatter(
        scatter_df, x="% Low Income", y="% Meeting + Exceeding (ELA)",
        hover_name="City", color_discrete_sequence=[LEHS_NAVY],
        trendline="ols",
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=350,
                       xaxis_tickformat=".0%", yaxis_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
- **Use when:** asking *"do these two things move together?"*. One
  variable on the X axis, another on Y, every dot is one observation.
- **What to look for:** if dots form a sloping pattern, the two things
  are *correlated* (move together). The line through the cloud is a
  **trend line** — it summarizes the average pattern.
- **Warning:** correlation is not causation (Section 4). Two things
  can move together without one *causing* the other.
- **In this dashboard:** the [Cross-Topic Explorer](/Correlation_Lab?embed=true)
  is built entirely around scatter plots — pick any two metrics across
  MA's 26 Gateway cities and see if they move together.

👀 **See it in action:** head to the
[Cross-Topic Explorer](/Correlation_Lab?embed=true) and build your own
scatter plot with two metrics you're curious about.
"""
    )

    # --- Choropleth-style explanation ---
    st.subheader("🗺️ Choropleth map — *geography*")

    st.markdown(
        """
A **choropleth** is a map where each shape (state, town, neighborhood,
census tract) is *colored* by a value — darker means more, lighter
means less. It answers *"where is this happening?"* questions.

You'll see two flavors on this dashboard:
- **City-scale:** Lynn's 22 census tracts shaded by % Low Income,
  language at home, or chronic absence — on the
  [City → Neighborhoods tab](/Lynn_City?embed=true) and on the
  [Maps page](/Maps?embed=true).
- **State-scale:** all 351 MA municipalities shaded by school
  performance, demographics, or finance — on the standalone
  [MA Education Atlas](https://maxwellhowegis.com/ma-atlas/).

👀 **See it in action:** the [Maps](/Maps?embed=true) page is the launch pad
for both interactive maps — try shading Lynn's tracts by a metric you care about.
"""
    )

    # --- Heatmap ---
    st.subheader("🔥 Heatmap — *patterns across two dimensions*")

    heat_df = pd.DataFrame(
        {
            "Grade": list("3 4 5 6 7 8 10".split()) * 3,
            "Subject": (["ELA"] * 7) + (["Math"] * 7) + (["Science"] * 7),
            "% M+E": [
                0.39, 0.41, 0.42, 0.40, 0.43, 0.45, 0.49,
                0.32, 0.30, 0.28, 0.27, 0.29, 0.31, 0.34,
                None, None, 0.30, None, None, 0.36, 0.41,
            ],
        }
    )
    heat_pivot = heat_df.pivot(index="Subject", columns="Grade", values="% M+E")
    fig = go.Figure(
        data=go.Heatmap(
            z=heat_pivot.values, x=heat_pivot.columns, y=heat_pivot.index,
            colorscale=SEQ_BRAND, text=heat_pivot.values,
            texttemplate="%{text:.0%}", textfont={"size": 12},
            zmin=0, zmax=0.6,
        )
    )
    fig.update_layout(**DEFAULT_LAYOUT, height=280, xaxis_title="Grade",
                       yaxis_title="Subject")
    st.plotly_chart(fig, width="stretch")

    st.markdown(
        """
- **Use when:** you want to see patterns across *two* category
  dimensions at once (here: subject × grade).
- **What to look for:** which cells are darkest (highest values),
  whether one row or column stands out from the others.
- **In this dashboard:** subject-by-grade MCAS performance grids,
  attendance × subgroup tables.
"""
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 3 — How to read a percentage
    # ---------------------------------------------------------------------------

    st.header("3. How to read a percentage")

    st.markdown(
        """
Percentages are everywhere on this dashboard. They look simple, but
they hide a few traps.

**A percentage is always "out of what?"**
When you see *"42% of LEHS students are English Learners"*, the
**"out of"** is the school's total enrollment — about 1,727 students.
So that's roughly 725 EL students. The percentage *normalizes* the
count so you can compare schools of different sizes.

**Percentage vs. percentage points**
If LEHS's graduation rate goes from 80% to 85%, that's a **5
percentage-point** increase. It is **not** a 5% increase — a 5%
increase from 80% would only get you to 84%. The two phrases mean
different things and journalists mix them up constantly. On this
dashboard, when we say "+5 pts" we mean percentage points.

**Compared to what?**
A single percentage isn't useful by itself. *75% Low Income* sounds
high — but compared to what? On the dashboard you'll always see
percentages next to peer comparisons:
- LEHS's same-district sibling schools
- LPS as a whole
- Other MA Gateway cities (Lawrence, Holyoke, Springfield, …)
- The state average

That's why almost every chart has multiple colored lines or bars
side-by-side — single numbers without context can mislead.
"""
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 4 — Common pitfalls
    # ---------------------------------------------------------------------------

    st.header("4. Common pitfalls — what to watch for")

    with st.expander("**Mean vs. median** — averages can lie", expanded=False):
        st.markdown(
            """
The **mean** is what most people call "the average" — add up all the
values and divide by how many. The **median** is the middle value when
you sort everything from low to high.

When a few extreme values are pulling the mean around, the median
gives you a fairer picture. Classic example: median household income
in Lynn is **\\$74,715**. The *mean* would be higher, because a small
number of very-wealthy households pull the average up while the typical
Lynn household sits at the median.

This dashboard reports **median** household income, and uses median
home values, median rent, etc. — to keep outliers from skewing the
story.
"""
        )

    with st.expander("**Sample size** — 100% of 4 students vs. 100% of 1,000", expanded=False):
        st.markdown(
            """
If a school reports "100% of seniors took the SAT", that means very
different things at LEHS (~400 seniors) than at a tiny program (~10
seniors). Small sample sizes are noisy — one or two unusual students
can swing the percentage wildly.

This is why DESE **suppresses** subgroup numbers below n=10 — the
percentage would be too unstable to publish, and it would also risk
identifying individual students. When you see "—" or "DS" (Data
Suppressed) in a chart, that's why.
"""
        )

    with st.expander("**Correlation ≠ causation** — moving together isn't the same as causing", expanded=False):
        st.markdown(
            """
On a scatter plot, if % Low Income and % Meeting MCAS slope downward
together, it's tempting to say "low income causes lower scores". But
correlation just means two things move together — it doesn't say
which causes which, or whether something *else* (housing, healthcare,
family time, instructional minutes) is causing both.

The [Cross-Topic Explorer](/Correlation_Lab?embed=true) is for *spotting*
correlations across MA's 26 gateway cities. Use it to ask questions,
not to declare causes.
"""
        )

    with st.expander("**Year-over-year noise vs. real trends**", expanded=False):
        st.markdown(
            """
Any single year's data can wobble for reasons that have nothing to do
with the school: a tough testing day, a cohort that happened to have
more EL students, COVID cancellations (2020).

A real trend shows up across multiple years — three points in a row
going the same direction is much more convincing than one big jump.
That's why most trend charts on this dashboard go back 5+ years.
"""
        )

    with st.expander("**Confidence intervals** — the fuzzy bars on some charts", expanded=False):
        st.markdown(
            """
When a chart shows a number with little error bars above and below
(or a shaded band around a line), those are **confidence intervals**.
They tell you how *certain* the measurement is.

A short bar = we're confident in the number. A long bar = the
underlying sample is small or noisy, so the "real" value could be
anywhere in that range. **If two confidence intervals overlap, the
two numbers might actually be the same** — don't read too much into
the difference between them.

👀 **See it in action:** the MCAS trend charts on
[MCAS](/Academic_Performance?embed=true) are where to
practice telling a real trend from year-to-year noise.
"""
        )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 5 — Try it
    # ---------------------------------------------------------------------------

    st.header("5. Try it yourself")

    st.markdown(
        """
Now you know how to read everything on this site. A few suggested
places to practice:

- **[School Profile](/School_Profile?embed=true)** — bar charts and trend lines
  showing who attends LEHS. Compare year-over-year.
- **[MCAS](/Academic_Performance?embed=true)** — MCAS line
  charts with confidence intervals. Look for trend vs. noise.
- **[Cross-Topic Explorer](/Correlation_Lab?embed=true)** — scatter plots across
  26 MA gateway cities. Pick any two metrics and look for
  correlation. Remember: correlation ≠ causation.
- **[Maps](/Maps?embed=true)** — choropleths at the city and statewide scale.

If anything on the dashboard is confusing, the explanation is
probably back on this page. Bookmark it and come back."""
    )

    st.divider()
    st.caption(
        "Built for students, by a teacher. If you spot something that's "
    "still confusing or want a chart type covered that isn't here, let "
    "Maxwell know via the GitHub link in the footer."
    )

with _tab_2:
    # ==== from pages/Data_Gaps.py ====
    # ---------------------------------------------------------------------------
    # Hero
    # ---------------------------------------------------------------------------

    st.header("What We Still Don't Know")
    st.markdown(
        "A dashboard is only as trustworthy as it is honest about its blind "
    "spots. This page is the catalog of things this site **cannot** show "
    "you — and *why*. Some gaps are about what public agencies publish; "
    "some are about geography; some are about how small numbers get "
    "suppressed to protect students' privacy. None of them are secrets."
    )

    st.info(
        "This tab extends the **Important caveats** section on the "
    "**Methodology & Sources** tab. Where a limitation is fully "
    "documented there, we link rather than repeat it. The goal here is one "
    "honest, browsable list of every meaningful gap."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # 1. Student wellbeing / mental health
    # ---------------------------------------------------------------------------

    st.header("1. Student wellbeing & mental health")

    with st.expander("What we'd like to show — and why we can't", expanded=True):
        st.markdown(
            """
**What we'd like to show.** Student-reported wellbeing: mental health,
vaping, sleep, food insecurity, and the kinds of questions a Youth Risk
Behavior Survey (MYRBS) asks — broken out at the school or district level.

**Why we can't.** DESE does not publish student-reported health and
mental-health data at the school/district level in the Education-to-Career
(E2C) pipeline this dashboard is built on. The youth survey results that do
exist are aggregated to a scale that doesn't isolate LEHS or even Lynn.

**The proxy we use instead.** The closest available signals are **adult,
census-tract-level CDC PLACES** health indicators (not student-specific),
plus **chronic-absenteeism** and **counselor-to-student ratios** as
indirect wellbeing measures. These gesture at the question; they don't
answer it.

*In progress:* a dedicated **Wellbeing** page may attempt a district-level
youth-survey ingest. Treat it as experimental — the underlying series may
turn out to be unavailable or too aggregated to publish responsibly.
        """
        )

    # ---------------------------------------------------------------------------
    # 2. Charter schools
    # ---------------------------------------------------------------------------

    st.header("2. Charter schools (e.g. KIPP Academy Lynn)")

    with st.expander("Why KIPP isn't shown side-by-side", expanded=False):
        st.markdown(
            """
**What we'd like to show.** A Lynn family weighing **KIPP Academy Lynn**
against the district high schools should be able to compare them on the
same charts.

**Why we can't.** Commonwealth charter schools are their own districts;
they are **not part of the Lynn Public Schools datasets** that drive this
dashboard. Pulling KIPP in would mean a separate ingest with its own codes,
and the comparison would need careful caveats (charters enroll by lottery,
not by attendance area).

**The workaround.** Where charter options matter to a family's decision, we
point to them on the [Lynn HS Options](/Lynn_Schools) page rather than
folding charter numbers into LEHS's own trend charts.
        """
        )

    # ---------------------------------------------------------------------------
    # 3. Housing supply
    # ---------------------------------------------------------------------------

    st.header("3. Housing supply — permits & zoning")

    with st.expander("Affordability yes, supply no", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Whether Lynn is *building* housing — permit
counts, zoning capacity, the pipeline of new units.

**Why we can't.** We have housing **affordability** (Zillow home values plus
ACS rent, units, and year-built) but **not** building-permit counts or
zoning. Those live in municipal and regional-planning sources (the City of
Lynn and MAPC), not in the education/Census stack this dashboard draws from.

**The proxy we use instead.** ACS *year-built* distributions hint at how
much of the stock is recent, but they are a snapshot of what exists — not a
measure of what's being added.
        """
        )

    # ---------------------------------------------------------------------------
    # 4. Student-level cohort tracking
    # ---------------------------------------------------------------------------

    st.header("4. Following one cohort over time")

    with st.expander("Why we can't follow a 9th-grade class to graduation", expanded=False):
        st.markdown(
            """
**What we'd like to show.** True longitudinal tracking — *follow this
specific 9th-grade cohort year by year to graduation and beyond.*

**Why we can't.** Real cohort tracking needs **Lynn SIS student-level
records**, which are confidential and not public. We never have a row per
student.

**The proxy we use instead.** **Aggregate grade-band counts** — how many
9th graders this year, how many 12th graders three years later. That
approximates a cohort but cannot account for students who transfer in or
out, so it is not a true longitudinal measure.
        """
        )

    # ---------------------------------------------------------------------------
    # 5. ACS geography vs. catchment
    # ---------------------------------------------------------------------------

    st.header("5. Census geography ≠ the LEHS attendance area")

    with st.expander("Whole-city Lynn, not the precise catchment", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Community context for the **LEHS attendance
area** specifically — the eastern half of the city the school actually
draws from.

**Why we can't.** Census **American Community Survey** data is published for
**whole-city Lynn**, not LEHS's catchment. The exact attendance-area
boundaries aren't published, so any "neighborhood" framing is approximate.
This is the same caveat noted on the **Methodology & Sources** tab; read every
ACS figure as *Lynn the city*, not *LEHS families*.
        """
        )

    # ---------------------------------------------------------------------------
    # 6. Suppression of small cells
    # ---------------------------------------------------------------------------

    st.header("6. Small-group suppression")

    with st.expander("Why the smallest subgroups show gaps", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Every student group, every year, at every
school — including the smallest ones.

**Why we can't.** DESE **suppresses any student-group cell with fewer than
10 students** before publishing, to protect individual privacy. So the
smallest subgroups, and small schools like **Frederick Douglass** and
**Harold Durgin**, show blanks or noticeably noisier rates.

**The honest read.** A missing cell is *usually* a suppressed small group,
not a true zero. Where a rate jumps around year to year for a tiny group,
that's sample noise, not necessarily a real change. This rule is documented
in full on the **Methodology & Sources** tab.
        """
        )

    # ---------------------------------------------------------------------------
    # 7. Lagging / paused series
    # ---------------------------------------------------------------------------

    st.header("7. Lagging & paused data series")

    with st.expander("Numbers that are older than you'd expect", expanded=False):
        st.markdown(
            """
Not every series is current, and a few are frozen:

- **Earnings outcomes — paused.** DESE **paused updates to the
  Average Earnings of HS Graduates series in 2025** over a methodology issue
  affecting graduates who didn't attend Massachusetts public postsecondary
  institutions. The figures shown are the last published vintage.
- **CRDC — biennial, and pandemic-shaped.** The federal Civil Rights Data
  Collection is released **every two years**; the latest public-use file is
  the **2021–22** school year — a pandemic-recovery year. Its public-use
  release also applies **small random perturbations** to protect privacy, so
  counts are approximate.
- **General lag.** Several DESE indicators (graduation, dropout, extended
  engagement) lag a year behind the determination year. A "latest" chart may
  be reporting a school year that already closed.
        """
        )

    # ---------------------------------------------------------------------------
    # 8. EJScreen snapshot
    # ---------------------------------------------------------------------------

    st.header("8. Environmental-justice indicators (EJScreen)")

    with st.expander("Currently an empty snapshot", expanded=False):
        st.markdown(
            """
**What we'd like to show.** EPA **EJScreen** environmental-justice
indicators around the school — pollution burden, proximity to hazards, and
the demographic indices that pair with them.

**Why we can't, right now.** The EJScreen dataset is currently an **empty
snapshot** in the pipeline. The source has been in flux, and until a stable
release lands we'd rather show nothing than show a half-loaded layer that
looks authoritative but isn't.
        """
        )

    st.divider()

    # ---------------------------------------------------------------------------
    # Summary table
    # ---------------------------------------------------------------------------

    st.subheader("At a glance")

    gaps = pd.DataFrame(
        [
            ("Student wellbeing / mental health",
             "Not published at school/district level in E2C",
             "Adult CDC PLACES + absenteeism & counselor ratios"),
            ("Charter schools (KIPP Academy Lynn)",
             "Charters are separate districts, not in LPS data",
             "Pointed to on Lynn HS Options, not merged in"),
            ("Housing supply (permits / zoning)",
             "Lives in municipal / MAPC sources, not our stack",
             "ACS affordability & year-built as context only"),
            ("Student-level cohort tracking",
             "Needs confidential Lynn SIS records",
             "Aggregate grade-band counts (approximate)"),
            ("ACS geography vs. catchment",
             "ACS is whole-city Lynn; catchment unpublished",
             "Read ACS as the city, not LEHS families"),
            ("Small-group suppression",
             "DESE blanks cells under 10 students",
             "Treat blanks as suppressed, not zero"),
            ("Lagging / paused series",
             "Earnings paused 2025; CRDC biennial (2021-22)",
             "Latest available vintage, flagged in context"),
            ("EJScreen indicators",
             "Currently an empty snapshot in the pipeline",
             "Omitted until a stable release lands"),
        ],
        columns=["Gap", "Why", "Workaround / proxy"],
    )

    st.dataframe(gaps, use_container_width=True, hide_index=True)

    st.divider()

    # ---------------------------------------------------------------------------
    # Crosslink + corrections invite
    # ---------------------------------------------------------------------------

    st.markdown(
        """
**Spotted something wrong, or a gap we missed?** This list is meant to be
corrected. If a number looks off, a caveat is out of date, or a dataset has
since been published, please flag it — every fix is recorded in the
**Corrections** tab so you can see what changed and when.
    """
    )

with _tab_3:
    # ==== from pages/Corrections.py ====
    # ---------------------------------------------------------------------------
    # Load the corrections log
    # ---------------------------------------------------------------------------

    _LOG_PATH = PROJECT_ROOT / "data" / "corrections.yaml"

    entries: list[dict] = []
    if _LOG_PATH.exists():
        parsed = yaml.safe_load(_LOG_PATH.read_text(encoding="utf-8")) or {}
        entries = parsed.get("corrections") or []

    # ---------------------------------------------------------------------------
    # Hero
    # ---------------------------------------------------------------------------

    st.header("Methodology")
    st.markdown(
        "This dashboard is a **living document**. When a number, label, or chart "
    "is corrected, the fix is logged here — with the date it shipped, the page "
    "it touched, what changed, and why. Keeping that record in the open makes "
    "the dashboard **transparent and auditable**: you can always trace how a "
    "figure got to where it is today, rather than seeing it quietly change "
    "from one visit to the next."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # The log
    # ---------------------------------------------------------------------------

    if not entries:
        st.info("No corrections logged yet.")
    else:
        df = pd.DataFrame(entries)

        # Normalize/select the expected columns, tolerating missing optional fields.
        for col in ("date", "page", "change", "reason", "source"):
            if col not in df.columns:
                df[col] = ""
        df = df[["date", "page", "change", "reason", "source"]].fillna("")

        # Newest first. Dates are ISO strings, so a lexical sort is chronological.
        df = df.sort_values("date", ascending=False, kind="stable").reset_index(drop=True)

        st.caption(f"{len(df)} correction(s) logged.")

        st.dataframe(
            df,
            width="stretch",
            hide_index=True,
            column_config={
                "date": st.column_config.TextColumn("Date", width="small"),
                "page": st.column_config.TextColumn("Page", width="medium"),
                "change": st.column_config.TextColumn("Change", width="large"),
                "reason": st.column_config.TextColumn("Reason", width="large"),
                "source": st.column_config.TextColumn("Source", width="small"),
            },
        )

        # Readable card view beneath the table, for anyone who prefers prose
        # over a grid (and so long "change" text is never truncated).
        with st.expander("Read as cards", expanded=False):
            for row in df.itertuples(index=False):
                with st.container(border=True):
                    header = f"**{row.date}** · {row.page}" if row.page else f"**{row.date}**"
                    st.markdown(header)
                    st.markdown(row.change)
                    if row.reason:
                        st.caption(f"Why: {row.reason}")
                    if row.source:
                        st.caption(f"Source: {row.source}")

    st.caption(
        "For the broader picture of what this dashboard can and can't show, "
        "see the **What We Don't Know** tab."
    )

page_footer()
