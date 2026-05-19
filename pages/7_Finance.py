"""Section 7 — Finance & Resource Allocation."""

import streamlit as st

from utils.data_loader import load_lehs_master

st.set_page_config(page_title="Finance | LEHS", page_icon="💰", layout="wide")

st.title("Finance & Resource Allocation")
st.markdown(
    "Per-pupil spending by category, federal funding allocations, and derived "
    "cost-per-outcome metrics."
)

df = load_lehs_master()

if df.empty:
    st.warning("Data pipeline not yet run. See README for setup.")
    st.stop()

st.subheader("LEHS per-pupil expenditure trend (state method)")
st.info("Chart placeholder")

st.subheader("ESSA federal-method per-pupil")
st.info("Chart placeholder")

st.subheader("Spending breakdown by category")
st.info("Chart placeholder — administration, instruction, support, operations")

st.subheader("Per-pupil by category vs. gateway peers")
st.info("Chart placeholder")

st.subheader("Lynn district-level finance context")
st.info("Chart placeholder — total budget, % from state aid / local / federal")

st.subheader("Title I, Title III (ELL), IDEA federal funding")
st.info("Chart placeholder")

st.subheader("Cost per graduate, cost per college-bound student")
st.info("Chart placeholder")
