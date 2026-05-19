"""Section 9 — Community Context (Census ACS, environment, public health)."""

import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_NAVY
from utils.data_loader import load_dataset

st.set_page_config(page_title="Community Context | LEHS", page_icon="🏘️", layout="wide")
sidebar_attribution()

st.title("Community Context")
st.markdown(
    "The neighborhood Lynn English serves — Census ACS demographics, "
    "environmental exposure, and public health context that shapes the "
    "students who walk through the door."
)

# ---------------------------------------------------------------------------
# What we know so far (from enrollment data — proxies)
# ---------------------------------------------------------------------------

st.header("What the school data tells us")
st.caption(
    "Until Census ACS data is layered in, these school-level proxies tell us "
    "about Lynn's community: very high First-Language-Not-English share, high "
    "Hispanic/Latino share, very high low-income share."
)

enrollment = load_dataset("enrollment_demographics")
if not enrollment.empty:
    lehs = enrollment[enrollment["ORG_CODE"] == "01630510"].sort_values("SY")
    if not lehs.empty:
        latest = lehs.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("% First Language Not English", f"{latest['FLNE_PCT']:.0%}")
        with c2:
            st.metric("% Hispanic/Latino", f"{latest['HL_PCT']:.0%}")
        with c3:
            st.metric("% Low Income", f"{latest['LI_PCT']:.0%}")
        with c4:
            st.metric("% English Learner", f"{latest['EL_PCT']:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# Data acquisition needed
# ---------------------------------------------------------------------------

st.header("Coming with the Census + EJ + Public Health layers")

st.markdown(
    """
This page becomes fully populated once `scripts/04_download_census.py` and
companion scripts are filled in. Planned data:

### Census American Community Survey (5-year, tract level)
- **Median household income** (Lynn vs. MA average)
- **Child poverty rate**
- **% foreign-born** in households
- **Languages spoken at home** — top 5 with breakdown
- **Parent educational attainment** — % bachelor's or higher in 25+ population
- **Housing cost burden** — % of households paying 30%+ of income

### SAIPE — Small Area Income and Poverty Estimates
- School-district-modeled child poverty (used in federal Title I formulas)

### EPA EJScreen — Environmental Justice indicators
- Lead exposure, air quality, traffic proximity around the school
- Toxic release proximity
- Demographic Index (poverty + race)

### CDC PLACES — Local health
- Mental health (% with 14+ poor mental-health days)
- % uninsured adults
- Health risk behaviors

### BLS / MA EOLWD — Labor market
- Top hiring industries in North Shore
- Median wages
- Unemployment by demographic

### Comparison view
Lynn's community context vs. each of the other 25 gateway cities — answers
"how much of LEHS's challenge is community-driven vs. school-driven?"
"""
)

st.info(
    "These data sources require API keys (Census, BLS) or web scraping. "
    "Add as you have time — the dashboard architecture supports them out of "
    "the box once `data/raw/census/`, `data/raw/crdc/` etc. are populated."
)
