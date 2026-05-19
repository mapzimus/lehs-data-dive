"""
LEHS Data Information Center — landing page.

Run locally: `streamlit run app.py`
"""

import streamlit as st

from utils.branding import AUTHOR_NAME, AUTHOR_SITE, sidebar_attribution
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="LEHS Data Dive",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

sidebar_attribution()

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

col_title, col_author = st.columns([3, 1])
with col_title:
    st.title("Lynn English High School")
    st.subheader("Data Dive")
with col_author:
    st.markdown(
        f"""
        <div style='text-align:right; margin-top:2rem;'>
            <span style='color:#0A1F44; font-size:0.95rem;'>Built by</span><br>
            <strong style='font-size:1.3rem; color:#0A1F44;'>{AUTHOR_NAME}</strong><br>
            <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "A public, integrated data view of LEHS and its peer high schools across "
    "Massachusetts — built from every relevant DESE, federal, and Census dataset. "
    "**Unlike any DESE tool, this dashboard puts every domain in one place** and "
    "supports correlation analysis across them."
)

st.divider()

# ---------------------------------------------------------------------------
# Hero stats from real LEHS data
# ---------------------------------------------------------------------------

enrollment = load_dataset("enrollment_demographics")

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

st.caption(f"All metrics below are for school year {sy_label(current_sy)} (most recent available).")

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

st.markdown(
    f"""
    <div style='text-align:center; margin-top:2rem; color:#455A64; font-size:0.9rem;'>
        Built by <strong>{AUTHOR_NAME}</strong> ·
        <a href='https://{AUTHOR_SITE}' style='color:#FFB81C;'>{AUTHOR_SITE}</a> ·
        <a href='https://github.com/mapzimus/lehs-data-dive' style='color:#FFB81C;'>source on GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
