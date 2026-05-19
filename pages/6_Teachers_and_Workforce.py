"""Section 6 — Teachers & Workforce."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="Teachers & Workforce | LEHS", page_icon="👩‍🏫", layout="wide")

st.title("Teachers & Workforce")
st.markdown(
    "Teacher diversity, experience distribution, retention, in-field rates, "
    "and student support staffing ratios."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("Teacher headcount & FTE")
st.info("Chart placeholder")

st.subheader("Teacher diversity vs. student body — representation gap")
st.info("Chart placeholder")

st.subheader("Years of experience distribution")
st.info("Chart placeholder")

st.subheader("Year-over-year retention rate")
st.info("Chart placeholder")

st.subheader("Average teacher salary")
st.info("Chart placeholder")

st.subheader("% In-field by subject")
st.info("Chart placeholder")

st.subheader("Educator pipeline (Teach Mass)")
st.info("Chart placeholder — MTEL pass rates, prep program data")

st.subheader("Student support staff ratios")
st.info("Chart placeholder — counselors, nurses, psychologists, social workers per 100 students")

st.subheader("Class size by subject")
st.info("Chart placeholder")
