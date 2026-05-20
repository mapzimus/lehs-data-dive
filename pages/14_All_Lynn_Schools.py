"""Section 18 — All Lynn Schools Explorer: filter/sort the full Lynn district."""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY
from utils.constants import LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="All Lynn Schools | LEHS", page_icon="🏫", layout="wide"
)
sidebar_attribution()

st.title("All Lynn Schools — Explorer")
st.markdown(
    "Filter and sort every school in Lynn Public Schools (LPS) — useful for "
    "parents choosing schools, administrators benchmarking internally, and "
    "anyone curious about the patterns inside the district."
)

enrollment = load_dataset("enrollment_demographics")
mcas = load_dataset("mcas_achievement")
attendance = load_dataset("student_attendance")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# Filter to Lynn district schools (any year)
lynn_all = enrollment[
    (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
    & (enrollment["ORG_TYPE"] == "School")
].copy()

if lynn_all.empty:
    st.warning("No Lynn district schools found in enrollment data.")
    st.stop()

# Get latest year per school
latest = lynn_all.sort_values("SY").groupby("ORG_CODE").tail(1)
latest_year = int(latest["SY"].max())

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

st.subheader(f"Filter Lynn schools (showing SY {latest_year} data)")

c1, c2, c3 = st.columns(3)
with c1:
    grade_filter = st.multiselect(
        "Grade level (any served)",
        options=["PK", "K-5", "Middle", "High"],
        default=[],
    )
with c2:
    min_enrollment = st.slider("Minimum enrollment", 0, 2000, 0, step=50)
with c3:
    ell_range = st.slider("% ELL range", 0, 100, (0, 100), step=5)

# Apply filters
filtered = latest.copy()
if grade_filter:
    # Use grade counts to classify
    grade_masks = []
    if "PK" in grade_filter:
        grade_masks.append(filtered["PK_CNT"] > 0)
    if "K-5" in grade_filter:
        grade_masks.append((filtered[["K_CNT", "G1_CNT", "G2_CNT", "G3_CNT", "G4_CNT", "G5_CNT"]].sum(axis=1) > 0))
    if "Middle" in grade_filter:
        grade_masks.append((filtered[["G6_CNT", "G7_CNT", "G8_CNT"]].sum(axis=1) > 0))
    if "High" in grade_filter:
        grade_masks.append((filtered[["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]].sum(axis=1) > 0))
    if grade_masks:
        combined_mask = grade_masks[0]
        for m in grade_masks[1:]:
            combined_mask = combined_mask | m
        filtered = filtered[combined_mask]

filtered = filtered[filtered["TOTAL_CNT"] >= min_enrollment]
filtered = filtered[
    (filtered["EL_PCT"] >= ell_range[0] / 100)
    & (filtered["EL_PCT"] <= ell_range[1] / 100)
]

st.caption(f"Showing **{len(filtered)} of {len(latest)}** Lynn schools.")

st.divider()

# ---------------------------------------------------------------------------
# Sortable scorecard
# ---------------------------------------------------------------------------

display = filtered[[
    "ORG_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT",
    "HN_PCT", "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT",
]].rename(columns={
    "ORG_NAME": "School",
    "TOTAL_CNT": "Enrollment",
    "EL_PCT": "% ELL",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% SPED",
    "HN_PCT": "% High Needs",
    "HL_PCT": "% Hispanic/Latino",
    "BAA_PCT": "% Black/AA",
    "AS_PCT": "% Asian",
    "WH_PCT": "% White",
})

# Highlight LEHS
def highlight_lehs(row):
    if "Lynn English" in str(row["School"]):
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)

# Format
display["Enrollment"] = display["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
for c in display.columns:
    if c.startswith("%"):
        display[c] = display[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

st.dataframe(display.sort_values("School").style.apply(highlight_lehs, axis=1),
             use_container_width=True, hide_index=True, height=500)

st.divider()

# ---------------------------------------------------------------------------
# Scatter: enrollment vs % ELL for all Lynn schools
# ---------------------------------------------------------------------------

st.subheader("Lynn schools — Enrollment vs. % ELL")

scatter_df = filtered.dropna(subset=["TOTAL_CNT", "EL_PCT"]).copy()
scatter_df["is_lehs"] = scatter_df["ORG_NAME"].str.contains("Lynn English", na=False)
scatter_df["category"] = scatter_df["is_lehs"].map({True: "LEHS", False: "Other Lynn"})

fig = px.scatter(
    scatter_df, x="TOTAL_CNT", y="EL_PCT", text="ORG_NAME",
    color="category",
    color_discrete_map={"LEHS": LEHS_GOLD, "Other Lynn": LEHS_NAVY},
    size="TOTAL_CNT", size_max=40,
    hover_name="ORG_NAME",
)
fig.update_traces(textposition="top center", textfont=dict(size=9))
fig.update_layout(
    **DEFAULT_LAYOUT, yaxis_tickformat=".0%",
    xaxis_title="Enrollment", yaxis_title="% ELL",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# District-level totals
# ---------------------------------------------------------------------------

st.subheader("District totals")

c1, c2, c3, c4 = st.columns(4)
with c1:
    total_enr = filtered["TOTAL_CNT"].sum()
    st.metric("Total Enrollment (filtered)", f"{int(total_enr):,}")
with c2:
    if total_enr > 0:
        wtd_ell = (filtered["TOTAL_CNT"] * filtered["EL_PCT"]).sum() / total_enr
        st.metric("Weighted % ELL", f"{wtd_ell:.0%}")
with c3:
    if total_enr > 0:
        wtd_li = (filtered["TOTAL_CNT"] * filtered["LI_PCT"]).sum() / total_enr
        st.metric("Weighted % Low Income", f"{wtd_li:.0%}")
with c4:
    st.metric("Schools shown", f"{len(filtered)}")

