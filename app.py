"""
LEHS Data Information Center — landing page.

Run locally: `streamlit run app.py`
"""

import streamlit as st

from utils.constants import LEHS_SCHOOL_NAME
from utils.data_loader import load_lehs_master

st.set_page_config(
    page_title="LEHS Data Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("Lynn English High School")
st.subheader("Data Information Center")
st.markdown(
    "A public, integrated data view of LEHS and its peer high schools across "
    "Massachusetts — built from every relevant DESE, federal, and Census dataset."
)

st.divider()

# ---------------------------------------------------------------------------
# Hero stats (placeholder — wired up after data pipeline runs)
# ---------------------------------------------------------------------------

df = load_lehs_master()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Enrollment", "—", help="From DESE enrollment dataset")
with col2:
    st.metric("4-Year Graduation Rate", "—", help="From DART Success After High School")
with col3:
    st.metric("Gr 10 MCAS — Math (% M+E)", "—")
with col4:
    st.metric("Immediate College Enrollment", "—")

if df.empty:
    st.info(
        "**Data not yet loaded.** Run `python scripts/refresh_all.py` to download "
        "and process the source datasets. Then refresh this page."
    )

st.divider()

# ---------------------------------------------------------------------------
# What's in here
# ---------------------------------------------------------------------------

st.markdown(
    """
## What's in here

Navigate the sections in the sidebar to explore:

- **School Profile** — Demographics, enrollment trends, headline accountability indicators
- **Academic Performance** — MCAS Grade 10 ELA, Math, STE trends with subgroup gaps
- **ELL Pipeline** — WIDA proficiency, former-EL outcomes, ELL achievement gaps (central narrative thread)
- **College & Career** — AP access and performance, FAFSA, MassCore, graduate plans
- **Success After HS** — Graduation rates, college enrollment, persistence
- **Teachers & Workforce** — Diversity, experience, retention, support staff ratios
- **Finance** — Per-pupil spending, federal funding, cost-per-outcome metrics
- **Discipline & Climate** — Suspensions, CRDC federal data, VOCAL climate survey
- **Community Context** — Lynn's ACS demographics, environment, public health context
- **Lynn District & Sibling Schools** — LEHS vs. Lynn Classical, Lynn Tech, etc. + district-wide view *(closest comparison)*
- **Gateway Peer Comparison** — LEHS vs. 25 gateway-city main high schools
- **Correlation Lab** — Cross-domain correlation discovery and custom explorer
- **Methodology** — Sources, definitions, caveats
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.caption(
    "Built independently. Data sourced from MA DESE, US Census Bureau, US Dept of "
    "Education, EPA, CDC, and the Massachusetts Department of Higher Education. "
    "See Methodology for full citations."
)
