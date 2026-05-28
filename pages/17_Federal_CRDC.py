"""Section 17 — Federal CRDC (Civil Rights Data Collection)."""

import streamlit as st

from utils.branding import sidebar_attribution
from utils.data_loader import load_dataset

st.set_page_config(page_title="Federal CRDC | LEHS", page_icon="📊", layout="wide")
sidebar_attribution()

st.title("Federal CRDC — Civil Rights Data Collection")
st.markdown(
    "The CRDC is a biennial federal collection from the U.S. Department of "
    "Education's Office for Civil Rights. It captures things state datasets "
    "don't: school-based arrests, law-enforcement referrals, restraint and "
    "seclusion, AP/IB course offerings, and support-staff ratios. Most recent "
    "release at script-write time covers SY 2017-18 (next release: SY 2020-21)."
)

st.caption(
    "**Caveat about COVID-era data.** Recent CRDC releases cover school years "
    "affected by pandemic disruption — numbers may not reflect typical patterns."
)

discipline = load_dataset("crdc_discipline")
offerings = load_dataset("crdc_offerings")
staffing = load_dataset("crdc_staffing")

if discipline.empty and offerings.empty and staffing.empty:
    st.info(
        "CRDC parquet files are scaffolded but empty — the bulk-download URL "
        "for 2020-21 has changed since the script was written. The 2017-18 "
        "ZIP did download into data/raw/crdc/2017-18/ — per-school row "
        "extraction from those CSVs is a follow-up task. See "
        "scripts/04_download_crdc.py."
    )
    st.markdown(
        "When wired up, this page will surface:\n"
        "- **Discipline disaggregated** by race × disability × ELL × gender "
        "(ISS, OSS-single, OSS-multiple, expulsion, arrest, restraint).\n"
        "- **AP/IB offerings** — what courses each Lynn school actually offers "
        "vs. peer cities (a key equity-of-access measure).\n"
        "- **Support-staff ratios** — counselors/nurses/social workers per "
        "100 students vs. ASCA recommendation."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Discipline
# ---------------------------------------------------------------------------
if not discipline.empty:
    st.header("Discipline (CRDC)")
    st.dataframe(discipline, use_container_width=True, height=400)

# ---------------------------------------------------------------------------
# Course offerings
# ---------------------------------------------------------------------------
if not offerings.empty:
    st.header("Course offerings (AP / IB / advanced math)")
    st.dataframe(offerings, use_container_width=True, height=400)

# ---------------------------------------------------------------------------
# Support staffing
# ---------------------------------------------------------------------------
if not staffing.empty:
    st.header("Support-staff ratios")
    st.dataframe(staffing, use_container_width=True, height=400)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'CRDC discipline': discipline,
        'CRDC offerings': offerings,
        'CRDC staffing': staffing,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

