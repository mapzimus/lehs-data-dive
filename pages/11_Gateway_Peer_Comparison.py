"""Section 11 — Gateway Peer Comparison: LEHS vs. 25 gateway-city main HS."""

import streamlit as st

from utils.data_loader import load_gateway_hs_panel

st.set_page_config(
    page_title="Gateway Peer Comparison | LEHS", page_icon="🏙️", layout="wide"
)

st.title("Gateway Peer Comparison")
st.markdown(
    "LEHS benchmarked against the main comprehensive high school in each of the "
    "other 25 Massachusetts Gateway Cities — similar urban contexts, similar "
    "demographic profiles."
)

df = load_gateway_hs_panel()

if df.empty:
    st.warning("Gateway HS panel not yet loaded. See README for setup.")
    st.stop()

st.subheader("Side-by-side scorecard — all 26 gateway HS")
st.info("Chart placeholder — sortable table with ~30 indicators")

st.subheader("Scatter — per-pupil spending vs. graduation rate")
st.info("Chart placeholder — where does LEHS fall?")

st.subheader("Subset: peers with similar ELL share")
st.info("Chart placeholder — Lawrence, Chelsea, Holyoke")

st.subheader("Multi-dimensional comparison")
st.info("Select 3 peers → see them on every metric")
