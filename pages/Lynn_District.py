"""
Lynn — District page.

Three tabs covering Lynn Public Schools (LPS) as a whole:
  - Snapshot           — district-level enrollment, MCAS, grad, attendance, finance,
                         middle-school feeders, special education, Gateway comparison.
  - All Schools        — filter + sort every school in the district.
  - LEHS vs Siblings   — the closest peer comparison: Lynn English vs. Classical,
                         Tech, Frederick Douglass, Harold Durgin.

Merged in reorg Phase 2 from former pages 15_Lynn_District_Dashboard.py,
14_All_Lynn_Schools.py, 10_Lynn_District_and_Siblings.py. All content
preserved as-is; only the page-host changed (3 sidebar items → 3 tabs).
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    SUBGROUP_PALETTE,
    data_downloads_panel,
)
from utils.constants import (
    GATEWAY_CITIES,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    LYNN_SIBLING_HS,
)
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="Lynn District | LEHS", page_icon="🏛️", layout="wide"
)
sidebar_attribution()

st.title("Lynn Public Schools — District")
st.markdown(
    "A district-wide view of Lynn Public Schools (LPS) — the system that "
    "includes LEHS, Classical, Tech, and all elementary and middle schools. "
    "**Snapshot** shows district-level trends. **All Schools** lets you filter "
    "every school in the district. **LEHS vs Siblings** is the closest peer "
    "comparison — same district, same policies, same student pool."
)

# ---------------------------------------------------------------------------
# Shared data loads (used across tabs)
# ---------------------------------------------------------------------------

enrollment = load_dataset("enrollment_demographics")
grad = load_dataset("graduation_rates")
mcas = load_dataset("mcas_achievement")
attendance = load_dataset("student_attendance")
dist_exp = load_dataset("district_expenditures")
sped = load_dataset("special_ed_indicators")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Module-level helpers used by tabs
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _gateway_codes() -> set[str]:
    """Return DIST_CODE set for the 26 Gateway-city districts."""
    if enrollment.empty:
        return {LYNN_DISTRICT_CODE}
    by_name = enrollment[
        enrollment["DIST_NAME"].isin(
            [f"{c} Public Schools" for c in GATEWAY_CITIES] + GATEWAY_CITIES
        )
        & (enrollment["ORG_TYPE"] == "District")
    ]
    return set(by_name["DIST_CODE"].dropna().unique())


def _small_multiple(df: pd.DataFrame, value_col: str, title: str, ytick: str = ".0%"):
    """Three-line chart: Lynn, Gateway median, State median."""
    if df.empty:
        return None
    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[value_col, "SY"])
    if df.empty:
        return None

    gw_codes = _gateway_codes()
    lynn_line = df[df["DIST_CODE"] == LYNN_DISTRICT_CODE].groupby("SY")[value_col].mean().reset_index()
    gw_line = df[df["DIST_CODE"].isin(gw_codes)].groupby("SY")[value_col].median().reset_index()
    state_line = df.groupby("SY")[value_col].median().reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=state_line["SY"], y=state_line[value_col],
                              mode="lines", name="State median",
                              line=dict(color="#9E9E9E", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=gw_line["SY"], y=gw_line[value_col],
                              mode="lines+markers", name="Gateway median",
                              line=dict(color=LEHS_GOLD, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=lynn_line["SY"], y=lynn_line[value_col],
                              mode="lines+markers", name="Lynn district",
                              line=dict(color=LEHS_NAVY, width=3)))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=ytick,
                      title=title, yaxis_title="", xaxis_title="SY")
    return fig


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_snapshot, tab_all_schools, tab_siblings = st.tabs([
    "Snapshot",
    "All Schools",
    "LEHS vs Siblings",
])

# ===========================================================================
# TAB 1 — SNAPSHOT (former 15_Lynn_District_Dashboard.py)
# ===========================================================================

with tab_snapshot:
    district = enrollment[
        (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (enrollment["ORG_TYPE"] == "District")
    ].sort_values("SY")

    if district.empty:
        st.caption("Lynn district-level enrollment rows aren't loaded yet.")
    else:
        current = district.iloc[-1]

        # -------------------------------------------------------------------
        # Headline
        # -------------------------------------------------------------------
        st.header(f"Lynn Public Schools — School Year {sy_label(current['SY'])}")
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("Total Enrollment", f"{int(current['TOTAL_CNT']):,}")
        with c2:
            st.metric("% English Learners", f"{current['EL_PCT']:.0%}")
        with c3:
            st.metric("% Low Income", f"{current['LI_PCT']:.0%}")
        with c4:
            st.metric("% High Needs", f"{current['HN_PCT']:.0%}")
        with c5:
            st.metric("% Hispanic/Latino", f"{current['HL_PCT']:.0%}")

        # -------------------------------------------------------------------
        # District enrollment + demographics trend
        # -------------------------------------------------------------------
        st.header("District Enrollment Over Time")
        fig = px.line(district, x="SY", y="TOTAL_CNT", markers=True)
        fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
        st.plotly_chart(fig, use_container_width=True)

        st.header("Selected Populations Trend (District-wide)")
        long = district.melt(
            id_vars="SY",
            value_vars=["EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "FLNE_PCT"],
            var_name="Group", value_name="Pct",
        )
        label_map = {
            "EL_PCT": "English Learner", "LI_PCT": "Low Income",
            "SWD_PCT": "Students w/ Disabilities", "HN_PCT": "High Needs",
            "FLNE_PCT": "First Lang Not English",
        }
        long["Group"] = long["Group"].map(label_map)
        long = long.dropna(subset=["Pct"])

        fig = px.line(
            long, x="SY", y="Pct", color="Group", markers=True,
            color_discrete_map={
                "English Learner":          SUBGROUP_PALETTE["English Learner"],
                "Low Income":               SUBGROUP_PALETTE["Low Income"],
                "Students w/ Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
                "High Needs":               SUBGROUP_PALETTE["High Needs"],
                "First Lang Not English":   "#0277BD",
            },
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share")
        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # District MCAS performance
        # -------------------------------------------------------------------
        st.header("Lynn District MCAS Performance")

        district_mcas = mcas[
            (mcas["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (mcas["ORG_TYPE"] == "District")
            & (mcas["STU_GRP"] == "All Students")
        ].copy()

        if not district_mcas.empty:
            g10 = district_mcas[district_mcas["TEST_GRADE"] == "10"].sort_values("SY")
            if not g10.empty:
                st.subheader("Grade 10 — All Students, by Subject")
                fig = px.line(
                    g10, x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
                    markers=True,
                    color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
                )
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                   yaxis_title="% Meeting + Exceeding")
                st.plotly_chart(fig, use_container_width=True)

            elem_mcas = district_mcas[
                district_mcas["TEST_GRADE"].astype(str).isin(
                    ["03", "04", "05", "06", "07", "08"]
                )
            ].copy()
            if not elem_mcas.empty:
                st.subheader("Grades 3-8 — Average % M+E (across grades)")
                avg = elem_mcas.groupby(["SY", "SUBJECT_CODE"])["M_PLUS_E_PCT"].mean().reset_index()
                fig = px.line(
                    avg, x="SY", y="M_PLUS_E_PCT", color="SUBJECT_CODE",
                    markers=True,
                    color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
                )
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                   yaxis_title="Avg % M+E across grades")
                st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # District graduation
        # -------------------------------------------------------------------
        st.header("Lynn District Graduation Rate")

        district_grad = grad[
            (grad["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (grad["ORG_TYPE"] == "District")
            & (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        ].sort_values("SY")

        if not district_grad.empty:
            fig = px.line(district_grad, x="SY", y="GRAD_PCT", markers=True)
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                               yaxis_title="4-yr Graduation Rate",
                               xaxis_title="Cohort Year")
            st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # District attendance / chronic absence
        # -------------------------------------------------------------------
        st.header("Lynn District Attendance")

        district_att = attendance[
            (attendance["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (attendance["ORG_TYPE"] == "District")
            & (attendance["STU_GRP"] == "All Students")
            & (attendance["ATTEND_PERIOD"] == "FY")
        ].sort_values("SY")

        if not district_att.empty:
            district_att["PCT_CHRON_ABS_10"] = pd.to_numeric(
                district_att["PCT_CHRON_ABS_10"], errors="coerce"
            )
            fig = px.line(district_att, x="SY", y="PCT_CHRON_ABS_10", markers=True)
            fig.update_traces(line=dict(color="#F57C00", width=3))
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                               yaxis_title="% Chronically Absent (10%+ missed)")
            st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # District finance
        # -------------------------------------------------------------------
        st.header("Lynn District Finance")

        if not dist_exp.empty:
            d = dist_exp[dist_exp["DIST_CODE"] == LYNN_DISTRICT_CODE].copy()
            d["IND_VALUE"] = pd.to_numeric(d["IND_VALUE"], errors="coerce")

            pp = d[
                (d["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False))
                & (d["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False))
            ].sort_values("SY")
            if not pp.empty:
                latest_t = pp.iloc[-1]
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.metric(f"Per-pupil expenditure (FY {int(latest_t['SY'])})",
                              f"${latest_t['IND_VALUE']:,.0f}")
                fig = px.line(pp, x="SY", y="IND_VALUE", markers=True)
                fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                                   yaxis_title="$ per pupil", xaxis_title="Fiscal Year")
                with c2:
                    st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # Lynn middle schools (LEHS feeders)
        # -------------------------------------------------------------------
        st.header("Lynn Middle Schools — Profile of LEHS's Feeders")
        st.caption(
            "The three Lynn middle schools that feed every Lynn comprehensive high "
            "school (LEHS, LCHS, Tech). Each row is the latest publicly-published "
            "DESE snapshot — enrollment, key demographic shares, and Grade 8 MCAS "
            "% Meeting+Exceeding. (Per-student outcome tracking from each feeder "
            "to LEHS specifically would require Lynn-SIS data and isn't part of "
            "the public dashboard.)"
        )

        MIDDLE_SCHOOL_CODES = [
            "01630405",  # Breed Middle School
            "01630420",  # Pickering Middle
            "01630305",  # Thurgood Marshall Mid
        ]

        ms_enroll = enrollment[enrollment["ORG_CODE"].isin(MIDDLE_SCHOOL_CODES)].copy()
        if not ms_enroll.empty:
            ms_latest_year = int(ms_enroll["SY"].max())
            ms_snap = ms_enroll[ms_enroll["SY"] == ms_latest_year].copy()
            ms_snap["TOTAL_CNT"] = pd.to_numeric(ms_snap["TOTAL_CNT"], errors="coerce")

            ms_mcas = mcas[
                (mcas["ORG_CODE"].isin(MIDDLE_SCHOOL_CODES))
                & (mcas["TEST_GRADE"].astype(str) == "08")
                & (mcas["STU_GRP"] == "All Students")
                & (mcas["SUBJECT_CODE"].isin(["ELA", "MATH"]))
            ].copy()
            ms_mcas["M_PLUS_E_PCT"] = pd.to_numeric(ms_mcas["M_PLUS_E_PCT"], errors="coerce")
            ms_mcas_latest = ms_mcas.sort_values("SY").groupby(["ORG_CODE", "SUBJECT_CODE"]).tail(1)
            ms_mcas_wide = ms_mcas_latest.pivot_table(
                index="ORG_CODE", columns="SUBJECT_CODE", values="M_PLUS_E_PCT",
            ).reset_index().rename(columns={"ELA": "G8_ELA_ME", "MATH": "G8_MATH_ME"})

            ms_table = ms_snap[[
                "ORG_CODE", "ORG_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "HN_PCT", "HL_PCT",
            ]].merge(ms_mcas_wide, on="ORG_CODE", how="left")
            ms_table = ms_table.rename(columns={
                "ORG_NAME":  "School",
                "TOTAL_CNT": "Enrollment",
                "EL_PCT":    "% ELL",
                "LI_PCT":    "% Low Income",
                "HN_PCT":    "% High Needs",
                "HL_PCT":    "% Hispanic/Latino",
                "G8_ELA_ME": "G8 ELA % M+E",
                "G8_MATH_ME":"G8 Math % M+E",
            })
            ms_table = ms_table.drop(columns=["ORG_CODE"])

            for col in ["% ELL", "% Low Income", "% High Needs", "% Hispanic/Latino",
                         "G8 ELA % M+E", "G8 Math % M+E"]:
                if col in ms_table.columns:
                    ms_table[col] = ms_table[col].apply(
                        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
                    )
            ms_table["Enrollment"] = ms_table["Enrollment"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—"
            )
            st.dataframe(ms_table, use_container_width=True, hide_index=True)
            st.caption(f"School year {ms_latest_year}. Sources: enrollment_demographics + mcas_achievement parquets.")

        # -------------------------------------------------------------------
        # Special-education program (district-level)
        # -------------------------------------------------------------------
        st.header("Special Education Program — Lynn District")
        st.caption(
            "DESE publishes a separate *Special Education Indicators* dataset that "
            "tracks the LPS SpEd program end-to-end: identification, MCAS performance "
            "for students with disabilities (SWD), and postsecondary outcomes. "
            "All figures are district-level, K-12 (or grade range as noted)."
        )

        if not sped.empty:
            sped_lynn = sped[sped["DIST_CODE"] == LYNN_DISTRICT_CODE].copy()
            sped_lynn["IND_PCT"] = pd.to_numeric(sped_lynn["IND_PCT"], errors="coerce")

            if not sped_lynn.empty:
                ctx = sped_lynn[
                    (sped_lynn["IND_CAT"] == "CONTEXT")
                    & (sped_lynn["IND_DESC"] == "Student Enrollment")
                    & (sped_lynn["GRADES"] == "K-12")
                ].sort_values("SY")
                if not ctx.empty:
                    latest_year_sped = int(ctx["SY"].max())
                    swd_row = ctx[
                        (ctx["SY"] == latest_year_sped)
                        & (ctx["STU_GRP"] == "Students with Disabilities")
                    ]
                    if not swd_row.empty:
                        swd_pct = swd_row.iloc[0]["IND_PCT"]
                        swd_cnt = swd_row.iloc[0]["IND_CNT"]
                        tot_cnt = swd_row.iloc[0]["TOT_CNT"]
                        st.metric(
                            f"% Students with Disabilities (K-12, SY {latest_year_sped})",
                            f"{swd_pct:.1f}%",
                            f"{int(swd_cnt):,} of {int(tot_cnt):,} students",
                            delta_color="off",
                        )

                mcas_sped = sped_lynn[
                    (sped_lynn["IND_CAT"] == "ASSESSMENTS (Next Gen MCAS)")
                    & (sped_lynn["IND_DESC"].str.contains("Meeting or exceeding", na=False))
                    & (sped_lynn["GRADES"] == "Grade 10")
                    & (sped_lynn["STU_GRP"].isin(["Students with Disabilities", "Students without Disabilities"]))
                ].copy()
                if not mcas_sped.empty:
                    latest_sped_mcas = int(mcas_sped["SY"].max())
                    snap = mcas_sped[mcas_sped["SY"] == latest_sped_mcas].copy()
                    snap["Subject"] = snap["IND_DESC"].str.extract(r"on (ELA|Math|Science)")[0]
                    snap = snap.dropna(subset=["Subject"])
                    if not snap.empty:
                        st.subheader(
                            f"Grade 10 MCAS — % Meeting + Exceeding, SWD vs. non-SWD "
                            f"(SY {latest_sped_mcas})"
                        )
                        fig = px.bar(
                            snap, x="Subject", y="IND_PCT", color="STU_GRP",
                            barmode="group",
                            color_discrete_map={
                                "Students with Disabilities":    "#D32F2F",
                                "Students without Disabilities": LEHS_NAVY,
                            },
                            text=snap["IND_PCT"].round(1).astype(str) + "%",
                        )
                        fig.update_traces(textposition="outside", cliponaxis=False)
                        fig.update_layout(
                            **DEFAULT_LAYOUT,
                            yaxis_title="% Meeting + Exceeding",
                            yaxis_ticksuffix="%",
                            yaxis_range=[0, max(snap["IND_PCT"].max() * 1.15, 10)],
                            xaxis_title="",
                            legend_title="",
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        st.caption(
                            "The gap between the two groups is one of DESE's most "
                            "tracked indicators for SpEd program effectiveness."
                        )

                post = sped_lynn[
                    (sped_lynn["IND_CAT"] == "POSTSECONDARY OUTCOMES")
                    & (sped_lynn["STU_GRP"] == "Students with Disabilities")
                ].copy()
                if not post.empty:
                    latest_post = int(post["SY"].max())
                    post_latest = post[post["SY"] == latest_post].sort_values("IND_PCT", ascending=True)
                    if not post_latest.empty:
                        st.subheader(
                            f"Postsecondary outcomes for Lynn SWD graduates "
                            f"(SY {latest_post})"
                        )
                        fig = px.bar(
                            post_latest, y="IND_DESC", x="IND_PCT", orientation="h",
                            color_discrete_sequence=[LEHS_NAVY],
                            text=post_latest["IND_PCT"].round(1).astype(str) + "%",
                        )
                        fig.update_traces(textposition="outside", cliponaxis=False)
                        fig.update_layout(
                            **DEFAULT_LAYOUT,
                            xaxis_title="% of SWD graduates",
                            xaxis_ticksuffix="%",
                            xaxis_range=[0, max(post_latest["IND_PCT"].max() * 1.18, 10)],
                            yaxis_title="",
                            height=max(280, 28 * len(post_latest)),
                        )
                        st.plotly_chart(fig, use_container_width=True)

        # -------------------------------------------------------------------
        # Lynn vs. Gateway median vs. State median — small multiples
        # -------------------------------------------------------------------
        st.header("Lynn vs. Gateway Cities median vs. State median")
        st.caption(
            "Each panel: Lynn (navy line) compared to the median of the 26 MA Gateway "
            "Cities (gold) and the state-wide median (grey). Latest 8 years."
        )

        col_a, col_b = st.columns(2)

        if not grad.empty:
            g4 = grad[(grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
                      & (grad["ORG_TYPE"] == "District")
                      & (grad["STU_GRP"] == "All Students")][["SY", "DIST_CODE", "GRAD_PCT"]]
            g4["GRAD_PCT"] = pd.to_numeric(g4["GRAD_PCT"], errors="coerce")
            if g4["GRAD_PCT"].max() and g4["GRAD_PCT"].max() > 1.5:
                g4["GRAD_PCT"] = g4["GRAD_PCT"] / 100.0
            fig = _small_multiple(g4, "GRAD_PCT", "4-yr graduation rate")
            if fig:
                with col_a:
                    st.plotly_chart(fig, use_container_width=True)

        if not attendance.empty:
            a = attendance[(attendance["ORG_TYPE"] == "District")
                           & (attendance["STU_GRP"] == "All Students")
                           & (attendance["ATTEND_PERIOD"] == "FY")][["SY", "DIST_CODE", "PCT_CHRON_ABS_10"]]
            fig = _small_multiple(a, "PCT_CHRON_ABS_10", "Chronic absenteeism")
            if fig:
                with col_b:
                    st.plotly_chart(fig, use_container_width=True)

        if not mcas.empty:
            m_g10 = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                         & (mcas["SUBJECT_CODE"] == "ELA")
                         & (mcas["STU_GRP"] == "All Students")
                         & (mcas["ORG_TYPE"] == "District")
                         ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
            m_g10["M_PLUS_E_PCT"] = pd.to_numeric(m_g10["M_PLUS_E_PCT"], errors="coerce")
            if m_g10["M_PLUS_E_PCT"].max() and m_g10["M_PLUS_E_PCT"].max() > 1.5:
                m_g10["M_PLUS_E_PCT"] = m_g10["M_PLUS_E_PCT"] / 100.0
            fig = _small_multiple(m_g10, "M_PLUS_E_PCT", "MCAS Grade 10 ELA — % M+E")
            if fig:
                with col_a:
                    st.plotly_chart(fig, use_container_width=True)

        if not mcas.empty:
            m_g10m = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                          & (mcas["SUBJECT_CODE"] == "MATH")
                          & (mcas["STU_GRP"] == "All Students")
                          & (mcas["ORG_TYPE"] == "District")
                          ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
            m_g10m["M_PLUS_E_PCT"] = pd.to_numeric(m_g10m["M_PLUS_E_PCT"], errors="coerce")
            if m_g10m["M_PLUS_E_PCT"].max() and m_g10m["M_PLUS_E_PCT"].max() > 1.5:
                m_g10m["M_PLUS_E_PCT"] = m_g10m["M_PLUS_E_PCT"] / 100.0
            fig = _small_multiple(m_g10m, "M_PLUS_E_PCT", "MCAS Grade 10 Math — % M+E")
            if fig:
                with col_b:
                    st.plotly_chart(fig, use_container_width=True)


# ===========================================================================
# TAB 2 — ALL SCHOOLS (former 14_All_Lynn_Schools.py)
# ===========================================================================

with tab_all_schools:
    st.markdown(
        "Filter and sort every school in Lynn Public Schools (LPS) — useful for "
        "parents choosing schools, administrators benchmarking internally, and "
        "anyone curious about the patterns inside the district."
    )

    lynn_all = enrollment[
        (enrollment["DIST_CODE"] == LYNN_DISTRICT_CODE)
        & (enrollment["ORG_TYPE"] == "School")
    ].copy()

    if lynn_all.empty:
        st.caption("Lynn district school list isn't loaded yet.")
    else:
        latest = lynn_all.sort_values("SY").groupby("ORG_CODE").tail(1)
        latest_year_all = int(latest["SY"].max())

        # -------------------------------------------------------------------
        # Filters
        # -------------------------------------------------------------------
        st.subheader(f"Filter Lynn schools (showing SY {latest_year_all} data)")

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

        filtered = latest.copy()
        if grade_filter:
            grade_masks = []
            if "PK" in grade_filter:
                grade_masks.append(filtered["PK_CNT"] > 0)
            if "K-5" in grade_filter:
                grade_masks.append(
                    (filtered[["K_CNT", "G1_CNT", "G2_CNT", "G3_CNT", "G4_CNT", "G5_CNT"]].sum(axis=1) > 0)
                )
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

        # -------------------------------------------------------------------
        # Sortable scorecard
        # -------------------------------------------------------------------
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

        def highlight_lehs(row):
            if "Lynn English" in str(row["School"]):
                return ["background-color: #FFF4D6"] * len(row)
            return [""] * len(row)

        display["Enrollment"] = display["Enrollment"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "—"
        )
        for c in display.columns:
            if c.startswith("%"):
                display[c] = display[c].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

        st.dataframe(display.sort_values("School").style.apply(highlight_lehs, axis=1),
                     use_container_width=True, hide_index=True, height=500)

        # -------------------------------------------------------------------
        # Scatter: enrollment vs % ELL
        # -------------------------------------------------------------------
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

        # -------------------------------------------------------------------
        # Performance comparison
        # -------------------------------------------------------------------
        st.subheader("Performance comparison — attendance + MCAS proficiency")
        st.caption("Latest available year for each school. Blank cells = no data published for that school × indicator.")

        perf = filtered[["ORG_CODE", "ORG_NAME"]].copy()

        if not attendance.empty:
            a = attendance.copy()
            a["PCT_CHRON_ABS_10"] = pd.to_numeric(a["PCT_CHRON_ABS_10"], errors="coerce")
            a["ATTEND_RATE"] = pd.to_numeric(a["ATTEND_RATE"], errors="coerce")
            a = a[(a["STU_GRP"] == "All Students") & (a["ATTEND_PERIOD"] == "FY")]
            a_latest = a.sort_values("SY").groupby("ORG_CODE").tail(1)[
                ["ORG_CODE", "ATTEND_RATE", "PCT_CHRON_ABS_10"]
            ]
            perf = perf.merge(a_latest, on="ORG_CODE", how="left")

        if not mcas.empty:
            m = mcas.copy()
            m["M_PLUS_E_PCT"] = pd.to_numeric(m.get("M_PLUS_E_PCT"), errors="coerce")
            g10 = m[(m["TEST_GRADE"].astype(str) == "10") & (m["STU_GRP"] == "All Students")]
            for subj, label in [("ELA", "MCAS G10 ELA M+E%"), ("MATH", "MCAS G10 Math M+E%")]:
                s = g10[g10["SUBJECT_CODE"] == subj].sort_values("SY").groupby("ORG_CODE").tail(1)
                s = s[["ORG_CODE", "M_PLUS_E_PCT"]].rename(columns={"M_PLUS_E_PCT": label})
                perf = perf.merge(s, on="ORG_CODE", how="left")
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

        # -------------------------------------------------------------------
        # District-level totals
        # -------------------------------------------------------------------
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


# ===========================================================================
# TAB 3 — LEHS vs SIBLINGS (former 10_Lynn_District_and_Siblings.py)
# ===========================================================================

with tab_siblings:
    st.markdown(
        "**The most analytically powerful peer view.** Lynn's high schools "
        "share the same district, same policies, and draw from the same student "
        "pool. Differences between them isolate school-level practices rather "
        "than city-level factors. (For the district-wide picture, see the "
        "*Snapshot* tab above.)"
    )

    SIBLING_CODES = [c for c in LYNN_SIBLING_HS.values() if c]

    # Color map: LEHS in gold, others muted
    SIBLING_COLORS = {
        "01630510": LEHS_GOLD,                                       # LEHS
        "01630505": LEHS_NAVY,                                       # Classical
        "01630605": SUBGROUP_PALETTE["Asian"],                       # Lynn Tech
        "01630575": SUBGROUP_PALETTE["Hispanic/Latino"],             # Frederick Douglass
        "01630525": SUBGROUP_PALETTE["African American/Black"],      # Harold Durgin
    }

    NAME_OVERRIDES = {
        "01630510": "Lynn English High",
        "01630505": "Lynn Classical",
        "01630605": "Lynn Tech",
        "01630575": "Frederick Douglass",
        "01630525": "Harold Durgin",
    }

    # -------------------------------------------------------------------
    # Lynn high schools — side by side
    # -------------------------------------------------------------------
    st.header("Lynn High Schools — Side by Side")
    st.markdown(
        "Comparison across Lynn's five high schools that report MCAS data: "
        "**Lynn English** (the focus), **Lynn Classical**, **Lynn Tech** "
        "(vocational), **Frederick Douglass Collegiate Academy** (alternative), "
        "and **Harold Durgin Success Academy** (alternative)."
    )

    siblings = enrollment[enrollment["ORG_CODE"].isin(SIBLING_CODES)].copy()
    siblings["School"] = siblings["ORG_CODE"].map(NAME_OVERRIDES)

    # -------------------------------------------------------------------
    # Most-recent scorecard
    # -------------------------------------------------------------------
    st.subheader("Latest Year Scorecard")

    latest_year_sib = int(siblings["SY"].max())
    latest_sib = siblings[siblings["SY"] == latest_year_sib].set_index("School")
    scorecard_cols = {
        "TOTAL_CNT": "Total Enrollment",
        "EL_PCT": "% ELL",
        "LI_PCT": "% Low Income",
        "SWD_PCT": "% SPED",
        "HN_PCT": "% High Needs",
        "HL_PCT": "% Hispanic/Latino",
        "FE_PCT": "% Female",
    }
    scorecard = latest_sib[list(scorecard_cols.keys())].rename(columns=scorecard_cols)
    for col in scorecard.columns:
        if col == "Total Enrollment":
            scorecard[col] = scorecard[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        else:
            scorecard[col] = scorecard[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")

    def highlight_lehs_sib(row):
        if row.name == "Lynn English High":
            return ["background-color: #FFF4D6"] * len(row)
        return [""] * len(row)

    st.dataframe(scorecard.style.apply(highlight_lehs_sib, axis=1), use_container_width=True)
    st.caption(f"School year {latest_year_sib}. LEHS highlighted in gold.")

    # -------------------------------------------------------------------
    # Enrollment trends
    # -------------------------------------------------------------------
    st.subheader("Enrollment Trends")

    fig = px.line(
        siblings.sort_values("SY"),
        x="SY", y="TOTAL_CNT", color="School",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
        markers=True,
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Students", xaxis_title="School Year")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Lynn English is by far the largest of the Lynn high schools, followed "
        "closely by Lynn Classical."
    )

    # -------------------------------------------------------------------
    # Demographic mix comparison
    # -------------------------------------------------------------------
    st.subheader(f"Demographic Composition ({latest_year_sib})")

    demo_cols = ["EL_PCT", "LI_PCT", "SWD_PCT", "HL_PCT", "BAA_PCT"]
    demo_labels = {
        "EL_PCT": "% ELL",
        "LI_PCT": "% Low Income",
        "SWD_PCT": "% SPED",
        "HL_PCT": "% Hispanic/Latino",
        "BAA_PCT": "% Black/African American",
    }

    demo_long = latest_sib.reset_index().melt(
        id_vars=["School"], value_vars=demo_cols, var_name="Metric", value_name="Pct"
    )
    demo_long["Metric"] = demo_long["Metric"].map(demo_labels)

    fig = px.bar(
        demo_long, x="Metric", y="Pct", color="School", barmode="group",
        color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", xaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Each Lynn HS serves a slightly different student population. Lynn Tech "
        "and the alternative HS (Frederick Douglass, Harold Durgin) often have "
        "different demographic profiles than the two main comprehensive schools."
    )

    # -------------------------------------------------------------------
    # MCAS Grade 10 comparison
    # -------------------------------------------------------------------
    st.header("MCAS Grade 10 — Lynn HS Comparison")

    mcas_lynn = mcas[
        (mcas["ORG_CODE"].isin(SIBLING_CODES))
        & (mcas["TEST_GRADE"] == "10")
        & (mcas["STU_GRP"] == "All Students")
    ].copy()
    mcas_lynn["School"] = mcas_lynn["ORG_CODE"].map(NAME_OVERRIDES)

    if mcas_lynn.empty:
        st.info("No MCAS Grade 10 'All Students' data for Lynn HS yet.")
    else:
        for subject_code, subject_label in [("ELA", "English Language Arts"), ("MATH", "Mathematics")]:
            st.subheader(f"Grade 10 {subject_label} — % Meeting or Exceeding")
            sub = mcas_lynn[mcas_lynn["SUBJECT_CODE"] == subject_code].sort_values("SY")
            if sub.empty:
                st.info(f"No data for {subject_label}")
                continue
            fig = px.line(
                sub, x="SY", y="M_PLUS_E_PCT", color="School",
                color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
                markers=True,
            )
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickformat=".0%",
                yaxis_title="% Meeting + Exceeding",
                xaxis_title="School Year",
            )
            st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # Graduation rates
    # -------------------------------------------------------------------
    st.header("4-Year Graduation Rates — Lynn HS Comparison")

    grad_lynn = grad[
        (grad["ORG_CODE"].isin(SIBLING_CODES))
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
        & (grad["STU_GRP"] == "All Students")
    ].copy()
    grad_lynn["School"] = grad_lynn["ORG_CODE"].map(NAME_OVERRIDES)

    if grad_lynn.empty:
        st.info("No graduation data yet.")
    else:
        fig = px.line(
            grad_lynn.sort_values("SY"),
            x="SY", y="GRAD_PCT", color="School",
            color_discrete_map={NAME_OVERRIDES[code]: SIBLING_COLORS[code] for code in NAME_OVERRIDES},
            markers=True,
        )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="4-Year Graduation Rate",
            xaxis_title="Cohort Year",
        )
        st.plotly_chart(fig, use_container_width=True)

        latest_grad_year = int(grad_lynn["SY"].max())
        st.subheader(f"Cohort {latest_grad_year} — Outcome Breakdown")
        latest_grad = (
            grad_lynn[grad_lynn["SY"] == latest_grad_year]
            .set_index("School")
            [["GRAD_PCT", "IN_SCH_PCT", "GED_PCT", "DRPOUT_PCT", "NON_GRAD_PCT"]]
            .rename(columns={
                "GRAD_PCT": "Graduated",
                "IN_SCH_PCT": "Still In School",
                "GED_PCT": "GED",
                "DRPOUT_PCT": "Dropped Out",
                "NON_GRAD_PCT": "Non-Grad Completer",
            })
        )
        fig = px.bar(
            latest_grad.reset_index().melt(id_vars="School", var_name="Outcome", value_name="Pct"),
            x="School", y="Pct", color="Outcome", barmode="stack",
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------
    # Key analytical question
    # -------------------------------------------------------------------
    st.subheader("Key Analytical Question")
    st.markdown(
        """
**When student populations are similar (or after controlling for them), what's
different about the schools' outcomes?**

The Lynn HS sibling comparison isolates school-level practices from city-level
demographic factors. Use the ELL Pipeline page to drill into how each Lynn HS
serves English Learners specifically — Lynn Tech, the alternative academies, and
the two comprehensive HS may all show different patterns despite operating
under the same district leadership.
"""
    )


# ===========================================================================
# Shared data downloads (one consolidated panel for the whole page)
#
# Lives outside the `with tab_*` blocks so it appears below the tab bar and
# avoids the StreamlitDuplicateElementKey bug that would fire if two tabs
# each rendered their own panel with overlapping dataset labels.
# ===========================================================================

data_downloads_panel({
    "Enrollment & demographics": enrollment,
    "Graduation rates": grad,
    "MCAS achievement": mcas,
    "Student attendance": attendance,
    "District expenditures": dist_exp,
    "Special education indicators": sped,
})
