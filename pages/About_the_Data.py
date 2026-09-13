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
from utils.data_loader import latest_sy, load_dataset
from utils.interpret import sy_label
st.set_page_config(page_title="About the Data | LEHS", page_icon="📚", layout="wide")
sidebar_attribution()

_latest_data_sy = latest_sy(load_dataset("enrollment_demographics"))
_latest_ay = sy_label(_latest_data_sy).replace("-", "–") if _latest_data_sy else "2025–26"

st.title("About the Data")
st.markdown(
    "Where the numbers come from, how to read the charts, what this site "
    "*cannot* show, and a public list of every fix. Pick a tab below."
)
_tab_0, _tab_1, _tab_2, _tab_3 = st.tabs(['📚 Sources & Methods', '📖 Data 101', "🔎 What We Don't Know", '📝 Corrections'])

with _tab_0:
    # ==== from pages/99_Methodology.py ====
    st.header("Sources & methods")
    st.markdown(
        "Every number on this site comes from a public source. This tab "
        "lists those sources, explains a few labels you will see on charts, "
        "and names the limits that matter."
    )

    st.header("About this dashboard")
    st.markdown(
        """
**What it is.** A free, public website about **Lynn English High School**
(LEHS) — the largest comprehensive high school in Lynn, Massachusetts. It
brings together enrollment, MCAS tests, courses, English Learners, college
and career, the state report card, staffing, spending, discipline, and
neighborhood context. Those pieces usually live on a dozen state and
federal sites.

**Why it exists.** The information is public, but it is hard to find, hard
to compare year to year, and full of agency jargon. The goal is a clear
picture for **students, families, teachers, school leaders, and neighbors**
— no spreadsheet required.

**Who built it.** Built and kept up by **Maxwell Howe**
([maxwellhowegis.com](https://maxwellhowegis.com)) as an independent
project. It is **not** an official Lynn Public Schools or Massachusetts
DESE publication. Every figure traces back to the sources below so you
can check the work yourself.
"""
    )

    st.divider()

    st.info(
        "This tab is *where the numbers come from*. The **Data 101** tab "
        "is *how to read the charts*. **What We Don't Know** is *what this "
        "site cannot show*."
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
        ("E2C Hub (Massachusetts DESE open data)", "educationtocareer.data.mass.gov",
         "The main state data site: MCAS, graduation, AP, enrollment, attendance, spending, staffing, graduate plans, career pathways, and college outcomes."),
        ("DESE school/district reports", "profiles.doe.mass.edu/statereport/",
         "Downloadable tables for discipline, school climate (VOCAL), the state report card, ACCESS (the English test for English Learners), and detailed staffing."),
        ("DESE accountability workbooks", "doe.mass.edu/accountability/lists-tools",
         "The five yearly spreadsheets behind the State Accountability page — the school's rating, goals, and statewide rank. Details below."),
        ("Civil Rights Data Collection (CRDC)", "civilrightsdata.ed.gov",
         "A federal survey every two years: discipline by race, disability, and gender; restraint; school-based arrests; AP offerings; sports participation."),
        ("IPEDS / College Scorecard", "nces.ed.gov/ipeds",
         "Federal college data — graduation rates and outcomes at the colleges Lynn graduates attend."),
        ("Census ACS 5-year", "data.census.gov",
         "City of Lynn context: income, language, parental education, housing."),
        ("Census SAIPE", "census.gov/programs-surveys/saipe",
         "Child-poverty estimates for the school district."),
        ("EPA EJScreen", "ejscreen.epa.gov",
         "Neighborhood environmental-health indicators. Currently not loaded — see What We Don't Know."),
        ("CDC PLACES", "cdc.gov/places",
         "Adult health indicators by neighborhood (not student health)."),
        ("MA Department of Higher Education", "mass.edu",
         "Public-college enrollment, first-year return rates, and degrees."),
        ("MaxPreps", "maxpreps.com",
         "Season-by-season athletics records. Hall of Fame and older history come from a separate curated file on this site."),
        ("DESE one-off files", "—",
         "Former English Learner MCAS results, and the statewide WIDA ACCESS 2025 English-test summary."),
    ]

    for name, url, desc in sources:
        st.markdown(f"**{name}** — `{url}`")
        st.caption(desc)
        st.markdown("")

    st.subheader("The state report card, in plain language")

    st.markdown(
        """
The **[State Accountability](/Accountability?embed=true)** page comes from
**five public DESE spreadsheets** on the
[lists-and-tools page](https://www.doe.mass.edu/accountability/lists-tools/).
Together they answer four questions:

1. **How is the school rated this year?** — classification (for example,
   "requiring assistance"), a statewide percentile from 1–99, and any
   federal flag such as CSI.
2. **How close is it to its own yearly goals?** — each measure
   (MCAS, graduation, English-learner progress, attendance, and so on)
   is scored for each student group.
3. **What is the goal for next year?** — the state sets a starting
   point and a step for each measure. For dropout and chronic
   absence, a *lower* number is the goal.
4. **Where does each piece rank statewide?** — ranks blend **three
   years**, with the newest year counting most (15% / 25% / 60%).

**How the score is built (short version).** Each measure can earn
**0–4 points** for a student group. Those points are weighted:

- *All Students:* tests 40%, growth 20%, finishing high school 20%,
  English progress 10%, other (attendance, etc.) 10%.
- *Lowest-performing group:* tests 67.5%, growth 22.5%, other 10%.

The **this-year** progress figure is the share of possible points
earned. The **multi-year** figure is 40% last year + 60% this year.
**75% or higher** is "meeting targets."

A few limits: DESE hides groups smaller than 10 students; some
measures (graduation, dropout) are a year behind the rating year; and
the newest targets file landed **July 31, 2026**.
"""
    )

    with st.expander("File names for people who want to rebuild this"):
        st.markdown(
            """
Downloaded by `scripts/19_download_accountability_detail.py` and
processed by `scripts/16_process_dese_profiles.py`:

1. `accountability-data-{year}.xlsx` → `accountability_summary.parquet`
2. `criterion-referenced-percentage-{year}.xlsx` →
   `accountability_indicators.parquet` (schools) and
   `accountability_benchmarks.parquet` (state and district)
3. `accountability-targets-{year}.xlsx` → `accountability_targets.parquet`
4. `school-percentile-{year}.xlsx` and
   `student-group-percentile-{year}.xlsx` →
   `accountability_percentiles.parquet`
"""
        )

    st.divider()

    st.header("What \"Lynn\" means on this site")

    st.markdown(
        """
The word "Lynn" shows up in three different ways. Charts label which
one they mean:

- **LEHS** — Lynn English High School. The one school this site is
  about (state code `01630510`).
- **Lynn district** / **LPS** — Lynn Public Schools, the K–12 system
  with LEHS plus 25 other schools — 26 in all (state code `01630000`).
- **Lynn** (alone) — the city of Lynn. Used for Census, income, and
  maps.
- **Lynn Classical**, **Lynn Tech**, **Fredrick Douglass**, and
  **Harold Durgin** — the other Lynn high schools, always named in
  full.

"Lynn" by itself never means Lynn English.
"""
    )

    st.divider()

    st.header("A few labels you will see")

    st.markdown(
        f"""
The state files use the same short names in many tables:

- **School / district / state** — the same number is often published
  for one school, the whole district, and Massachusetts. Charts say
  which. Behind the scenes those rows are tagged `ORG_TYPE` and an
  8-digit `ORG_CODE` (LEHS is `01630510`; the district is `01630000`).
- **School year (`SY`)** — stored as the spring year. `SY =
  {_latest_data_sy or 2026}` means **{_latest_ay}** (the latest year in
  the enrollment file). `SY = 2024` means 2023–24, ending June 2024.
- **Student group** — `All Students`, or a group such as English
  Learner, Low Income, Students with Disabilities, or a
  race/ethnicity. Groups smaller than 10 students are hidden (see
  caveats).
- **Count vs. percent** — a count is a headcount. A percent is that
  count divided by the group it belongs to, so you can compare schools
  of different sizes.
"""
    )

    st.divider()

    st.header("Who we compare Lynn English with")

    st.markdown(
        """
Most pages stay focused on Lynn English. Comparison lives on three
pages:

1. **Other Lynn high schools** — Classical, Tech, Fredrick Douglass,
   and Harold Durgin. Same city, same rules. Differences here are
   more about the school (courses, discipline, English Learner
   programs) than about the city. See
   **[Lynn Schools](/Lynn_Schools?embed=true)**. Finance and Discipline
   charts that include Classical also include Lynn Tech.
2. **The whole district** — all 26 Lynn Public Schools. See
   **[Lynn District](/Lynn_District?embed=true)**.
3. **Similar cities** — the main public high school in each of the
   26 Massachusetts Gateway Cities. See
   **[Gateway Cities](/Gateway_Peer_Comparison?embed=true)** and the
   **[Cross-Topic Explorer](/Correlation_Lab?embed=true)**.
"""
    )

    st.divider()

    st.header("Things to keep in mind")

    st.markdown(
        """
- **Small groups are hidden.** DESE does not publish a student-group
  number when fewer than 10 students are in it. Those cells are blank —
  not zero.
- **Labels change over time.** "Economically Disadvantaged" (2015–2021)
  and "Low Income" (before 2015, and 2022+) are not the same formula.
  See the [DESE Researcher's Guide](https://www.doe.mass.edu/infoservices/research/guide.html).
- **Graduate earnings are frozen.** DESE paused that series in 2025
  because of a method problem for graduates who did not attend a
  Massachusetts public college.
- **Not every school takes the climate survey (VOCAL) every year.**
  Coverage is noted where it appears.
- **City numbers are for all of Lynn**, not just the Lynn English
  attendance area. That area is roughly the eastern half of the city;
  exact boundaries are not published.
- **Federal civil-rights data is every two years.** The latest public
  file is **2021–22**, a pandemic-recovery year. Staffing ratios are on
  [Teachers & Workforce](/Teachers_and_Workforce?embed=true), advanced
  courses on [Courses & Academics](/Courses_and_Academics?embed=true),
  and discipline detail on
  [Discipline & Climate](/Discipline_and_Climate?embed=true). The file
  also adds small random noise to protect privacy, so counts are
  approximate.
- **Two numbers moving together is not proof that one causes the
  other.** The Cross-Topic Explorer is for spotting patterns, not
  declaring causes.
"""
    )

    st.divider()

    st.header("How to rebuild this site")
    st.markdown(
        "For people who want to run the same downloads on their own "
        "computer. Everyone else can skip this."
    )

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
- **This dashboard** — https://maxwellhowegis.com/lynndata/
- **Massachusetts map** — https://maxwellhowegis.com/ma-atlas/
- **Source code** — private GitHub repo (`mapzimus/lehs-data-dive`)
"""
    )

with _tab_1:
    # ==== from pages/Data_Literacy.py ====
    # ---------------------------------------------------------------------------
    # Hero
    # ---------------------------------------------------------------------------

    st.header("Data 101 — Reading the Charts")
    st.markdown(
        "This site is full of numbers and graphs. If you have never opened "
        "a dashboard before, **start here**. No background needed."
    )

    st.info(
        "📚 Written for Lynn English students, families, teachers, and "
        "neighbors. Skip around — you do not have to read it in order."
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
            "School Year": ["2024–25", "2025–26"],
            "School": ["Lynn English High"] * 2,
            "Total Students": [2_062, 1_727],
            "% English Learners": ["43%", "42%"],
            "% Low Income": ["75%", "75%"],
        }
    )
    st.dataframe(demo_dataset, hide_index=True, width="stretch")

    st.markdown(
        """
