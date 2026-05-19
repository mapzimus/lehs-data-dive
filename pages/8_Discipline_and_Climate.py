"""Section 8 — Discipline, Climate & Safety."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="Discipline & Climate | LEHS", page_icon="⚖️", layout="wide")

st.title("Discipline, Climate & Safety")
st.markdown(
    "Suspension and expulsion rates with subgroup disproportionality analysis, "
    "federal CRDC data (restraint, school-based arrests, bullying), and VOCAL "
    "Survey climate results."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("Suspension rates over time (in-school and out-of-school)")
st.info("Chart placeholder")

st.subheader("Suspensions by race, gender, ELL, SPED — disproportionality")
st.info("Chart placeholder")

st.subheader("Expulsions")
st.info("Chart placeholder")

st.subheader("Federal CRDC data")
st.info("Chart placeholder — school-based arrests, restraint and seclusion, bullying incidents")

st.subheader("VOCAL Survey — student-reported climate")
st.info("Chart placeholder — belonging, safety, engagement (when LEHS participates)")
