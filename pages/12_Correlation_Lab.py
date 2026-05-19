"""
Section 12 — Cross-Reference Lab: correlation discovery across domains.

The novel analytical layer no DESE tool provides.
"""

import streamlit as st

from utils.data_loader import load_gateway_hs_panel

st.set_page_config(page_title="Correlation Lab | LEHS", page_icon="🔬", layout="wide")

st.title("Cross-Reference Lab — Correlation Discovery")
st.markdown(
    "Because every dataset lives in the same data model joined on (school_code, year), "
    "we can ask questions DESE's siloed tools can't. This section surfaces curated "
    "cross-domain correlations and lets you explore your own."
)

st.caption(
    "**Note:** Correlation is not causation. Patterns here are starting points for "
    "questions, not proof of cause and effect."
)

df = load_gateway_hs_panel()

if df.empty:
    st.warning("Master panel not yet loaded. See README for setup.")
    st.stop()

# ---------------------------------------------------------------------------
# Curated correlation views
# ---------------------------------------------------------------------------

st.header("Curated correlations")

curated = [
    "Spending category → outcomes",
    "Teacher diversity → subgroup growth",
    "Counselor ratio → college-going",
    "Early-warning chain: absenteeism → promotion → graduation → college",
    "AP access → AP equity by subgroup",
    "ELL reclassification timing → MCAS outcomes",
    "Discipline disproportionality → academic gaps",
    "Class size → student growth",
    "Community poverty → school spending → outcomes",
]

for item in curated:
    with st.expander(item):
        st.info("Chart placeholder — Phase 4")

st.divider()

# ---------------------------------------------------------------------------
# Custom explorer
# ---------------------------------------------------------------------------

st.header("Custom correlation explorer")
st.markdown("Pick any X and Y variable from the master panel to explore their relationship.")

numeric_cols = df.select_dtypes("number").columns.tolist() if not df.empty else []

if numeric_cols:
    col1, col2 = st.columns(2)
    with col1:
        x_var = st.selectbox("X variable", options=numeric_cols, index=0)
    with col2:
        y_var = st.selectbox("Y variable", options=numeric_cols, index=min(1, len(numeric_cols) - 1))
    st.info(f"Scatter chart placeholder — {x_var} vs. {y_var}, LEHS highlighted")
else:
    st.info("Numeric columns will appear once master panel is built.")

st.divider()

# ---------------------------------------------------------------------------
# Composite indices
# ---------------------------------------------------------------------------

st.header("Composite indices")
st.markdown(
    "User-configurable composite measures that combine multiple indicators into a "
    "single score. Adjust the weights to see how LEHS ranks under different value sets."
)

st.info("Index builder — Phase 4")
