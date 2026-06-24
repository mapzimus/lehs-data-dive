"""Section 99 — Methodology, sources, and caveats."""

import streamlit as st

from utils.branding import page_footer, sidebar_attribution

st.set_page_config(page_title="Methodology | LEHS", page_icon="📚", layout="wide")
sidebar_attribution()

st.title("Methodology & Data Sources")
st.markdown(
    "Every number in this dashboard traces back to a public source. The "
    "dashboard is built on **50+ processed datasets drawn from ~10 public "
    "sources**. This page lists those sources, defines the common data "
    "fields, and spells out the suppression rules and important caveats."
)

# Owner direction: keep Methodology, "how to read the charts", and "what we
# don't know" discoverable as one reference family. Rather than duplicate that
# content, point to its dedicated pages up top.
st.info(
    "**The reference family:** this page covers *sources, fields, and "
    "caveats*. For how to read the charts see **Data 101**, and for the honest "
    "limits of what's measurable see **What We Still Don't Know**."
)
_ref1, _ref2 = st.columns(2)
_ref1.page_link("pages/Data_Literacy.py", label="📊 Data 101 — reading the charts")
_ref2.page_link("pages/Data_Gaps.py", label="🕳️ What We Still Don't Know")

# Annual PDF download — built by scripts/13_build_annual_report.py
from pathlib import Path
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
     "Bulk CSVs — discipline, VOCAL climate, accountability, ACCESS for ELLs, detailed staffing"),
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
     "reporting-element4.xlsx (former-EL MCAS), state.docx (WIDA ACCESS 2025)"),
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
   `accountability_indicators.parquet`; the MSHS sheet carries the state and
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
proficiency 10, Additional indicators 10; for the *Lowest Performing* group:
67.5 / 22.5 / 10 (no HS-completion or ELP weight). The **annual**
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
- **Dashboard** — https://maxwellhowegis.com/Lynn-data-dive/
- **MA Education Atlas** (standalone statewide map) — https://maxwellhowegis.com/ma-atlas/
- **Source code** — https://github.com/mapzimus/lehs-data-dive
"""
)

page_footer()

