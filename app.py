"""
LEHS Data Information Center — landing page.

Run locally: `streamlit run app.py`
"""

import streamlit as st

from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset

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
# Hero stats from real LEHS data
# ---------------------------------------------------------------------------

enrollment = load_dataset("enrollment_demographics")
grad = load_dataset("graduation_rates")
mcas = load_dataset("mcas_achievement")
dart = load_dataset("dart_success_after_hs")

if enrollment.empty:
    st.info(
        "**Data not yet loaded.** Run `python scripts/refresh_all.py` (after "
        "creating the conda env) to download and process the source datasets. "
        "Then refresh this page."
    )
    st.stop()

lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY")
current = lehs.iloc[-1]
current_sy = int(current["SY"])

st.caption(f"All metrics below are for school year {current_sy} (most recent available).")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Total Enrollment", f"{int(current['TOTAL_CNT']):,}")
with c2:
    st.metric("% English Learners", f"{current['EL_PCT']:.0%}")
with c3:
    st.metric("% Low Income", f"{current['LI_PCT']:.0%}")
with c4:
    st.metric("% High Needs", f"{current['HN_PCT']:.0%}")

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
- **ELL Pipeline** — WIDA proficiency, former-EL outcomes, ELL achievement gaps *(central narrative thread)*
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
