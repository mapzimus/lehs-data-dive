"""Section 99 — Methodology, sources, and caveats."""

import streamlit as st

from utils.branding import sidebar_attribution

st.set_page_config(page_title="Methodology | LEHS", page_icon="📚", layout="wide")
sidebar_attribution()

st.title("Methodology & Data Sources")
st.markdown(
    "Every number in this dashboard traces back to a public source. This page "
    "lists every dataset, the field definitions, suppression rules, and important "
    "caveats."
)

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
    ("DESE local files", "—",
     "reporting-element4.xlsx (former-EL MCAS), state.docx (WIDA ACCESS 2025)"),
]

for name, url, desc in sources:
    st.markdown(f"**{name}** — `{url}`")
    st.caption(desc)
    st.markdown("")

st.divider()

st.header("Naming conventions")

st.markdown(
    """
The dashboard uses three distinct scopes of "Lynn." Read these
consistently:

- **LEHS** — Lynn English High School. The single school this dashboard is
  about (ORG_CODE `01630510`).
- **Lynn district** / **LPS** — Lynn Public Schools, the K-12 district
  that contains LEHS plus 21 other schools (DIST_CODE `01630000`).
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

st.header("Peer cohort framework")

st.markdown(
    """
The dashboard uses three peer-comparison cohorts, each in its dedicated
home so the rest of the pages can stay LEHS-focused:

1. **Lynn sibling high schools** (LEHS vs. Lynn Classical, Lynn Tech,
   Frederick Douglass, Harold Durgin) — the same-district, same-policies
   comparison. Lives on the **[Lynn Schools](/Lynn_Schools)** page under
   the Compare group. Differences here isolate school-level practices
   (curriculum, discipline policy, ELL programming) from city-wide
   demographics. Where surviving chart contrasts on other pages (Finance,
   Discipline) include Classical alongside LEHS, Lynn Tech is included
   too.
2. **Lynn Public Schools as a whole** — district context, 22 schools.
   Shown on the **[Lynn District](/Lynn_District)** *Snapshot* tab and
   referenced on other pages where the district benchmark adds context.
3. **26 Massachusetts Gateway Cities** — main comprehensive HS of each
   peer city. Shown on the **[Gateway Cities](/Gateway_Peer_Comparison)**
   page and as a scatter cloud on the
   **[Cross-Topic Explorer](/Correlation_Lab)**. This is the
   across-cities benchmark.

LEHS-focused pages (School Profile, Academic Performance, English
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
- **CRDC frequency**: Federal CRDC data is biennial. The latest release reflects the 2020-21 school year. The Civil Rights Data page is hidden from the sidebar until the ingest pipeline is finished.
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

# Filter + process
python scripts/08_build_master_panel.py  # → data/processed/*.parquet
python scripts/11_build_lynn_geo.py      # → data/processed/*.geojson

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

