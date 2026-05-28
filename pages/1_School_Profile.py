"""Section 1 — School Profile: demographics, enrollment trends, headline metrics."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import (
    IMAGES_DIR,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
)
from utils.data_loader import load_dataset
from utils.interpret import (
    chronic_absenteeism_methodology_note,
    sy_label,
    yoy_delta,
)

st.set_page_config(page_title="School Profile | LEHS", page_icon="📊", layout="wide")
sidebar_attribution()

st.title("Lynn English High School — Profile")
st.markdown(
    "Demographics, enrollment trends, and headline metrics for LEHS, going "
    "back to the 1992–93 school year."
)

# ---------------------------------------------------------------------------
# Visual identity row — small building photo on the left, principal
# block on the right. Previously the building photo was full-width and
# the Rardy block sat in its own row below; that pushed everything
# else far down the page. One compact row reads as "here's the place,
# here's who runs it" without dominating the viewport.
# ---------------------------------------------------------------------------

_id_l, _id_r = st.columns([1, 2], gap="medium")
with _id_l:
    st.image(
        str(IMAGES_DIR / "lehs-building.jpg"),
        use_container_width=True,
        caption="Main entrance, O'Callaghan Way",
    )
with _id_r:
    _p_l, _p_r = st.columns([1, 3], gap="small")
    with _p_l:
        st.image(str(IMAGES_DIR / "principal-rardy-pena.jpg"), width=120)
    with _p_r:
        st.markdown(
            "### Principal: Rardy Peña  \n"
            "Lynn English High School is led by **Principal Rardy Peña**. "
            "The data below tells a story about students, demographics, "
            "and outcomes — the people leading the school's response to "
            "that story matter just as much."
        )

# DESE ESSA accountability classification was previously rendered at
# the top of the page; that framed every visitor's first impression of
# LEHS as the worst news the state publishes about it. Block moved to
# near the bottom of the page (right before the history cross-link),
# preserved verbatim but no longer dominating the hero. See the
# render-block below the data charts.

enrollment = load_dataset("enrollment_demographics")
if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()
district = enrollment[
    (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE) & (enrollment["ORG_TYPE"] == "District")
].sort_values("SY").copy()

if lehs.empty:
    st.error(f"No rows for LEHS school code {LEHS_SCHOOL_CODE}")
    st.stop()

current = lehs.iloc[-1]
prior = lehs.iloc[-2] if len(lehs) > 1 else None
oldest = lehs.iloc[0]
# A year that fully populates demographic columns
first_with_demos = lehs.dropna(subset=["HL_PCT"]).iloc[0] if not lehs.dropna(subset=["HL_PCT"]).empty else oldest

# ---------------------------------------------------------------------------
# Hero metrics
# ---------------------------------------------------------------------------

st.subheader(f"At a Glance — School Year {sy_label(current['SY'])}")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.metric(
        "Total Enrollment",
        f"{int(current['TOTAL_CNT']):,}",
        yoy_delta(current["TOTAL_CNT"], prior["TOTAL_CNT"], "students") if prior is not None else "",
    )
with c2:
    st.metric(
        "% English Learners",
        f"{current['EL_PCT']:.0%}",
        yoy_delta(current["EL_PCT"] * 100, prior["EL_PCT"] * 100, "pts") if prior is not None else "",
    )
with c3:
    st.metric(
        "% Low Income",
        f"{current['LI_PCT']:.0%}",
        yoy_delta(current["LI_PCT"] * 100, prior["LI_PCT"] * 100, "pts") if prior is not None else "",
    )
with c4:
    st.metric(
        "% Students w/ Disabilities",
        f"{current['SWD_PCT']:.0%}",
        yoy_delta(current["SWD_PCT"] * 100, prior["SWD_PCT"] * 100, "pts") if prior is not None else "",
    )
with c5:
    st.metric(
        "% High Needs",
        f"{current['HN_PCT']:.0%}",
        yoy_delta(current["HN_PCT"] * 100, prior["HN_PCT"] * 100, "pts") if prior is not None else "",
        help=(
            "DESE's 'High Needs' flag fires when a student is in at least ONE "
            "of: English Learner, Economically Disadvantaged, or Students with "
            "Disabilities. It's a UNION, not an intersection — so it's higher "
            "than any single subgroup % but says nothing about how much those "
            "subgroups overlap. (The dashboard works from district-level "
            "aggregates, so a true EL-AND-LI cross-tab isn't available here.)"
        ),
    )

# ---------------------------------------------------------------------------
# Headline academic outcome — Gap #6: the Profile previously showed
# zero academic stats, forcing visitors to know to click out to
# Academic Performance. One outcome tile + a link closes the loop
# without duplicating the deep-dive page.
# ---------------------------------------------------------------------------

_grad = load_dataset("graduation_rates")
_g_row = None
if not _grad.empty:
    _g_lehs = _grad[
        (_grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_grad["ORG_TYPE"] == "School")
        & (_grad["STU_GRP"] == "All Students")
        & (_grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    ].sort_values("SY")
    if not _g_lehs.empty:
        _g_row = _g_lehs.iloc[-1]

_mcas = load_dataset("mcas_achievement")
_m_ela_row = None
_m_math_row = None
if not _mcas.empty:
    _g10 = _mcas[
        (_mcas["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_mcas["ORG_TYPE"] == "School")
        & (_mcas["STU_GRP"] == "All Students")
        & (_mcas["TEST_GRADE"] == "10")
    ]
    _ela = _g10[_g10["SUBJECT_CODE"] == "ELA"].sort_values("SY")
    _math = _g10[_g10["SUBJECT_CODE"] == "MATH"].sort_values("SY")
    if not _ela.empty:
        _m_ela_row = _ela.iloc[-1]
    if not _math.empty:
        _m_math_row = _math.iloc[-1]

if _g_row is not None or _m_ela_row is not None or _m_math_row is not None:
    st.caption(
        "Quick academic snapshot — see **[Academic Performance](/Academic_Performance)** "
        "for the full subject-by-subject MCAS breakdown with confidence intervals."
    )
    ac1, ac2, ac3, _ac4 = st.columns([1, 1, 1, 1])
    with ac1:
        if _g_row is not None:
            st.metric(
                f"4-yr Graduation Rate (cohort {int(_g_row['SY'])})",
                f"{float(_g_row['GRAD_PCT']):.0%}",
            )
    with ac2:
        if _m_ela_row is not None:
            st.metric(
                f"MCAS Gr10 ELA — % M+E (SY {sy_label(int(_m_ela_row['SY']))})",
                f"{float(_m_ela_row['M_PLUS_E_PCT']):.0%}",
                help="% of Grade 10 LEHS students Meeting + Exceeding expectations on ELA.",
            )
    with ac3:
        if _m_math_row is not None:
            st.metric(
                f"MCAS Gr10 Math — % M+E (SY {sy_label(int(_m_math_row['SY']))})",
                f"{float(_m_math_row['M_PLUS_E_PCT']):.0%}",
                help="% of Grade 10 LEHS students Meeting + Exceeding expectations on Math.",
            )

# ---------------------------------------------------------------------------
# Long-term transformation
# ---------------------------------------------------------------------------

st.subheader("How LEHS has changed since 1992")
st.caption(
    "The school today is not the school 30 years ago. These long-term deltas "
    "show how dramatically the student population has shifted in one generation."
)

c1, c2, c3, c4 = st.columns(4)


def long_term_metric(col, label: str, fmt: str = ".0%"):
    if col not in lehs.columns:
        return
    sub = lehs.dropna(subset=[col])
    if len(sub) < 2:
        return
    first = sub.iloc[0]
    last = sub.iloc[-1]
    diff_pts = (last[col] - first[col]) * 100
    direction = "+" if diff_pts >= 0 else ""
    val_now = f"{last[col]:{fmt}}" if isinstance(last[col], (int, float)) else "—"
    delta = f"{direction}{diff_pts:.0f} pts since SY {sy_label(first['SY'])}"
    return val_now, delta


with c1:
    res = long_term_metric("HL_PCT", "% Hispanic/Latino")
    if res:
        st.metric("% Hispanic/Latino", res[0], res[1])
with c2:
    res = long_term_metric("FLNE_PCT", "% First Lang Not English")
    if res:
        st.metric("% First Lang Not English", res[0], res[1])
with c3:
    res = long_term_metric("LI_PCT", "% Low Income")
    if res:
        st.metric("% Low Income", res[0], res[1])
with c4:
    res = long_term_metric("WH_PCT", "% White")
    if res:
        st.metric("% White", res[0], res[1])

# ---------------------------------------------------------------------------
# (History section was moved out to its own page — pages/15_LEHS_History.py.
# The Profile page is now data-only; the bottom-of-page footer links into
# the dedicated history page for the narrative side.)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Total enrollment trend
# ---------------------------------------------------------------------------

st.subheader("Total Enrollment Over Time")

fig = px.line(
    lehs, x="SY", y="TOTAL_CNT", markers=True,
)
fig.update_traces(
    line=dict(color=LEHS_NAVY, width=3),
    marker=dict(size=8),
    text=lehs["TOTAL_CNT"].apply(lambda v: f"{int(v):,}" if pd.notna(v) else ""),
    textposition="top center",
    mode="lines+markers+text",
    textfont=dict(size=10, color=LEHS_NAVY),
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year",
                   title="Lynn English High School — total enrollment by school year")
st.plotly_chart(fig, use_container_width=True)

peak_year = lehs.loc[lehs["TOTAL_CNT"].idxmax()]
trough_year = lehs.loc[lehs["TOTAL_CNT"].idxmin()]
st.caption(
    f"Enrollment peaked at **{int(peak_year['TOTAL_CNT']):,}** students in "
    f"SY {sy_label(peak_year['SY'])} and reached its lowest at "
    f"**{int(trough_year['TOTAL_CNT']):,}** in SY {sy_label(trough_year['SY'])}."
)

# ---------------------------------------------------------------------------
# Student-teacher ratio over time — Gap #1: the first question families
# ask. Pairs naturally with the enrollment trend above; if enrollment
# went up but staffing didn't, the ratio climbs (bad). If both moved
# together, the ratio's flat (neutral).
# ---------------------------------------------------------------------------

st.subheader("Student–teacher ratio over time")
st.caption(
    "DESE's reported student-to-teacher ratio for LEHS, computed from the "
    "'All Teachers' FTE total. Lower is better (smaller classes)."
)

_td = load_dataset("teacher_data")
if not _td.empty:
    _tr = _td[
        (_td["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_td["ORG_TYPE"] == "School")
        & (_td["SUBJECT"] == "All Teachers")
    ].sort_values("SY").copy()
    # STU_TCHR_RATIO ships as "13.2 to 1" — parse out the float.
    _tr["ratio_num"] = pd.to_numeric(
        _tr["STU_TCHR_RATIO"].astype(str).str.split("to").str[0].str.strip(),
        errors="coerce",
    )
    _tr = _tr.dropna(subset=["ratio_num"])
    if not _tr.empty:
        fig_r = px.line(_tr, x="SY", y="ratio_num", markers=True)
        fig_r.update_traces(
            line=dict(color=LEHS_GOLD, width=3),
            marker=dict(size=8, color=LEHS_NAVY),
            text=_tr["ratio_num"].apply(lambda v: f"{v:.1f}:1"),
            textposition="top center",
            mode="lines+markers+text",
            textfont=dict(size=10, color=LEHS_NAVY),
        )
        fig_r.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_title="Students per teacher",
            xaxis_title="School Year",
            title="Lynn English High School — student-to-teacher ratio",
        )
        st.plotly_chart(fig_r, use_container_width=True)
        _latest_r = _tr.iloc[-1]
        _earliest_r = _tr.iloc[0]
        st.caption(
            f"Latest available: **{_latest_r['ratio_num']:.1f} students per teacher** "
            f"in SY {sy_label(int(_latest_r['SY']))}. Earliest reported in this "
            f"dataset: {_earliest_r['ratio_num']:.1f}:1 in SY "
            f"{sy_label(int(_earliest_r['SY']))}."
        )
    else:
        st.caption("Student-teacher ratio data isn't loaded for LEHS yet.")

# ---------------------------------------------------------------------------
# LEHS vs Lynn district — same-year comparison
# ---------------------------------------------------------------------------

st.subheader(f"LEHS vs. Lynn district ({sy_label(current['SY'])})")
st.caption(
    "How LEHS's student body compares to the Lynn Public Schools district "
    "average (across all 22 schools, PK-12). For school-to-school "
    "comparison against other Lynn high schools, see "
    "[Lynn Schools](/Lynn_Schools) (Compare group)."
)

if not district.empty:
    d_current = district.iloc[-1]
    rows = [
        ("% Hispanic/Latino",          "HL_PCT"),
        ("% English Learners",         "EL_PCT"),
        ("% Low Income",               "LI_PCT"),
        ("% High Needs",               "HN_PCT"),
        ("% First Lang Not English",   "FLNE_PCT"),
        ("% Students w/ Disabilities", "SWD_PCT"),
    ]
    data = {"Indicator": [r[0] for r in rows],
            "LEHS":            [current[r[1]] for r in rows],
            "Lynn District":   [d_current[r[1]] for r in rows]}
    compare = pd.DataFrame(data)
    long = compare.melt(id_vars="Indicator", var_name="Scope", value_name="Pct").dropna()
    fig = px.bar(
        long, x="Indicator", y="Pct", color="Scope", barmode="group",
        text=long["Pct"].apply(lambda x: f"{x:.0%}"),
        color_discrete_map={
            "LEHS":          LEHS_GOLD,
            "Lynn District": LEHS_NAVY,
        },
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                       xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Race/ethnicity — current snapshot + composition over time
# ---------------------------------------------------------------------------

st.subheader(f"Race / Ethnicity — {sy_label(current['SY'])}")

col_a, col_b = st.columns([1, 2])

with col_a:
    race_data = pd.DataFrame({
        "Group": [
            "Hispanic/Latino", "African American/Black", "Asian", "White",
            "Multi-Race", "Native American", "Native Hawaiian/PI",
        ],
        "Pct": [
            current["HL_PCT"], current["BAA_PCT"], current["AS_PCT"], current["WH_PCT"],
            current["MNHL_PCT"], current["AIAN_PCT"], current["NHPI_PCT"],
        ],
    })
    race_data = race_data[race_data["Pct"] > 0].sort_values("Pct", ascending=False)
    fig = px.pie(
        race_data, names="Group", values="Pct", hole=0.5,
        color="Group",
        color_discrete_map={
            "Hispanic/Latino":         SUBGROUP_PALETTE["Hispanic/Latino"],
            "African American/Black":  SUBGROUP_PALETTE["African American/Black"],
            "Asian":                   SUBGROUP_PALETTE["Asian"],
            "White":                   SUBGROUP_PALETTE["White"],
            "Multi-Race":              SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        },
    )
    fig.update_traces(textposition="inside", textinfo="percent+label", textfont_size=11)
    fig.update_layout(**DEFAULT_LAYOUT, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.markdown("**Composition over time**")
    race_long = lehs.melt(
        id_vars=["SY"],
        value_vars=["HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "MNHL_PCT"],
        var_name="Group",
        value_name="Pct",
    )
    label_map = {
        "HL_PCT": "Hispanic/Latino",
        "BAA_PCT": "African American/Black",
        "AS_PCT": "Asian",
        "WH_PCT": "White",
        "MNHL_PCT": "Multi-Race",
    }
    race_long["Group"] = race_long["Group"].map(label_map)
    race_long = race_long.dropna(subset=["Pct"])
    fig = px.area(
        race_long, x="SY", y="Pct", color="Group",
        color_discrete_map={
            "Hispanic/Latino":        SUBGROUP_PALETTE["Hispanic/Latino"],
            "African American/Black": SUBGROUP_PALETTE["African American/Black"],
            "Asian":                  SUBGROUP_PALETTE["Asian"],
            "White":                  SUBGROUP_PALETTE["White"],
            "Multi-Race":             SUBGROUP_PALETTE["Multi-Race, Non-Hispanic/Latino"],
        },
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                       xaxis_title="School Year")
    st.plotly_chart(fig, use_container_width=True)

# Detailed race table
st.markdown("**Detailed race/ethnicity counts and shares (latest year)**")
total = current["TOTAL_CNT"]
race_table = pd.DataFrame({
    "Group": ["Hispanic/Latino", "African American/Black", "Asian", "White",
              "Multi-Race", "Native American", "Native Hawaiian/PI"],
    "%":     [current["HL_PCT"], current["BAA_PCT"], current["AS_PCT"], current["WH_PCT"],
              current["MNHL_PCT"], current["AIAN_PCT"], current["NHPI_PCT"]],
})
race_table["Approx. students"] = (race_table["%"] * total).round().astype("Int64")
race_table = race_table.sort_values("%", ascending=False)
race_table["%"] = race_table["%"].apply(lambda x: f"{x:.1%}")
race_table["Approx. students"] = race_table["Approx. students"].apply(
    lambda x: f"{int(x):,}" if pd.notna(x) else "—"
)
st.dataframe(race_table, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Gender breakdown
# ---------------------------------------------------------------------------

st.subheader("Gender Breakdown Over Time")

gender_long = lehs.melt(
    id_vars=["SY"],
    value_vars=["FE_PCT", "MA_PCT", "NB_PCT"] if "NB_PCT" in lehs.columns else ["FE_PCT", "MA_PCT"],
    var_name="Gender", value_name="Pct",
).dropna(subset=["Pct"])
gender_long["Gender"] = gender_long["Gender"].map({
    "FE_PCT": "Female", "MA_PCT": "Male", "NB_PCT": "Non-binary",
})
fig = px.area(
    gender_long, x="SY", y="Pct", color="Gender",
    color_discrete_map={"Female": "#D81B60", "Male": "#1E88E5", "Non-binary": "#FFC107"},
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                   xaxis_title="School Year")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Selected populations trend
# ---------------------------------------------------------------------------

st.subheader("Selected Populations Over Time")
st.caption(
    "Six key student-group classifications that drive resource allocation, "
    "accountability calculations, and federal/state programmatic support. "
    "**Economically Disadvantaged (ECD)** is DESE's current direct-certification "
    "measure (SNAP, TANF, foster, homeless); **Low Income (LI)** is the "
    "older Title-I-style flag — they capture nearly the same population but "
    "differ by definition, so both are shown."
)

# Gap #3: add Economically Disadvantaged (ECD_PCT) alongside Low Income
# so the FRPL/direct-cert vs Title-I distinction is visible.
_pop_cols = ["EL_PCT", "LI_PCT", "ECD_PCT", "SWD_PCT", "HN_PCT", "FLNE_PCT"]
_pop_cols = [c for c in _pop_cols if c in lehs.columns]
pop_long = lehs.melt(
    id_vars=["SY"],
    value_vars=_pop_cols,
    var_name="Group",
    value_name="Pct",
)
pop_labels = {
    "EL_PCT":   "English Learner",
    "LI_PCT":   "Low Income",
    "ECD_PCT":  "Economically Disadvantaged",
    "SWD_PCT":  "Students w/ Disabilities",
    "HN_PCT":   "High Needs",
    "FLNE_PCT": "First Lang Not English",
}
pop_long["Group"] = pop_long["Group"].map(pop_labels)
pop_long = pop_long.dropna(subset=["Pct"])

fig = px.line(
    pop_long, x="SY", y="Pct", color="Group", markers=True,
    color_discrete_map={
        "English Learner":            SUBGROUP_PALETTE["English Learner"],
        "Low Income":                 SUBGROUP_PALETTE["Low Income"],
        "Economically Disadvantaged": "#8B4513",
        "Students w/ Disabilities":   SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":                 SUBGROUP_PALETTE["High Needs"],
        "First Lang Not English":     "#0277BD",
    },
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of Students",
                   xaxis_title="School Year")
st.plotly_chart(fig, use_container_width=True)

# Special pull-out: ELL trajectory
ell_with_data = lehs.dropna(subset=["EL_PCT"])
if len(ell_with_data) >= 2:
    first_ell = ell_with_data.iloc[0]
    last_ell = ell_with_data.iloc[-1]
    st.markdown(
        f"**ELL share trajectory:** {first_ell['EL_PCT']:.0%} in SY "
        f"{sy_label(first_ell['SY'])} → **{last_ell['EL_PCT']:.0%}** in SY "
        f"{sy_label(last_ell['SY'])}  "
        f"*(+{(last_ell['EL_PCT'] - first_ell['EL_PCT']) * 100:.0f} percentage points)*."
    )

# ---------------------------------------------------------------------------
# Grade-level enrollment + grade-by-race breakdown
# ---------------------------------------------------------------------------

st.subheader(f"Grade-Level Enrollment ({sy_label(current['SY'])})")

grade_data = pd.DataFrame({
    "Grade": ["9", "10", "11", "12"],
    "Students": [current["G9_CNT"], current["G10_CNT"], current["G11_CNT"], current["G12_CNT"]],
})

fig = go.Figure(go.Bar(
    x=grade_data["Grade"],
    y=grade_data["Students"],
    text=grade_data["Students"].apply(lambda v: f"{int(v):,}" if pd.notna(v) else ""),
    textposition="outside",
    marker_color=LEHS_NAVY,
))
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="Grade")
st.plotly_chart(fig, use_container_width=True)

# Pull-out: 9-12 attrition narrative
total_hs = sum(current[c] for c in ["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]
                if pd.notna(current[c]))
if pd.notna(current["G9_CNT"]) and pd.notna(current["G12_CNT"]):
    if current["G9_CNT"] < current["G12_CNT"]:
        narrowing = (current["G12_CNT"] - current["G9_CNT"]) / current["G12_CNT"]
        narrative = (
            f"Grade 9 enrollment is **{narrowing:.0%} smaller** than grade 12 — "
            f"could reflect shrinking incoming cohorts. See **Success After HS** "
            f"for 9th-to-10th promotion rates and attrition analysis."
        )
    else:
        narrowing = (current["G9_CNT"] - current["G12_CNT"]) / current["G9_CNT"]
        narrative = (
            f"Grade 9 enrollment is **{narrowing:.0%} larger** than grade 12 — "
            f"the standard funneling pattern (some students leave before "
            f"graduation). See **Success After HS** for cohort-tracked attrition."
        )
    st.caption(narrative)

# ---------------------------------------------------------------------------
# Enrollment by selected populations — counts, not just percentages
# ---------------------------------------------------------------------------

st.subheader(f"Selected populations — count and share ({sy_label(current['SY'])})")

pop_counts = pd.DataFrame({
    "Group": ["English Learners", "First Lang Not English", "Low Income",
              "Students w/ Disabilities", "High Needs"],
    "Count": [current.get("EL_CNT"), current.get("FLNE_CNT"), current.get("LI_CNT"),
              current.get("SWD_CNT"), current.get("HN_CNT")],
    "Share": [current.get("EL_PCT"), current.get("FLNE_PCT"), current.get("LI_PCT"),
              current.get("SWD_PCT"), current.get("HN_PCT")],
})
pop_counts = pop_counts.dropna(subset=["Count"])
pop_counts["Count"] = pop_counts["Count"].astype(int)
pop_counts["Display"] = pop_counts.apply(
    lambda r: f"{r['Count']:,} ({r['Share']:.0%})", axis=1
)

fig = go.Figure(go.Bar(
    y=pop_counts["Group"],
    x=pop_counts["Count"],
    text=pop_counts["Display"],
    textposition="outside",
    orientation="h",
    marker_color=LEHS_GOLD,
))
fig.update_layout(**DEFAULT_LAYOUT, xaxis_title="Students", yaxis_title="",
                   xaxis_range=[0, pop_counts["Count"].max() * 1.25])
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Where LEHS students live — Gap #4: tie the demographic story to a
# place. A kernel-density thumbnail from the original catchment
# research, with a hand-off to Where Students Live for the full
# investigation.
# ---------------------------------------------------------------------------

_catchment_thumb = PROCESSED_DIR / "lehs_research" / "kde_heatmap.png"
if _catchment_thumb.exists():
    st.subheader("Where LEHS students live")
    _cm_l, _cm_r = st.columns([2, 3], gap="medium")
    with _cm_l:
        st.image(
            str(_catchment_thumb),
            use_container_width=True,
            caption="Kernel-density estimate of LEHS student residences (aggregated for privacy).",
        )
    with _cm_r:
        st.markdown(
            "LEHS's demographic story has a geographic shape. Roughly **75%** "
            "of the school's students live within a tight cluster of "
            "neighborhoods in central and south Lynn, with smaller pockets "
            "further out. The catchment overlaps with the city's denser "
            "rental stock, lower-income tracts, and the corridor where "
            "Lynn's foreign-born population concentrates."
        )
        st.page_link(
            "pages/16_Where_Students_Live.py",
            label="Open Where Students Live →",
            use_container_width=True,
        )
        st.caption(
            "Built from private student records (Lynn Public Schools SIS); "
            "spatially aggregated to prevent individual identification."
        )

# ---------------------------------------------------------------------------
# Student mobility — Gap #2: how stable is the LEHS student body
# during a given school year? Schools with high churn have a very
# different operational reality than schools with low churn even at
# the same headcount.
# ---------------------------------------------------------------------------

_mob = load_dataset("student_mobility")
if not _mob.empty:
    _mob_lehs = _mob[
        (_mob["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_mob["ORG_TYPE"] == "School")
        & (_mob["STU_GRP"] == "All Students")
    ].sort_values("SY").copy()
    if not _mob_lehs.empty:
        st.subheader("Student mobility")
        st.caption(
            "How much of LEHS's student body turns over during a school year. "
            "**Stability** = % enrolled the whole year. **Churn** = % who "
            "moved in or out mid-year. **Intake** = % new during the year. "
            "Lower churn means a more predictable instructional environment."
        )

        _latest_m = _mob_lehs.iloc[-1]
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric(
                "Stability rate",
                f"{float(_latest_m['STAB_PCT']):.0%}",
                help="% of LEHS students who stayed enrolled the entire school year.",
            )
        with m2:
            st.metric(
                "Churn rate",
                f"{float(_latest_m['CHURN_PCT']):.0%}",
                help="% of the school year's enrollment that moved in or out mid-year.",
            )
        with m3:
            st.metric(
                "Mid-year intake",
                f"{float(_latest_m['INTAKE_PCT']):.0%}",
                help="% of students who started at LEHS partway through the school year.",
            )
        with m4:
            st.metric("School year", sy_label(int(_latest_m["SY"])))

        _mob_long = _mob_lehs.melt(
            id_vars=["SY"],
            value_vars=["STAB_PCT", "CHURN_PCT", "INTAKE_PCT"],
            var_name="Metric", value_name="Pct",
        )
        _mob_label = {
            "STAB_PCT": "Stability",
            "CHURN_PCT": "Churn",
            "INTAKE_PCT": "Mid-year intake",
        }
        _mob_long["Metric"] = _mob_long["Metric"].map(_mob_label)
        _mob_long = _mob_long.dropna(subset=["Pct"])
        fig_m = px.line(
            _mob_long, x="SY", y="Pct", color="Metric", markers=True,
            color_discrete_map={
                "Stability": LEHS_NAVY,
                "Churn": "#D32F2F",
                "Mid-year intake": "#F57C00",
            },
        )
        fig_m.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="Share of students",
            xaxis_title="School Year",
            title="LEHS student mobility over time",
        )
        st.plotly_chart(fig_m, use_container_width=True)

# ---------------------------------------------------------------------------
# Attendance & Chronic Absenteeism
# DESE accountability metric: share missing ≥10% of school days. LEHS hovers
# near 50% — one of the most consequential numbers on the page.
# ---------------------------------------------------------------------------

attendance = load_dataset("student_attendance")
if not attendance.empty:
    eoy = attendance[attendance["ATTEND_PERIOD"] == "End of Year"].copy()
    lehs_att = eoy[(eoy["ORG_CODE"] == LEHS_SCHOOL_CODE) & (eoy["STU_GRP"] == "All Students")].sort_values("SY")
    dist_att = eoy[
        (eoy["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (eoy["ORG_TYPE"] == "District")
        & (eoy["STU_GRP"] == "All Students")
    ].sort_values("SY")
    state_att = eoy[(eoy["ORG_TYPE"] == "State") & (eoy["STU_GRP"] == "All Students")].sort_values("SY")

    if not lehs_att.empty:
        st.divider()
        st.subheader("Attendance & Chronic Absenteeism")

        latest_att = lehs_att.iloc[-1]
        prior_att = lehs_att.iloc[-2] if len(lehs_att) > 1 else None

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                f"Chronic absenteeism (SY {sy_label(int(latest_att['SY']))})",
                f"{latest_att['PCT_CHRON_ABS_10']:.0%}" if pd.notna(latest_att["PCT_CHRON_ABS_10"]) else "—",
                (
                    yoy_delta(
                        latest_att["PCT_CHRON_ABS_10"] * 100,
                        prior_att["PCT_CHRON_ABS_10"] * 100,
                        "pts",
                    )
                    if prior_att is not None
                    else ""
                ),
            )
        with c2:
            st.metric(
                "Severely absent (≥20% of days)",
                f"{latest_att['PCT_CHRON_ABS_20']:.0%}" if pd.notna(latest_att["PCT_CHRON_ABS_20"]) else "—",
            )
        with c3:
            st.metric(
                "Average attendance rate",
                f"{latest_att['ATTEND_RATE']:.0%}" if pd.notna(latest_att["ATTEND_RATE"]) else "—",
            )

        # Trend: LEHS vs Lynn district vs MA state
        trend_frames = []
        for label, frame in [("LEHS", lehs_att), ("Lynn District", dist_att), ("Massachusetts", state_att)]:
            t = frame[["SY", "PCT_CHRON_ABS_10"]].dropna().copy()
            if not t.empty:
                t["Scope"] = label
                trend_frames.append(t)
        if trend_frames:
            trend_df = pd.concat(trend_frames, ignore_index=True)
            trend_df["label"] = trend_df["PCT_CHRON_ABS_10"].apply(lambda x: f"{x:.0%}")
            fig = px.line(
                trend_df.sort_values(["Scope", "SY"]),
                x="SY", y="PCT_CHRON_ABS_10", color="Scope", markers=True, text="label",
                color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": "#455A64"},
            )
            fig.update_traces(textposition="top center", textfont=dict(size=10))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".0%",
                yaxis_title="% chronically absent (≥10% of days)",
                xaxis_title="School Year",
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "The post-COVID spike (SY 2022) is visible across MA, but LEHS "
                "has not recovered to its pre-pandemic baseline. Even the "
                "current rate (~half of students) is substantially elevated "
                "vs. the statewide average."
            )

        # Subgroup breakdown — latest year, sorted high-to-low
        sub = eoy[
            (eoy["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (eoy["SY"] == latest_att["SY"])
            & (eoy["STU_GRP"] != "All Students")
        ].copy()
        sub = sub.dropna(subset=["PCT_CHRON_ABS_10"]).sort_values("PCT_CHRON_ABS_10")
        if not sub.empty:
            st.markdown(f"**Chronic absenteeism by student group — SY {sy_label(int(latest_att['SY']))}**")
            sub["label"] = sub["PCT_CHRON_ABS_10"].apply(lambda x: f"{x:.0%}")
            fig = px.bar(
                sub, x="PCT_CHRON_ABS_10", y="STU_GRP", orientation="h", text="label",
            )
            fig.update_traces(marker_color=LEHS_NAVY, textposition="outside", cliponaxis=False)
            fig.add_vline(
                x=latest_att["PCT_CHRON_ABS_10"], line_dash="dash", line_color=LEHS_GOLD,
                annotation_text="All-students rate", annotation_position="top",
            )
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_tickformat=".0%", xaxis_title="% chronically absent",
                yaxis_title="", height=max(360, 28 * len(sub)),
            )
            st.plotly_chart(fig, use_container_width=True)

        # Geographic context — pull in the lehs_research distance/spatial analyses
        st.markdown("**Where chronically absent students live**")
        st.caption(
            "Internal research on the geographic distribution of LEHS "
            "absenteeism — chronic absenteeism rises with distance from "
            "the school, and clusters in identifiable parts of Lynn."
        )
        research_dir = PROCESSED_DIR / "lehs_research"
        col_a, col_b = st.columns(2)
        absence_band = research_dir / "absence_by_distance_band.png"
        hexbin = research_dir / "hexbin_absenteeism_100m.png"
        if absence_band.exists():
            with col_a:
                st.image(
                    str(absence_band),
                    caption="Average absenteeism by distance from LEHS (banded).",
                    use_container_width=True,
                )
        if hexbin.exists():
            with col_b:
                st.image(
                    str(hexbin),
                    caption="Spatial clustering of chronic absenteeism (100 m hex grid).",
                    use_container_width=True,
                )

        st.caption(chronic_absenteeism_methodology_note())

# ---------------------------------------------------------------------------
# DESE ESSA accountability — moved here from the top of the page. Still
# important context, but placing it at the bottom lets the data above
# speak for itself before a visitor sees the state's intervention label.
# ---------------------------------------------------------------------------

st.divider()
st.subheader("State accountability status")
st.caption(
    "DESE's official ESSA-era classification for LEHS — what the state "
    "publishes about the school's overall improvement standing."
)

_acc = load_dataset("accountability")
if not _acc.empty:
    _lehs_acc = _acc[(_acc["ORG_CODE"] == LEHS_SCHOOL_CODE) & (_acc["ORG_TYPE"] == "School")]
    _dist_acc = _acc[(_acc["ORG_CODE"] == LYNN_DISTRICT_CODE) & (_acc["ORG_TYPE"] == "District")]
    if not _lehs_acc.empty:
        _row = _lehs_acc.iloc[0]
        _sy = _row["SY"]
        _classif = _row["CLASSIFICATION"]
        _reason = _row["REASON"]
        _pct = _row["PERCENTILE"]
        _progress = _row["PROGRESS_PCT"]

        # Color the callout by classification severity. DESE has 4 buckets;
        # everything starting with "Requiring" is in the intervention tier.
        if isinstance(_classif, str) and _classif.lower().startswith("requiring"):
            _alert = st.error
            _icon = "⚠️"
        elif isinstance(_classif, str) and _classif.lower().startswith("not requiring"):
            _alert = st.success
            _icon = "✓"
        else:
            _alert = st.info
            _icon = "ℹ️"

        _district_blurb = ""
        if not _dist_acc.empty:
            _drow = _dist_acc.iloc[0]
            _district_blurb = (
                f"  \n_Lynn district overall:_ **{_drow['CLASSIFICATION']}** "
                f"({_drow['REASON'].lower()})."
            )

        _alert(
            f"{_icon} **DESE Accountability ({_sy}): {_classif}** — {_reason}." + _district_blurb
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                "Statewide Accountability Percentile",
                f"{int(_pct)}" if pd.notna(_pct) else "—",
                help=(
                    "DESE ranks every MA school 1-99 on a composite of MCAS achievement, "
                    "growth, English-learner progress, chronic absenteeism, dropout, and "
                    "graduation. Higher is better. LEHS at 1 means it scores at or near "
                    "the bottom of the statewide distribution on the composite — though "
                    "the underlying inputs each tell different stories (see Academic "
                    "Performance, Discipline & Climate, and Success After HS)."
                ),
            )
        with c2:
            st.metric(
                "Cumulative progress toward targets",
                f"{int(_progress)}%" if pd.notna(_progress) else "—",
                help=(
                    "% of LEHS's improvement-target indicators where the school has met "
                    "or exceeded its annual target."
                ),
            )
        with c3:
            st.markdown(
                "<small>Source: DESE statereport accountability report. "
                "Classifications: *Schools of Recognition* &gt; *Not requiring "
                "assistance* &gt; *Requiring assistance or intervention* &gt; *Underperforming* "
                "&gt; *Chronically Underperforming*.</small>",
                unsafe_allow_html=True,
            )

# ---------------------------------------------------------------------------
# Cross-link out to the narrative history page. The Profile is "just the
# data"; the story lives next door.
# ---------------------------------------------------------------------------

st.divider()
_h_l, _h_r = st.columns([3, 1], gap="medium")
with _h_l:
    st.markdown("#### 📜 Want the story behind the numbers?")
    st.caption(
        "The architecture, the 1924 fire, the 1931 Goodridge Street campus, "
        "and the alumni who put LEHS on a map (from MLB All-Stars to a "
        "drummer of Boston) live on a dedicated history page."
    )
with _h_r:
    st.write("")
    st.page_link(
        "pages/15_LEHS_History.py",
        label="Open LEHS History →",
        use_container_width=True,
    )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Enrollment & demographics': enrollment,
        'Attendance & chronic absenteeism': attendance,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

