"""Section 1 — School Profile: demographics, enrollment trends, headline metrics."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE, year_axis
from utils.constants import (
    GENDER_PALETTE,
    IMAGES_DIR,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    MOBILITY_PALETTE,
    PROCESSED_DIR,
    STATE_COLOR,
)
from utils.data_loader import load_dataset
from utils.interpret import (
    chronic_absenteeism_methodology_note,
    sy_label,
    yoy_delta,
)

st.set_page_config(page_title="School Profile | LEHS", page_icon="📊", layout="wide")
sidebar_attribution()

# Load enrollment up front so the At-a-Glance stats can sit in the header beside
# the photo — filling what was otherwise empty space under the title.
enrollment = load_dataset("enrollment_demographics")
lehs = (
    enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()
    if not enrollment.empty else pd.DataFrame()
)
district = (
    enrollment[
        (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE) & (enrollment["ORG_TYPE"] == "District")
    ].sort_values("SY").copy()
    if not enrollment.empty else pd.DataFrame()
)
current = lehs.iloc[-1] if not lehs.empty else None
prior = lehs.iloc[-2] if len(lehs) > 1 else None
oldest = lehs.iloc[0] if not lehs.empty else None
# A year that fully populates demographic columns
first_with_demos = (
    lehs.dropna(subset=["HL_PCT"]).iloc[0]
    if not lehs.empty and not lehs.dropna(subset=["HL_PCT"]).empty else oldest
)

# Header — title + intro + the At-a-Glance stats on the left, building photo on
# the right. The stats fill the space the photo used to leave blank under the
# title; the photo is a touch smaller too (addresses the "takes up too much
# space" note). Columns stack on mobile. The accountability block stays near the
# bottom (see render-block below the charts).
_hdr_l, _hdr_r = st.columns([2, 1], gap="large")
with _hdr_l:
    st.title("Lynn English High School — Profile")
    st.markdown(
        "Demographics, enrollment trends, and headline metrics for LEHS, going "
        "back to the 1992–93 school year."
    )
    if current is not None:
        st.subheader(f"At a Glance — School Year {sy_label(current['SY'])}")
        _m1, _m2, _m3, _m4, _m5 = st.columns(5)
        with _m1:
            st.metric(
                "Total Enrollment",
                f"{int(current['TOTAL_CNT']):,}",
                yoy_delta(current["TOTAL_CNT"], prior["TOTAL_CNT"], "students") if prior is not None else "",
            )
        with _m2:
            st.metric(
                "% English Learners",
                f"{current['EL_PCT']:.0%}",
                yoy_delta(current["EL_PCT"] * 100, prior["EL_PCT"] * 100, "pts") if prior is not None else "",
            )
        with _m3:
            st.metric(
                "% Low Income",
                f"{current['LI_PCT']:.0%}",
                yoy_delta(current["LI_PCT"] * 100, prior["LI_PCT"] * 100, "pts") if prior is not None else "",
            )
        with _m4:
            st.metric(
                "% Students w/ Disabilities",
                f"{current['SWD_PCT']:.0%}",
                yoy_delta(current["SWD_PCT"] * 100, prior["SWD_PCT"] * 100, "pts") if prior is not None else "",
            )
        with _m5:
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
with _hdr_r:
    st.image(
        str(IMAGES_DIR / "lehs-building.jpg"),
        use_container_width=True,
        caption="Main entrance, O'Callaghan Way",
    )

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()
if lehs.empty:
    st.error(f"No rows for LEHS school code {LEHS_SCHOOL_CODE}")
    st.stop()

# ---------------------------------------------------------------------------
# Headline academic outcome — Gap #6: the Profile previously showed
# zero academic stats, forcing visitors to know to click out to
# Academic Performance. One outcome tile + a link closes the loop
# without duplicating the deep-dive page.
# ---------------------------------------------------------------------------

_grad = load_dataset("graduation_rates")
_g_row = None
_g_state_row = None
if not _grad.empty:
    _g4 = _grad[
        (_grad["STU_GRP"] == "All Students")
        & (_grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    ]
    _g_lehs = _g4[
        (_g4["ORG_CODE"] == LEHS_SCHOOL_CODE) & (_g4["ORG_TYPE"] == "School")
    ].sort_values("SY")
    if not _g_lehs.empty:
        _g_row = _g_lehs.iloc[-1]
    _g_state = _g4[_g4["ORG_TYPE"] == "State"].sort_values("SY")
    if not _g_state.empty:
        _g_state_row = _g_state.iloc[-1]

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
        "Quick academic snapshot — see **[Academic Performance](/Academic_Performance?embed=true)** "
        "for the full subject-by-subject MCAS breakdown with confidence intervals."
    )
    ac1, ac2, ac3, ac4 = st.columns(4)
    with ac1:
        if _g_row is not None:
            st.metric(
                f"4-yr Graduation Rate (Class of {int(_g_row['SY'])})",
                f"{float(_g_row['GRAD_PCT']):.0%}",
                help=(
                    "Share of the 4-year cohort that graduated on time. This rate "
                    "swings several points year to year at LEHS — read it with the "
                    "trend on Academic Performance, not as a fixed number."
                ),
            )
    with ac2:
        if _g_row is not None and pd.notna(_g_row.get("DRPOUT_PCT")):
            st.metric(
                f"Dropout rate (Class of {int(_g_row['SY'])})",
                f"{float(_g_row['DRPOUT_PCT']):.0%}",
                help="Share of the same 4-year cohort recorded as dropping out — the flip side of the graduation rate.",
            )
    with ac3:
        if _m_ela_row is not None:
            st.metric(
                f"MCAS Gr10 ELA — % M+E (SY {sy_label(int(_m_ela_row['SY']))})",
                f"{float(_m_ela_row['M_PLUS_E_PCT']):.0%}",
                help="% of Grade 10 LEHS students Meeting + Exceeding expectations on ELA.",
            )
    with ac4:
        if _m_math_row is not None:
            st.metric(
                f"MCAS Gr10 Math — % M+E (SY {sy_label(int(_m_math_row['SY']))})",
                f"{float(_m_math_row['M_PLUS_E_PCT']):.0%}",
                help="% of Grade 10 LEHS students Meeting + Exceeding expectations on Math.",
            )
    if _g_state_row is not None and _g_row is not None:
        st.caption(
            f"For context, the statewide 4-year graduation rate was "
            f"**{float(_g_state_row['GRAD_PCT']):.0%}** for the Class of "
            f"{int(_g_state_row['SY'])}. LEHS's rate moves several points from "
            f"year to year, so a single year over- or under-states the trend."
        )

# What graduates do next — one-line teaser that hands off to College & Career
# (the page's top question for families, kept to a single sentence here).
_plans = load_dataset("plans_of_graduates")
_pl_row = None
if not _plans.empty:
    _pl = _plans[_plans["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY")
    if not _pl.empty:
        _pl_row = _pl.iloc[-1]
if _pl_row is not None:
    _coll = sum(
        float(_pl_row[c])
        for c in ("COLL_4YRPUB_PCT", "COLL_4YRPRV_PCT", "COLL_2YRPUB_PCT", "COLL_2YRPRV_PCT")
        if c in _pl_row and pd.notna(_pl_row[c])
    )
    _work = float(_pl_row["WORK_PCT"]) if pd.notna(_pl_row.get("WORK_PCT")) else 0.0
    st.caption(
        f"**After graduation (Class of {int(_pl_row['SY'])}):** about "
        f"**{_coll:.0%}** of graduates planned to enroll in college and "
        f"**{_work:.0%}** planned to go straight to work — see "
        "**[College & Career](/College_and_Career?embed=true)** for the full breakdown."
    )

# ---------------------------------------------------------------------------
# Long-term transformation
# ---------------------------------------------------------------------------

st.divider()
st.subheader("How LEHS has changed since 1992")
st.caption(
    "The school today is not the school 30 years ago. These long-term deltas "
    "show how dramatically the student population has shifted in one generation. "
    "*First Language Not English (FLNE)* counts students whose home language "
    "isn't English — whether or not they currently need language support — so "
    "it's broader than *English Learner*."
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
        st.metric("% Hispanic/Latino", res[0], res[1], delta_color="off")
with c2:
    res = long_term_metric("FLNE_PCT", "% First Lang Not English")
    if res:
        st.metric("% First Lang Not English", res[0], res[1], delta_color="off")
with c3:
    res = long_term_metric("LI_PCT", "% Low Income")
    if res:
        st.metric("% Low Income", res[0], res[1], delta_color="off")
with c4:
    res = long_term_metric("WH_PCT", "% White")
    if res:
        st.metric("% White", res[0], res[1], delta_color="off")

# ---------------------------------------------------------------------------
# (History section was moved out to its own page — pages/15_LEHS_History.py.
# The Profile page is now data-only; the bottom-of-page footer links into
# the dedicated history page for the narrative side.)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Total enrollment trend
# ---------------------------------------------------------------------------

st.divider()
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
fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
st.plotly_chart(year_axis(fig), use_container_width=True)

peak_year = lehs.loc[lehs["TOTAL_CNT"].idxmax()]
trough_year = lehs.loc[lehs["TOTAL_CNT"].idxmin()]
st.caption(
    f"Enrollment peaked at **{int(peak_year['TOTAL_CNT']):,}** students in "
    f"SY {sy_label(peak_year['SY'])} and reached its lowest at "
    f"**{int(trough_year['TOTAL_CNT']):,}** in SY {sy_label(trough_year['SY'])}. "
    "The long-run growth tracks the demographic shift shown above — the "
    "student body expanded as Lynn's Hispanic/Latino and first-language-not-"
    "English populations grew."
)

# ---------------------------------------------------------------------------
# Grade-level enrollment — sits with the enrollment trend as the "size &
# structure" view, ahead of the demographic breakdowns below.
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Grade-Level Enrollment")
st.caption(
    "How the four grades stack up — and how that structure has shifted over the "
    "last three years. A larger 9th grade than 12th is the usual funnel; the "
    "thing to watch is whether the gap is widening or the incoming cohorts are "
    "shrinking."
)

# Last 3 years of grade counts, grouped — the temporal view turns a flat
# four-bar snapshot into the pipeline-shift story the caption below tells.
_grade_years = lehs.tail(3)
_g_long = _grade_years.melt(
    id_vars=["SY"],
    value_vars=["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"],
    var_name="Grade", value_name="Students",
)
_g_long["Grade"] = _g_long["Grade"].map(
    {"G9_CNT": "9", "G10_CNT": "10", "G11_CNT": "11", "G12_CNT": "12"}
)
_g_long["School year"] = _g_long["SY"].apply(lambda s: sy_label(int(s)))
_g_long = _g_long.dropna(subset=["Students"])

# Oldest→newest goes light grey → navy so the current year reads as the anchor.
_yr_labels = [sy_label(int(s)) for s in _grade_years["SY"]]
_yr_shades = ["#CBD5E1", "#94A8C7", LEHS_NAVY][-len(_yr_labels):]
_yr_cmap = dict(zip(_yr_labels, _yr_shades))

fig = px.bar(
    _g_long, x="Grade", y="Students", color="School year", barmode="group",
    color_discrete_map=_yr_cmap, text="Students",
    category_orders={"Grade": ["9", "10", "11", "12"], "School year": _yr_labels},
)
fig.update_traces(texttemplate="%{y:,.0f}", textposition="outside", cliponaxis=False)
fig.update_layout(
    **DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="Grade",
    yaxis_range=[0, _g_long["Students"].max() * 1.15],
)
st.plotly_chart(fig, use_container_width=True)

# Pull-out: 9-12 attrition narrative
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
# Attrition by student group — the grade funnel above is a single year's
# snapshot. This is the cohort dropout rate broken out by group, with the
# school-wide rate as the "what's normal" reference. Surfaces who leaves
# without duplicating the full pipeline analysis on Success After HS.
# ---------------------------------------------------------------------------

if not _grad.empty:
    _att_grp = _grad[
        (_grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_grad["ORG_TYPE"] == "School")
        & (_grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (_grad["DRPOUT_PCT"].notna())
    ].copy()
    if not _att_grp.empty:
        _cohort_yr = int(_att_grp["SY"].max())
        _att_grp = _att_grp[_att_grp["SY"] == _cohort_yr]
        _keep_groups = [
            "Hispanic or Latino", "Black or African American", "Asian", "White",
            "Multi-Race, Not Hispanic or Latino", "English Learners", "Low Income",
            "Students with Disabilities", "High Needs",
        ]
        _att_plot = _att_grp[_att_grp["STU_GRP"].isin(_keep_groups)].copy()
        _att_plot["DRPOUT_PCT"] = pd.to_numeric(_att_plot["DRPOUT_PCT"], errors="coerce")
        _att_plot = _att_plot.dropna(subset=["DRPOUT_PCT"]).sort_values("DRPOUT_PCT")
        _all_row = _att_grp[_att_grp["STU_GRP"] == "All Students"]
        _all_drop = (
            float(pd.to_numeric(_all_row["DRPOUT_PCT"].iloc[0], errors="coerce"))
            if not _all_row.empty else None
        )
        if not _att_plot.empty:
            st.divider()
            st.subheader("Attrition by student group")
            st.caption(
                f"Annual dropout rate for the Class of {_cohort_yr} cohort, by "
                "student group. The dashed line is the school-wide rate — bars to "
                "its right lose students faster than LEHS as a whole. See "
                "**[Success After HS](/Success_After_HS?embed=true)** for the full "
                "9th-grade-to-graduation pipeline."
            )
            _short = {
                "Hispanic or Latino": "Hispanic/Latino",
                "Black or African American": "Black/African Am.",
                "Multi-Race, Not Hispanic or Latino": "Multi-Race",
                "Students with Disabilities": "Students w/ Disabilities",
                "English Learners": "English Learner",
            }
            _att_plot["Group"] = _att_plot["STU_GRP"].map(lambda g: _short.get(g, g))
            fig_a = go.Figure(go.Bar(
                x=_att_plot["DRPOUT_PCT"], y=_att_plot["Group"], orientation="h",
                text=_att_plot["DRPOUT_PCT"].apply(lambda v: f"{v:.0%}"),
                textposition="outside", marker_color=LEHS_NAVY,
            ))
            fig_a.update_traces(cliponaxis=False)
            fig_a.update_layout(
                **DEFAULT_LAYOUT, xaxis_title="Dropout rate", yaxis_title="",
                xaxis_tickformat=".0%",
                xaxis_range=[0, _att_plot["DRPOUT_PCT"].max() * 1.25],
            )
            if _all_drop is not None:
                fig_a.add_vline(
                    x=_all_drop, line_dash="dash", line_color=LEHS_GOLD,
                    annotation_text=f"All students {_all_drop:.0%}",
                    annotation_position="top",
                )
            st.plotly_chart(fig_a, use_container_width=True)

# ---------------------------------------------------------------------------
# Student-teacher ratio over time — Gap #1: the first question families
# ask. Pairs naturally with the enrollment trend above; if enrollment
# went up but staffing didn't, the ratio climbs (bad). If both moved
# together, the ratio's flat (neutral).
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Student–teacher ratio over time")
st.caption(
    "DESE's reported student-to-teacher ratio for LEHS, computed from the "
    "'All Teachers' FTE total — a lower ratio means fewer students per teacher. "
    "It counts every licensed adult (counselors, specialists, and so on), not "
    "just classroom teachers, so read it alongside average class size below "
    "rather than as a class-size figure on its own."
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
        )
        st.plotly_chart(year_axis(fig_r), use_container_width=True)
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
# Average class size — the number families actually picture. DESE's
# student-teacher ratio above counts every licensed adult (counselors,
# specialists), so it runs well below real classroom size.
# ---------------------------------------------------------------------------

_cs = load_dataset("class_size")
_cs_row = None
if not _cs.empty:
    _cs_all = _cs[
        (_cs["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (_cs["ORG_TYPE"] == "School")
        & (_cs["SUBJ"].astype(str).str.fullmatch("All", case=False))
    ].sort_values("SY")
    if not _cs_all.empty:
        _cs_row = _cs_all.iloc[-1]

if _cs_row is not None and pd.notna(_cs_row.get("AVG_CLSS_CNT")):
    _cs_l, _cs_r = st.columns([1, 3], gap="medium")
    with _cs_l:
        st.metric(
            f"Average class size (SY {sy_label(int(_cs_row['SY']))})",
            f"{float(_cs_row['AVG_CLSS_CNT']):.0f} students",
        )
        st.caption(
            "Averaged across all LEHS course sections — closer to what a student "
            "actually sits in than the staffing ratio above, which divides total "
            "enrollment by every licensed adult in the building (counselors, "
            "specialists, and so on), not just classroom teachers."
        )
    with _cs_r:
        _cs_trend = _cs_all.tail(5).copy()
        _cs_trend["AVG_CLSS_CNT"] = pd.to_numeric(_cs_trend["AVG_CLSS_CNT"], errors="coerce")
        _cs_trend["label"] = _cs_trend["AVG_CLSS_CNT"].apply(lambda x: f"{x:.0f}")
        _fig_cs = px.line(_cs_trend, x="SY", y="AVG_CLSS_CNT", markers=True, text="label")
        _fig_cs.update_traces(line=dict(color=LEHS_NAVY, width=3), textposition="top center")
        _fig_cs.update_layout(**DEFAULT_LAYOUT, yaxis_title="Avg class size",
                              xaxis_title="School Year")
        st.plotly_chart(year_axis(_fig_cs), use_container_width=True)

# ---------------------------------------------------------------------------
# LEHS vs Lynn district — same-year comparison
# ---------------------------------------------------------------------------

st.divider()
st.subheader(f"LEHS vs. Lynn district ({sy_label(current['SY'])})")
st.caption(
    "How LEHS's student body compares to the Lynn Public Schools district "
    "average (across all 22 schools, PK-12). For school-to-school "
    "comparison against other Lynn high schools, see "
    "[Lynn Schools](/Lynn_Schools?embed=true) (Compare group)."
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
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                       xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "LEHS enrolls noticeably higher shares of English Learners, low-income, "
        "and high-needs students than the district as a whole. Part of that gap "
        "is structural — the district average spans all 22 PK-12 schools while "
        "LEHS is a 9-12 high school — so read this as directional, not "
        "like-for-like. For a true peer view, see Lynn Schools."
    )

# ---------------------------------------------------------------------------
# Race/ethnicity — current snapshot + composition over time
# ---------------------------------------------------------------------------

st.divider()
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
    fig.update_layout(**DEFAULT_LAYOUT, showlegend=False, height=360)
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
                       xaxis_title="School Year", height=360)
    st.plotly_chart(year_axis(fig), use_container_width=True)

# Detailed race table — in an expander so it doesn't repeat the donut's
# latest-year shares as a third full-height block.
with st.expander("Detailed race/ethnicity counts and shares (latest year)"):
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

st.divider()
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
    color_discrete_map=GENDER_PALETTE,
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share",
                   xaxis_title="School Year")
st.plotly_chart(year_axis(fig), use_container_width=True)
if "NB_PCT" in lehs.columns and lehs["NB_PCT"].notna().any():
    st.caption(
        "A non-binary category appears in DESE reporting only in recent years "
        "and stays well under 1% of students, so its band is nearly invisible "
        "on the chart by design."
    )

# ---------------------------------------------------------------------------
# Selected populations trend
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Selected Populations Over Time")
st.caption(
    "Key student-group classifications that drive resource allocation, "
    "accountability calculations, and federal/state programmatic support. "
    "**Economically Disadvantaged (ECD)** — DESE's direct-certification measure "
    "(SNAP, TANF, foster, homeless) — is reported in this dataset through "
    "SY 2020-21; **Low Income (LI)**, the older Title-I-style flag, is the "
    "series carried forward since. They capture nearly the same population but "
    "differ by definition, so both are shown where available."
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
        "Economically Disadvantaged": SUBGROUP_PALETTE["Economically Disadvantaged"],
        "Students w/ Disabilities":   SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":                 SUBGROUP_PALETTE["High Needs"],
        "First Lang Not English":     SUBGROUP_PALETTE["First Lang Not English"],
    },
)
fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of Students",
                   xaxis_title="School Year")
st.plotly_chart(year_axis(fig), use_container_width=True)

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
# Enrollment by selected populations — counts, not just percentages
# ---------------------------------------------------------------------------

st.divider()
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
    st.divider()
    st.subheader("Where LEHS students live")
    _cm_l, _cm_r = st.columns([2, 3], gap="medium")
    with _cm_l:
        st.image(
            str(_catchment_thumb),
            use_container_width=True,
            caption="Kernel-density estimate of where LEHS students live, aggregated across Lynn.",
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
            "Source: Lynn Public Schools enrollment records, provided via a "
            "data request and aggregated to neighborhood-level density."
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
        st.divider()
        st.subheader("Student mobility")
        st.caption(
            "How much of LEHS's student body turns over during a school year. "
            "**Stability** = % enrolled the whole year. **Churn** = % who "
            "moved in or out mid-year. **Intake** = % new during the year. "
            "Solid lines are LEHS; dashed lines are the **Lynn district** average "
            "for the same year, so the school's churn reads against what's normal "
            "for its district (DESE doesn't publish a statewide mobility figure here)."
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

        _mob_label = {
            "STAB_PCT": "Stability",
            "CHURN_PCT": "Churn",
            "INTAKE_PCT": "Mid-year intake",
        }
        _mob_dist = _mob[
            (_mob["ORG_TYPE"] == "District")
            & (_mob["DIST_CODE"].astype(str).str.zfill(8) == LYNN_DISTRICT_CODE)
            & (_mob["STU_GRP"] == "All Students")
        ].sort_values("SY")

        def _mob_to_long(df, entity):
            melted = df.melt(
                id_vars=["SY"],
                value_vars=["STAB_PCT", "CHURN_PCT", "INTAKE_PCT"],
                var_name="Metric", value_name="Pct",
            )
            melted["Metric"] = melted["Metric"].map(_mob_label)
            melted["Entity"] = entity
            return melted

        _mob_long = pd.concat(
            [_mob_to_long(_mob_lehs, "Lynn English"),
             _mob_to_long(_mob_dist, "Lynn district")],
            ignore_index=True,
        ).dropna(subset=["Pct"])

        fig_m = px.line(
            _mob_long, x="SY", y="Pct", color="Metric", line_dash="Entity",
            markers=True, color_discrete_map=MOBILITY_PALETTE,
            line_dash_map={"Lynn English": "solid", "Lynn district": "dash"},
            category_orders={"Metric": ["Stability", "Churn", "Mid-year intake"]},
        )
        fig_m.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="Share of students",
            xaxis_title="School Year",
        )
        st.plotly_chart(year_axis(fig_m), use_container_width=True)

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

        if pd.notna(latest_att["PCT_CHRON_ABS_10"]):
            st.caption(
                f"About **{latest_att['PCT_CHRON_ABS_10']:.0%}** of LEHS students miss "
                "10% or more of the school year — roughly four-plus weeks of class. "
                "It's the single biggest driver of the state accountability rating "
                "shown near the bottom of this page."
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
                color_discrete_map={"LEHS": LEHS_GOLD, "Lynn District": LEHS_NAVY, "Massachusetts": STATE_COLOR},
            )
            fig.update_traces(textposition="top center", textfont=dict(size=10))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".0%",
                yaxis_title="% chronically absent (≥10% of days)",
                xaxis_title="School Year",
            )
            st.plotly_chart(year_axis(fig), use_container_width=True)
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
    "How the state (DESE) officially rates LEHS's overall progress. It boils a "
    "dozen different measures — test scores, student growth, attendance, "
    "graduation, English-learner progress, and more — down to a single label and "
    "a single 1–99 rank. Useful as a headline, but it flattens a lot; the "
    "sections above tell the fuller, measure-by-measure story."
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

        st.caption(
            "**Reading this fairly:** a low rank doesn't mean classrooms are "
            "failing. The state's formula leans heavily on chronic absenteeism and "
            "graduation — both shaped by poverty, student mobility, and being a "
            "large school serving many English learners — so the overall score can "
            "sit low even where individual measures (like year-over-year student "
            "growth) look stronger. Treat it as a prompt for questions, not a "
            "final verdict on the school."
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
            if pd.notna(_pct):
                st.caption(
                    f"≈ bottom {int(_pct)}% of MA schools on the state's composite — "
                    "driven heavily by chronic absenteeism and graduation, not by any "
                    "single classroom measure."
                )
        with c2:
            st.metric(
                "Progress toward state goals",
                f"{int(_progress)}%" if pd.notna(_progress) else "—",
                help=(
                    "Each year the state sets improvement targets for LEHS across "
                    "several measures. This is the share of those targets the "
                    "school has met or beaten — higher is better."
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
    st.subheader("📜 Want the story behind the numbers?")
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
        'Graduation rates': _grad,
        'MCAS achievement': _mcas,
        'Teacher & staffing': _td,
        'Average class size': _cs,
        'Student mobility': _mob,
        'Attendance & chronic absenteeism': attendance,
        'Accountability': _acc,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