- Two **rows**, one per school year. The real table goes back much further.
- Five **columns**, each measuring something different.
- The actual dataset behind the [School Profile](/School_Profile?embed=true) page
  has thousands of rows like these going back to 1992 — but the
  shape is the same.

**A database** is just a *collection of related tables* kept together.
This site sits on **50+ tables from about 10 public sources** —
Massachusetts DESE, the Census, federal civil-rights data, athletics
records, and Lynn-only maps. Each chart is a way of *looking at* one
or more of those tables.
"""
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 2 — Chart types (the main event)
    # ---------------------------------------------------------------------------

    st.header("2. Chart types and what each one is for")

    st.markdown(
        "Different charts answer different questions. Here are the ones "
        "this site uses most, with a tiny example of each."
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
- **Use when:** comparing a number across groups (here: schools).
- **What to look for:** which bar is tallest, how they rank, how big
  the gaps are.
- **On this site:** any page that ranks schools, subjects, or student
  groups.

👀 **See it live:** [Lynn Schools](/Lynn_Schools?embed=true) compares
Lynn English with the other Lynn high schools.
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
- **Use when:** showing how a number *changes* over time.
- **What to look for:** the slope (up or down?), sharp jumps, and
  gaps (the missing 2020 point above is when COVID cancelled MCAS).
- **On this site:** MCAS trends, enrollment over decades, graduation
  rates.

👀 **See it live:** [MCAS](/Academic_Performance?embed=true) opens
with multi-year lines — including that real 2020 gap.
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
- **Use when:** you want the *shape* of one set of numbers — where
  most values sit, how spread out they are, and whether a few are
  far from the rest.
- **What to look for:** the peak (the most common value), the spread
  (narrow = similar, wide = mixed), and the tails.
- **Not the same as a bar chart.** A bar chart compares groups
  (schools, subjects). A histogram chops *one number* into ranges
  and counts how many fall in each range.
- **On this site:** how MCAS levels are spread, and how large
  Gateway City high schools are.
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
- **Use when:** asking *"do these two things move together?"* One
  number on the bottom, one on the side, each dot is one city or
  school.
- **What to look for:** a sloping cloud means the two things are
  *correlated* (they tend to rise or fall together). The line is the
  average pattern.
- **Warning:** moving together is not the same as one *causing* the
  other (Section 4).
- **On this site:** the [Cross-Topic Explorer](/Correlation_Lab?embed=true)
  is all scatter plots — pick any two numbers across the 26 Gateway
  Cities.

👀 **See it live:** [Cross-Topic Explorer](/Correlation_Lab?embed=true)
— pick two numbers you are curious about.
"""
    )

    # --- Choropleth-style explanation ---
    st.subheader("🗺️ Color-coded map — *geography*")

    st.markdown(
        """
A **color-coded map** (sometimes called a choropleth) paints each
shape — town, neighborhood, or census tract — by a number. Darker
usually means more. It answers *"where is this happening?"*

You will see two sizes:
- **Lynn:** 22 neighborhoods shaded by income, language at home, or
  chronic absence — on the
  [City → Neighborhoods tab](/Lynn_City?embed=true) and the
  [Maps page](/Maps?embed=true).
- **Massachusetts:** all 351 cities and towns — on the
  [MA Education Atlas](https://maxwellhowegis.com/ma-atlas/).

👀 **See it live:** start on [Maps](/Maps?embed=true) and color Lynn
by a number you care about.
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
- **Use when:** you want patterns across *two* groupings at once
  (here: subject and grade).
- **What to look for:** the darkest cells (highest values) and
  whether one row or column stands out.
- **On this site:** subject-by-grade MCAS grids, attendance by
  student group.
"""
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Section 3 — How to read a percentage
    # ---------------------------------------------------------------------------

    st.header("3. How to read a percentage")

    st.markdown(
        """
Percentages are everywhere on this site. They look simple, but they
hide a few traps.

**A percentage is always "out of what?"**
When you see *"42% of LEHS students are English Learners"*, the
**"out of"** is the school's total enrollment — about 1,727 students.
That is roughly 725 English Learners. The percent lets you compare
schools of different sizes.

**Percent vs. percentage points**
If the graduation rate goes from 80% to 85%, that is a **5
percentage-point** rise. It is **not** a 5% rise — 5% of 80 is 4,
which would land at 84%. On this site, "+5 pts" always means
percentage points.

**Compared to what?**
A single percent is not useful by itself. *75% Low Income* sounds
high — but compared with what? Charts here put LEHS next to:
- the other Lynn high schools
- Lynn Public Schools as a whole
- other Massachusetts Gateway Cities (Lawrence, Holyoke, Springfield, …)
- the state average

That is why most charts have more than one color.
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

This site reports **median** household income, home values, and rent —
so a few very high numbers do not pull the story off center.
"""
        )

    with st.expander("**Sample size** — 100% of 4 students vs. 100% of 1,000", expanded=False):
        st.markdown(
            """
If a school reports "100% of seniors took the SAT", that means very
different things at LEHS (~400 seniors) than at a tiny program (~10
seniors). Small sample sizes are noisy — one or two unusual students
can swing the percentage wildly.

This is why DESE **hides** group numbers below 10 students — the
percent would jump around, and it could identify someone. When you
see "—" or "DS" (data hidden), that is why.
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
patterns across 26 similar cities. Use it to ask questions, not to
declare causes.
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
That's why most trend charts here go back 5+ years.
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

👀 **See it live:** the MCAS trend charts on
[MCAS](/Academic_Performance?embed=true) are a good place to
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
A few good places to practice:

- **[School Profile](/School_Profile?embed=true)** — who attends LEHS,
  year by year.
- **[MCAS](/Academic_Performance?embed=true)** — test-score lines with
  those fuzzy confidence bars. Look for a real trend, not one jump.
- **[Cross-Topic Explorer](/Correlation_Lab?embed=true)** — pick any
  two numbers across 26 cities. Remember: moving together is not
  causing.
- **[Maps](/Maps?embed=true)** — color-coded maps of Lynn and
  Massachusetts.

If a chart is confusing, the explanation is probably on this tab.
"""
    )

    st.divider()
    st.caption(
        "Built for students, by a teacher. If something is still unclear, "
        "use the contact link in the footer."
    )

with _tab_2:
    # ==== from pages/Data_Gaps.py ====
    # ---------------------------------------------------------------------------
    # Hero
    # ---------------------------------------------------------------------------

    st.header("What We Still Don't Know")
    st.markdown(
        "A site is only trustworthy if it is honest about its blind spots. "
        "This tab lists what we **cannot** show — and why. Some gaps are "
        "about what the state publishes. Some are about maps. Some are "
        "about hiding small groups to protect student privacy. None of "
        "them are secrets."
    )

    st.info(
        "This is the full list of gaps. Short versions also appear under "
        "**Things to keep in mind** on the Sources & Methods tab."
    )

    st.divider()

    # ---------------------------------------------------------------------------
    # 1. Student wellbeing / mental health
    # ---------------------------------------------------------------------------

    st.header("1. Student wellbeing & mental health")

    with st.expander("What we'd like to show — and why we can't", expanded=True):
        st.markdown(
            """
**What we'd like to show.** How students themselves say they are doing —
mental health, vaping, sleep, food, and the other Youth Risk Behavior
Survey questions — at the school or district level.

**Why we can't.** The state does not publish those student answers for
Lynn English or even for Lynn as a district in the open-data files this
site uses. The youth-survey results that exist are for a much larger
area.

**What we show instead.** Adult health by neighborhood (CDC PLACES — not
students), plus chronic absence and counselor-to-student ratios. Those
hint at the question. They do not answer it.

The **Wellbeing** tab tries a district-level youth-survey view. Treat it
as experimental — the numbers may be too broad to use with confidence.
        """
        )

    # ---------------------------------------------------------------------------
    # 2. Charter schools
    # ---------------------------------------------------------------------------

    st.header("2. Charter schools (e.g. KIPP Academy Lynn)")

    with st.expander("Why KIPP isn't shown side-by-side", expanded=False):
        st.markdown(
            """
**What we'd like to show.** A family weighing **KIPP Academy Lynn** next
to the district high schools, on the same charts.

**Why we can't.** Charter schools are their own districts. They are
**not in the Lynn Public Schools files** this site uses. Adding KIPP
would need a separate download and careful caveats (charters enroll by
lottery, not by neighborhood).

**What we do instead.** We say so on the
[Lynn Schools](/Lynn_Schools) family tab, rather than mixing KIPP into
Lynn English's own trend charts.
        """
        )

    # ---------------------------------------------------------------------------
    # 3. Housing supply
    # ---------------------------------------------------------------------------

    st.header("3. Housing supply — permits & zoning")

    with st.expander("Affordability yes, supply no", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Whether Lynn is *building* housing — permits,
zoning, and new units in the pipeline.

**Why we can't.** We have **affordability** (home values, rent, and year
built) but not permit counts or zoning. Those live with the City of Lynn
and regional planners, not in the education and Census files we use.

**What we show instead.** When homes were built. That is a snapshot of
what exists, not what is being added.
        """
        )

    # ---------------------------------------------------------------------------
    # 4. Student-level cohort tracking
    # ---------------------------------------------------------------------------

    st.header("4. Following one class over time")

    with st.expander("Why we can't follow a 9th-grade class to graduation", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Follow one 9th-grade class year by year to
graduation and beyond.

**Why we can't.** That needs a row per student from the district's
private records. Those records are not public. This site never has
student-level data.

**What we show instead.** Grade totals — how many 9th graders this year,
how many 12th graders three years later. That is a rough stand-in. It
cannot account for students who transfer in or out.
        """
        )

    # ---------------------------------------------------------------------------
    # 5. ACS geography vs. catchment
    # ---------------------------------------------------------------------------

    st.header("5. City numbers are not the Lynn English attendance area")

    with st.expander("Whole-city Lynn, not the school's exact area", expanded=False):
        st.markdown(
            """
**What we'd like to show.** Neighborhood facts for the **Lynn English
attendance area** — roughly the eastern half of the city.

**Why we can't.** Census numbers are published for **all of Lynn**, not
for the school's attendance area. Exact boundaries are not published,
so "neighborhood" maps are approximate. Read every Census figure as
*Lynn the city*, not *Lynn English families*.
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

**Why we can't.** DESE **hides any group with fewer than 10 students**
before publishing, to protect privacy. The smallest groups, and small
schools like **Fredrick Douglass** and **Harold Durgin**, show blanks
or jumpy rates.

**How to read it.** A blank cell is *usually* a hidden small group, not
a true zero. A rate that jumps around for a tiny group is often noise,
not a real change.
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

- **Graduate earnings — paused.** DESE stopped updating this series in
  **2025** because of a method problem for graduates who did not attend
  a Massachusetts public college. The figures shown are the last ones
  published.
- **Federal civil-rights data — every two years.** The latest public
  file is **2021–22**, a pandemic-recovery year. Counts are also
  slightly scrambled to protect privacy, so they are approximate.
- **Some numbers are a year behind.** Graduation, dropout, and a few
  others lag the rating year. A "latest" chart may be last year's
  class.
        """
        )

    # ---------------------------------------------------------------------------
    # 8. EJScreen snapshot
    # ---------------------------------------------------------------------------

    st.header("8. Environmental-justice indicators (EJScreen)")

    with st.expander("Currently an empty snapshot", expanded=False):
        st.markdown(
            """
**What we'd like to show.** EPA neighborhood environmental-health
indicators around the school — pollution, nearby hazards, and who lives
there.

**Why we can't, right now.** That file is empty in our current build.
The source has been changing. Until a stable copy lands, we would
rather show nothing than a half-loaded layer that looks official but
isn't.
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
             "Not published for Lynn English or Lynn district",
             "Adult neighborhood health + absence & counselor ratios"),
            ("Charter schools (KIPP Academy Lynn)",
             "Charters are separate districts, not in LPS data",
             "Noted on Lynn Schools, not mixed into LEHS charts"),
            ("Housing supply (permits / zoning)",
             "Lives with the city and regional planners",
             "Home values, rent, and year-built only"),
            ("Following one class over time",
             "Needs private student records",
             "Grade totals (approximate)"),
            ("Census maps vs. attendance area",
             "Census is whole-city Lynn; boundaries unpublished",
             "Read Census as the city, not LEHS families"),
            ("Small-group hiding",
             "DESE blanks groups under 10 students",
             "Treat blanks as hidden, not zero"),
            ("Older or paused series",
             "Earnings paused 2025; civil-rights file is 2021–22",
             "Latest published year, flagged on the chart"),
            ("Neighborhood environment (EJScreen)",
             "File is empty in the current build",
             "Left out until a stable copy lands"),
        ],
        columns=["Gap", "Why", "What we show instead"],
    )

    st.dataframe(gaps, use_container_width=True, hide_index=True)

    st.divider()

    # ---------------------------------------------------------------------------
    # Crosslink + corrections invite
    # ---------------------------------------------------------------------------

    st.markdown(
        """
**See something wrong, or a gap we missed?** Please say so. Every fix
is listed on the **Corrections** tab so you can see what changed and
when.
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

    st.header("Corrections")
    st.markdown(
        "When a number, label, or chart is fixed, it is logged here — the "
        "date, the page, what changed, and why. That way a figure does not "
        "quietly change between visits."
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
