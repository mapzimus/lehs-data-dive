"""Section 2 — Academic Performance: MCAS trends, growth, subgroup gaps."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="Academic Performance | LEHS", page_icon="📈", layout="wide")

st.title("Academic Performance")
st.markdown(
    "MCAS Grade 10 ELA, Math, and STE trends with student-group disaggregation "
    "and gap analysis."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("MCAS Grade 10 trends (2017–present)")
st.info("Chart placeholder")

st.subheader("Student group breakdown")
st.info("Chart placeholder")

st.subheader("Growth percentile (SGP) trends")
st.info("Chart placeholder")

st.subheader("Achievement gaps")
st.info("Chart placeholder")
