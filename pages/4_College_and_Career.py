"""Section 4 — College & Career Readiness."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="College & Career | LEHS", page_icon="🎓", layout="wide")

st.title("College & Career Readiness")
st.markdown(
    "AP enrollment and performance, MassCore completion, FAFSA, SAT, "
    "graduate plans, and pathway programs (CTE, Early College, Innovation Pathways)."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("AP enrollment by student group — the access question")
st.info("Chart placeholder")

st.subheader("AP score distribution")
st.info("Chart placeholder")

st.subheader("MassCore completion rate")
st.info("Chart placeholder")

st.subheader("FAFSA completion")
st.info("Chart placeholder")

st.subheader("SAT averages")
st.info("Chart placeholder")

st.subheader("Plans of HS Graduates")
st.info("Chart placeholder")

st.subheader("Pathway program participation (CTE, Early College, IP)")
st.info("Chart placeholder")
