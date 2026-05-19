"""
Section 10 — Lynn District & Sibling Schools.

The *closest* peer comparison: LEHS vs. its sibling Lynn HS (Classical, Tech,
Fecteau-Leary, Frederick Douglass) — same district, same policies, same student
pool. Differences here isolate school-level effects rather than city-level
demographics.
"""

import streamlit as st

from utils.data_loader import load_lynn_schools_panel, load_lynn_sibling_hs

st.set_page_config(
    page_title="Lynn District & Siblings | LEHS", page_icon="🏛️", layout="wide"
)

st.title("Lynn District & Sibling Schools")
st.markdown(
    "**This is the most analytically powerful peer view.** Lynn's high schools "
    "share the same district, same policies, and draw from the same student pool. "
    "Differences between them isolate school-level practices rather than city-level "
    "factors."
)

st.divider()

# ---------------------------------------------------------------------------
# Lynn Public Schools district-wide view
# ---------------------------------------------------------------------------

st.header("Lynn Public Schools — District View")
st.markdown(
    "~16,400 students across 22 schools. Below is the district-wide context that "
    "shapes LEHS's incoming cohorts and operating environment."
)

district = load_lynn_schools_panel()

if district.empty:
    st.warning("Lynn schools panel not yet loaded. See README for setup.")
else:
    st.subheader("District-wide demographics over time")
    st.info("Chart placeholder")

    st.subheader("District-wide MCAS performance")
    st.info("Chart placeholder")

    st.subheader("All 22 Lynn schools — at a glance")
    st.info("Chart placeholder — table of all schools with key indicators")

    st.subheader("Elementary feeder analysis")
    st.info("Chart placeholder — feeder demographics shape LEHS's incoming cohort")

    st.subheader("Lynn district budget")
    st.info("Chart placeholder")

st.divider()

# ---------------------------------------------------------------------------
# Lynn high schools side-by-side
# ---------------------------------------------------------------------------

st.header("Lynn High Schools — Side by Side")
st.markdown(
    "LEHS vs. Lynn Classical, Lynn Tech, Fecteau-Leary, and Frederick Douglass "
    "Collegiate Academy across every domain."
)

siblings = load_lynn_sibling_hs()

if siblings.empty:
    st.warning("Sibling-school panel not yet loaded.")
else:
    st.subheader("Sibling school scorecard")
    st.info("Chart placeholder — sortable table with rank within Lynn HS")

    st.subheader("Trend small-multiples — one panel per HS")
    st.info("Chart placeholder")

    st.subheader("Where LEHS leads, where it lags vs. siblings")
    st.info("Chart placeholder")

    st.subheader("Student-group filter — compare ELL outcomes across Lynn HS")
    st.info("Chart placeholder — does Classical do better with ELLs?")
