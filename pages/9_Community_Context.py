"""Section 9 — Community Context (ACS, environment, public health)."""

import streamlit as st

from utils.data_loader import load_dataset

st.set_page_config(page_title="Community Context | LEHS", page_icon="🏘️", layout="wide")

st.title("Community Context")
st.markdown(
    "The neighborhood Lynn English serves — Census ACS demographics, "
    "environmental exposure, public health, and local labor market context."
)

acs = load_dataset("lynn_acs")

if acs.empty:
    st.warning("Community context data not yet loaded. See README for setup.")
    st.stop()

st.subheader("Lynn Census ACS 5-year — demographics & economics")
st.info("Chart placeholder")

st.subheader("Child poverty (SAIPE district-modeled)")
st.info("Chart placeholder")

st.subheader("Environmental justice indicators (EPA EJScreen)")
st.info("Chart placeholder — lead, air quality, traffic proximity around the school")

st.subheader("Local health context (CDC PLACES)")
st.info("Chart placeholder — mental health days, insurance, etc.")

st.subheader("Local labor market (BLS / MA EOLWD)")
st.info("Chart placeholder — top hiring industries in North Shore")

st.subheader("Lynn vs. other gateway cities — community context comparison")
st.info("Chart placeholder")
