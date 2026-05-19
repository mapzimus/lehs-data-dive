"""Section 1 — School Profile: demographics, enrollment trends, headline metrics."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="School Profile | LEHS", page_icon="📊", layout="wide")

st.title("School Profile")
st.markdown(
    "Demographics, enrollment trends, and headline metrics for Lynn English High School."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("Enrollment over time")
st.info("Chart placeholder — wired up in Phase 4")

st.subheader("Student demographics")
st.info("Chart placeholder — wired up in Phase 4")

st.subheader("Comparison: LEHS vs. Lynn district vs. Gateway HS average")
st.info("Chart placeholder — wired up in Phase 4")
