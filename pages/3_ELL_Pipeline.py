"""
Section 3 — ELL Pipeline.

The central narrative thread: tracking English Learner outcomes from WIDA
proficiency through MCAS and into former-EL years.
"""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="ELL Pipeline | LEHS", page_icon="🌐", layout="wide")

st.title("ELL Pipeline")
st.markdown(
    "Lynn serves one of the highest concentrations of English Learners in "
    "Massachusetts (~45% district-wide). This section follows EL students "
    "from initial ACCESS scores through MCAS and into the years after they "
    "reclassify."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("ELL enrollment share over time")
st.info("Chart placeholder")

st.subheader("WIDA ACCESS proficiency distribution")
st.info("Chart placeholder")

st.subheader("Reclassification rate trend")
st.info("Chart placeholder")

st.subheader("Former EL MCAS performance by years post-exit")
st.info("Chart placeholder — from reporting-element4.xlsx")

st.subheader("ELL vs. non-ELL gap")
st.info("Chart placeholder")

st.subheader("LEHS ELL outcomes vs. peer cities (Lawrence, Chelsea, Holyoke)")
st.info("Chart placeholder")
