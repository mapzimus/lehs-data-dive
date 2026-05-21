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
# Performance comparison across Lynn schools
# ---------------------------------------------------------------------------

st.subheader("Performance comparison — attendance + MCAS proficiency")
st.caption("Latest available year for each school. Blank cells = no data published for that school × indicator.")

perf = filtered[["ORG_CODE", "ORG_NAME"]].copy()

# Attendance (all-students FY rate + chronic absent)
if not attendance.empty:
    a = attendance.copy()
    a["PCT_CHRON_ABS_10"] = pd.to_numeric(a["PCT_CHRON_ABS_10"], errors="coerce")
    a["ATTEND_RATE"] = pd.to_numeric(a["ATTEND_RATE"], errors="coerce")
    a = a[(a["STU_GRP"] == "All Students") & (a["ATTEND_PERIOD"] == "FY")]
    a_latest = a.sort_values("SY").groupby("ORG_CODE").tail(1)[
        ["ORG_CODE", "ATTEND_RATE", "PCT_CHRON_ABS_10"]
    ]
    perf = perf.merge(a_latest, on="ORG_CODE", how="left")

# MCAS grade 10 ELA + Math (for high schools)
if not mcas.empty:
    m = mcas.copy()
    m["M_PLUS_E_PCT"] = pd.to_numeric(m.get("M_PLUS_E_PCT"), errors="coerce")
    g10 = m[(m["TEST_GRADE"].astype(str) == "10") & (m["STU_GRP"] == "All Students")]
    for subj, label in [("ELA", "MCAS G10 ELA M+E%"), ("MATH", "MCAS G10 Math M+E%")]:
        s = g10[g10["SUBJECT_CODE"] == subj].sort_values("SY").groupby("ORG_CODE").tail(1)
        s = s[["ORG_CODE", "M_PLUS_E_PCT"]].rename(columns={"M_PLUS_E_PCT": label})
        perf = perf.merge(s, on="ORG_CODE", how="left")
    # Grade 3-8 average for elementary/middle
    g38 = m[m["TEST_GRADE"].astype(str).isin(["03", "04", "05", "06", "07", "08",
                                                 "3", "4", "5", "6", "7", "8"])
            & (m["STU_GRP"] == "All Students")]
    for subj, label in [("ELA", "MCAS 3-8 ELA M+E%"), ("MATH", "MCAS 3-8 Math M+E%")]:
        s = g38[g38["SUBJECT_CODE"] == subj]
        if not s.empty:
            latest_sy = s.sort_values("SY").groupby("ORG_CODE")["SY"].max().reset_index()
            s_latest = s.merge(latest_sy, on=["ORG_CODE", "SY"])
            s_avg = s_latest.groupby("ORG_CODE")["M_PLUS_E_PCT"].mean().reset_index()
            s_avg = s_avg.rename(columns={"M_PLUS_E_PCT": label})
            perf = perf.merge(s_avg, on="ORG_CODE", how="left")

perf_display = perf.copy().rename(columns={"ORG_NAME": "School"})
for c in perf_display.columns:
    if c.endswith("%") or c in ("ATTEND_RATE", "PCT_CHRON_ABS_10"):
        perf_display[c] = perf_display[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
perf_display = perf_display.drop(columns=["ORG_CODE"]).rename(columns={
    "ATTEND_RATE": "Attendance",
    "PCT_CHRON_ABS_10": "Chronic Absent",
})

def highlight_lehs_perf(row):
    if "Lynn English" in str(row.get("School", "")):
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)

st.dataframe(perf_display.sort_values("School").style.apply(highlight_lehs_perf, axis=1),
             use_container_width=True, hide_index=True, height=500)

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

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Enrollment & demographics': enrollment,
        'MCAS achievement': mcas,
        'Student attendance': attendance,
        'Per-school performance panel': perf,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

