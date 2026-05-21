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

st.header("Peer cohort framework")

st.markdown(
    """
The dashboard compares LEHS against three nested peer cohorts to isolate
different kinds of effects:

1. **Lynn Classical High School (LCHS)** — Lynn's *other* comprehensive
   high school. Same district, same city, same school board. Differences
   between LEHS and LCHS isolate **school-level practices** (curriculum,
   discipline policy, ELL programming, scheduling) from city-wide
   demographic effects. You'll see LCHS as a dashed-line overlay on
   *School Profile*, *Academic Performance*, *ELL Pipeline*, *College &
   Career*, *Success After HS*, *Teachers & Workforce*, *Finance*, and
   *Discipline & Climate*.
2. **All Lynn high schools** (Lynn Tech, Fredrick Douglass, Harold Durgin
   alongside LEHS and LCHS) — visible on the *Lynn District & Siblings*
   page and *All Lynn Schools* page. Shows where LEHS sits inside the
   Lynn Public Schools high-school portfolio.
3. **26 Massachusetts Gateway Cities** — main comprehensive HS of each
   peer city. Shown on *Gateway Peer Comparison* and as a scatter cloud
   on *Correlation Lab*. This is the *across-cities* benchmark; the
   LEHS-vs-LCHS pairing is the *within-city* benchmark.
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
- **CRDC frequency**: Federal CRDC data is biennial. The latest release reflects the 2020-21 school year.
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

