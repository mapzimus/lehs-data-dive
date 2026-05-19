"""Section 5 — Success After High School: graduation, college enrollment, persistence."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="Success After HS | LEHS", page_icon="🏆", layout="wide")

st.title("Success After High School")
st.markdown(
    "4-year and 5-year graduation cohorts, postsecondary enrollment by institution "
    "type, and college persistence to the second year."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("Graduation rates by student group")
st.info("Chart placeholder")

st.subheader("9th to 10th grade promotion rate — the early warning")
st.info("Chart placeholder")

st.subheader("Dropout trend")
st.info("Chart placeholder")

st.subheader("Postsecondary enrollment: 2-year vs. 4-year")
st.info("Chart placeholder")

st.subheader("College persistence to year 2")
st.info("Chart placeholder")

st.subheader("Cohort progression waterfall")
st.info("Chart placeholder — HS → enrolled → persisted → completed")
