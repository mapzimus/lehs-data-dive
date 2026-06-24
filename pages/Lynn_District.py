"""
Lynn — District page.

Two tabs covering Lynn Public Schools (LPS) as a whole:
  - Snapshot     — district-level enrollment, MCAS, grad, attendance, finance,
                   middle-school feeders, special education, Gateway comparison.
  - All Schools  — filter + sort every school in the district.

The LEHS-vs-Siblings comparison (LEHS vs Classical / Tech / Frederick Douglass
/ Harold Durgin) was lifted out of this page into pages/Lynn_Schools.py under
the Compare group, so all peer-comparison views live in one section of the
sidebar.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    SUBGROUP_PALETTE,
    data_downloads_panel,
    year_axis,
)
from utils.constants import (
    GATEWAY_CITIES,
    IMAGES_DIR,
    LYNN_DISTRICT_CODE,
    SUBJECT_PALETTE,
)
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(
    page_title="Lynn District | LEHS", page_icon="🏛️", layout="wide"
)
sidebar_attribution()

_hdr_l, _hdr_r = st.columns([1, 6])
with _hdr_l:
    st.image(str(IMAGES_DIR / "lps-logo.png"), width=110)
with _hdr_r:
    st.title("Lynn Public Schools — District")
    st.markdown(
        "A district-wide view of Lynn Public Schools (LPS) — the system that "
        "includes LEHS, Classical, Tech, and all elementary and middle schools. "
        "**Snapshot** shows district-level trends. **All Schools** lets you "
        "filter every school in the district. For school-to-school comparison "
        "(LEHS vs. Classical, Tech, Frederick Douglass, Harold Durgin) see "
        "[Lynn Schools](/Lynn_Schools?embed=true) under the Compare group."
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
# Accountability classifications — one row per school (all 26 Lynn schools),
# used by the All Schools scorecard + the downloads panel below.
acct = load_dataset("accountability_summary")

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


def _state_line(
    state_df: pd.DataFrame,
    value_col: str,
    *,
    extra_filters: dict | None = None,
    period_col: str | None = None,
    period: str | None = None,
) -> pd.DataFrame | None:
    """Pull DESE's *real* statewide row (ORG_TYPE == 'State') for one metric.

    Returns a per-SY frame, or None when the dataset ships no usable State row
    (e.g. graduation_rates has no State rows at all). This is what lets the
    small multiples show a *true* statewide line instead of mislabelling a
    median of districts as the "state".
    """
    if state_df is None or state_df.empty or "ORG_TYPE" not in state_df.columns:
        return None
    s = state_df[state_df["ORG_TYPE"] == "State"].copy()
    if period_col and period is not None and period_col in s.columns:
        s = s[s[period_col] == period]
    for col, val in (extra_filters or {}).items():
        if col in s.columns:
            s = s[s[col].astype(str) == str(val)]
    if s.empty or value_col not in s.columns:
        return None
    s[value_col] = pd.to_numeric(s[value_col], errors="coerce")
    if s[value_col].max() and s[value_col].max() > 1.5:
        s[value_col] = s[value_col] / 100.0
    s = s.dropna(subset=[value_col, "SY"])
    if s.empty:
        return None
    return s.groupby("SY")[value_col].mean().reset_index()


def _small_multiple(
    df: pd.DataFrame,
    value_col: str,
    title: str,
    ytick: str = ".0%",
    *,
    state_df: pd.DataFrame | None = None,
    state_filters: dict | None = None,
    state_period_col: str | None = "ATTEND_PERIOD",
    state_period: str | None = None,
):
    """Lynn vs. Gateway-districts median (+ a true statewide line where DESE
    publishes one).

    `df` is expected to already be district-level rows. The Gateway line is the
    median across the Gateway *districts* only (explicitly re-filtered here so
    the label is honest even if a caller forgets to pre-filter). The grey line
    is DESE's real ORG_TYPE=='State' value, sourced from `state_df`; when the
    dataset has no State row (e.g. graduation_rates) the line is simply omitted
    rather than faking it from a district median.
    """
    if df.empty:
        return None
    df = df.copy()
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")
    df = df.dropna(subset=[value_col, "SY"])
    if df.empty:
        return None

    gw_codes = _gateway_codes()
    if "ORG_TYPE" in df.columns:
        df_dist = df[df["ORG_TYPE"] == "District"]
    else:
        df_dist = df
    lynn_line = df_dist[df_dist["DIST_CODE"] == LYNN_DISTRICT_CODE].groupby("SY")[value_col].mean().reset_index()
    gw_line = df_dist[df_dist["DIST_CODE"].isin(gw_codes)].groupby("SY")[value_col].median().reset_index()
    state_line = _state_line(
        state_df, value_col,
        extra_filters=state_filters,
        period_col=state_period_col, period=state_period,
    )

    fig = go.Figure()
    if state_line is not None and not state_line.empty:
        fig.add_trace(go.Scatter(x=state_line["SY"], y=state_line[value_col],
                                  mode="lines", name="Massachusetts (statewide)",
                                  line=dict(color="#9E9E9E", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=gw_line["SY"], y=gw_line[value_col],
                              mode="lines+markers", name="Gateway districts (median)",
                              line=dict(color=LEHS_GOLD, width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=lynn_line["SY"], y=lynn_line[value_col],
                              mode="lines+markers", name="Lynn district",
                              line=dict(color=LEHS_NAVY, width=3)))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=ytick,
                      title=title, yaxis_title="", xaxis_title="SY")
    year_axis(fig)
    return fig


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_snapshot, tab_all_schools = st.tabs([
    "Snapshot",
    "All Schools",
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
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

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
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

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
                    color_discrete_map=SUBJECT_PALETTE,
                )
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                   yaxis_title="% Meeting + Exceeding")
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")

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
                    color_discrete_map=SUBJECT_PALETTE,
                )
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                   yaxis_title="Avg % M+E across grades")
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")

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
            year_axis(fig)
            st.plotly_chart(fig, width="stretch")

        # -------------------------------------------------------------------
        # District attendance / chronic absence
        # -------------------------------------------------------------------
        st.header("Lynn District Attendance")

        district_att = attendance[
            (attendance["DIST_CODE"] == LYNN_DISTRICT_CODE)
            & (attendance["ORG_TYPE"] == "District")
            & (attendance["STU_GRP"] == "All Students")
            & (attendance["ATTEND_PERIOD"] == "End of Year")
        ].sort_values("SY")

        if not district_att.empty:
            district_att["PCT_CHRON_ABS_10"] = pd.to_numeric(
                district_att["PCT_CHRON_ABS_10"], errors="coerce"
            )
            fig = px.line(district_att, x="SY", y="PCT_CHRON_ABS_10", markers=True)
            fig.update_traces(line=dict(color=LEHS_GOLD, width=3))
            fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                               yaxis_title="% Chronically Absent (10%+ missed)")
            year_axis(fig)
            st.plotly_chart(fig, width="stretch")

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
                year_axis(fig)
                with c2:
                    st.plotly_chart(fig, width="stretch")

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
                "EL_PCT":    "% English Learner(s)",
                "LI_PCT":    "% Low Income",
                "HN_PCT":    "% High Needs",
                "HL_PCT":    "% Hispanic/Latino",
                "G8_ELA_ME": "G8 ELA % M+E",
                "G8_MATH_ME":"G8 Math % M+E",
            })
            ms_table = ms_table.drop(columns=["ORG_CODE"])

            for col in ["% English Learner(s)", "% Low Income", "% High Needs", "% Hispanic/Latino",
                         "G8 ELA % M+E", "G8 Math % M+E"]:
                if col in ms_table.columns:
                    ms_table[col] = ms_table[col].apply(
                        lambda x: f"{x:.0%}" if pd.notna(x) else "—"
                    )
            ms_table["Enrollment"] = ms_table["Enrollment"].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) else "—"
            )
            st.dataframe(ms_table, width="stretch", hide_index=True)
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
                                "Students with Disabilities":    "#C2A99E",
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
                        st.plotly_chart(fig, width="stretch")
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
                        st.plotly_chart(fig, width="stretch")

        # -------------------------------------------------------------------
        # Lynn vs. Gateway median vs. State median — small multiples
        # -------------------------------------------------------------------
        st.header("Lynn vs. Gateway districts vs. Massachusetts")
        st.caption(
            "Each panel: Lynn (navy) compared to the median of the 26 MA Gateway "
            "City districts (gold). The grey dotted line is the *real* statewide "
            "figure DESE publishes, shown where available (graduation has no "
            "published statewide cohort row in this dataset, so that panel shows "
            "Lynn vs. Gateway only)."
        )

        col_a, col_b = st.columns(2)

        if not grad.empty:
            g4 = grad[(grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
                      & (grad["ORG_TYPE"] == "District")
                      & (grad["STU_GRP"] == "All Students")][["SY", "DIST_CODE", "GRAD_PCT"]]
            g4["GRAD_PCT"] = pd.to_numeric(g4["GRAD_PCT"], errors="coerce")
            if g4["GRAD_PCT"].max() and g4["GRAD_PCT"].max() > 1.5:
                g4["GRAD_PCT"] = g4["GRAD_PCT"] / 100.0
            fig = _small_multiple(
                g4, "GRAD_PCT", "4-yr graduation rate",
                state_df=grad, state_period_col=None,
                state_filters={
                    "GRAD_RATE_TYPE": "4-Year Adjusted Cohort Graduation Rate",
                    "STU_GRP": "All Students",
                },
            )
            if fig:
                with col_a:
                    st.plotly_chart(fig, width="stretch")

        if not attendance.empty:
            a = attendance[(attendance["ORG_TYPE"] == "District")
                           & (attendance["STU_GRP"] == "All Students")
                           & (attendance["ATTEND_PERIOD"] == "End of Year")][["SY", "DIST_CODE", "PCT_CHRON_ABS_10"]]
            fig = _small_multiple(a, "PCT_CHRON_ABS_10", "Chronic absenteeism",
                                  state_df=attendance, state_period="End of Year")
            if fig:
                with col_b:
                    st.plotly_chart(fig, width="stretch")

        if not mcas.empty:
            m_g10 = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                         & (mcas["SUBJECT_CODE"] == "ELA")
                         & (mcas["STU_GRP"] == "All Students")
                         & (mcas["ORG_TYPE"] == "District")
                         ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
            m_g10["M_PLUS_E_PCT"] = pd.to_numeric(m_g10["M_PLUS_E_PCT"], errors="coerce")
            if m_g10["M_PLUS_E_PCT"].max() and m_g10["M_PLUS_E_PCT"].max() > 1.5:
                m_g10["M_PLUS_E_PCT"] = m_g10["M_PLUS_E_PCT"] / 100.0
            fig = _small_multiple(
                m_g10, "M_PLUS_E_PCT", "MCAS Grade 10 ELA — % M+E",
                state_df=mcas, state_period_col=None,
                state_filters={"TEST_GRADE": "10", "SUBJECT_CODE": "ELA",
                               "STU_GRP": "All Students"},
            )
            if fig:
                with col_a:
                    st.plotly_chart(fig, width="stretch")

        if not mcas.empty:
            m_g10m = mcas[(mcas["TEST_GRADE"].astype(str) == "10")
                          & (mcas["SUBJECT_CODE"] == "MATH")
                          & (mcas["STU_GRP"] == "All Students")
                          & (mcas["ORG_TYPE"] == "District")
                          ][["SY", "DIST_CODE", "M_PLUS_E_PCT"]]
            m_g10m["M_PLUS_E_PCT"] = pd.to_numeric(m_g10m["M_PLUS_E_PCT"], errors="coerce")
            if m_g10m["M_PLUS_E_PCT"].max() and m_g10m["M_PLUS_E_PCT"].max() > 1.5:
                m_g10m["M_PLUS_E_PCT"] = m_g10m["M_PLUS_E_PCT"] / 100.0
            fig = _small_multiple(
                m_g10m, "M_PLUS_E_PCT", "MCAS Grade 10 Math — % M+E",
                state_df=mcas, state_period_col=None,
                state_filters={"TEST_GRADE": "10", "SUBJECT_CODE": "MATH",
                               "STU_GRP": "All Students"},
            )
            if fig:
                with col_b:
                    st.plotly_chart(fig, width="stretch")


    st.divider()

    # -------------------------------------------------------------------
    # Where Lynn students enroll (vxt3-k35x) — resident outflow by reason
    # -------------------------------------------------------------------
    st.header("Where Lynn Students Enroll")
    st.caption(
        "Of all students who live in Lynn, where do they actually enroll? Most "
        "stay in Lynn Public Schools; the rest leave for charter schools or "
        "inter-district school choice. Source: DESE 'Where Residents Go' (vxt3-k35x)."
    )
    choice = load_dataset("school_choice")
    if not choice.empty:
        lynn_choice = choice[choice["TOWN_NAME"] == "Lynn"].copy()
        if not lynn_choice.empty:
            latest_cy = int(lynn_choice["SY"].max())
            cur_c = lynn_choice[lynn_choice["SY"] == latest_cy]

            def _share(reason):
                r = cur_c[cur_c["ENR_REASON"] == reason]["PCT_OF_RESIDENTS"]
                return float(r.iloc[0]) if not r.empty else 0.0

            c1, c2, c3 = st.columns(3)
            c1.metric(f"Stay in Lynn (SY {latest_cy})", f"{_share('Resident/Member'):.1%}")
            c2.metric("Leave for a charter", f"{_share('Charter School'):.1%}")
            c3.metric("Inter-district choice", f"{_share('School Choice Program'):.1%}")

            out = lynn_choice[lynn_choice["ENR_REASON"].isin(
                ["Charter School", "School Choice Program"])].sort_values("SY")
            if not out.empty:
                fig = px.line(out, x="SY", y="PCT_OF_RESIDENTS", color="ENR_REASON",
                              markers=True)
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".1%",
                                  yaxis_title="% of Lynn residents", xaxis_title="School Year",
                                  legend_title="Leaving via")
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")

                # Plain-language callout: charter outflow has roughly doubled.
                charter_ts = out[out["ENR_REASON"] == "Charter School"].copy()
                charter_ts["PCT_OF_RESIDENTS"] = pd.to_numeric(
                    charter_ts["PCT_OF_RESIDENTS"], errors="coerce"
                )
                charter_ts = charter_ts.dropna(subset=["PCT_OF_RESIDENTS"]).sort_values("SY")
                if len(charter_ts) > 1:
                    _c0, _c1 = charter_ts.iloc[0], charter_ts.iloc[-1]
                    _yrs = int(_c1["SY"] - _c0["SY"])
                    st.markdown(
                        f"**Charter outflow has roughly doubled.** The share of "
                        f"Lynn residents enrolling in charter schools rose from "
                        f"**{_c0['PCT_OF_RESIDENTS']:.1%}** in SY{int(_c0['SY'])} to "
                        f"**{_c1['PCT_OF_RESIDENTS']:.1%}** in SY{int(_c1['SY'])} — "
                        f"about double over {_yrs} years — while inter-district "
                        f"school choice stayed comparatively flat."
                    )

    st.divider()

    # -------------------------------------------------------------------
    # Early education access (rg9w-dkpg) — Pre-K and full-day kindergarten
    # -------------------------------------------------------------------
    st.header("Early Education — Pre-K & Kindergarten")
    st.caption(
        "Access to early education in Lynn: total Pre-K enrollment, kindergarten "
        "headcount, and the share of kindergartners in full-day seats. "
        "Source: DESE Pre-K & Kindergarten Enrollment (rg9w-dkpg)."
    )
    early = load_dataset("early_education")
    if not early.empty:
        lynn_early = early[(early["DIST_CODE"] == LYNN_DISTRICT_CODE)
                           & (early["ORG_TYPE"] == "District")
                           & (early["STU_GRP"] == "All Students")].sort_values("SY")
        if not lynn_early.empty:
            cur_e = lynn_early.iloc[-1]
            fk = cur_e["KGR_SUBGROUP_FUL_PCT"]
            fk = fk / 100.0 if pd.notna(fk) and fk > 1.5 else fk
            c1, c2, c3 = st.columns(3)
            c1.metric(f"Pre-K enrolled (SY {int(cur_e['SY'])})",
                      f"{int(cur_e['PKG_PKENR_TOT']):,}" if pd.notna(cur_e["PKG_PKENR_TOT"]) else "—")
            c2.metric("Kindergartners",
                      f"{int(cur_e['KGR_SUBGROUP_CNT']):,}" if pd.notna(cur_e["KGR_SUBGROUP_CNT"]) else "—")
            c3.metric("% in full-day K", f"{fk:.0%}" if pd.notna(fk) else "—")

            fdk = lynn_early.dropna(subset=["KGR_SUBGROUP_FUL_PCT"]).copy()
            fdk["FDK"] = fdk["KGR_SUBGROUP_FUL_PCT"].apply(lambda x: x / 100.0 if x > 1.5 else x)
            # DESE ships two artifact years (SY2006 ≈ 1%, SY2021 ≈ 2%) where the
            # full-day-K share collapses to near-zero while every neighbouring
            # year sits at ~100% — a reporting gap, not a real swing. Dropping
            # values < 50% keeps the long flat-at-full-day trend honest instead
            # of drawing two phantom cliffs.
            fdk_glitch = fdk[fdk["FDK"] <= 0.5]
            fdk = fdk[fdk["FDK"] > 0.5]
            if len(fdk) > 1:
                fig = px.line(fdk, x="SY", y="FDK", markers=True)
                fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                  yaxis_title="% kindergartners in full-day",
                                  xaxis_title="School Year")
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")
                if not fdk_glitch.empty:
                    _gy = ", ".join(f"SY{int(y)}" for y in sorted(fdk_glitch["SY"]))
                    st.caption(
                        f"Lynn has offered universal full-day kindergarten across "
                        f"this period. {_gy} are omitted as DESE reporting "
                        f"artifacts (near-zero values that don't reflect a real "
                        f"change in access)."
                    )

    st.divider()

    # -------------------------------------------------------------------
    # Special education — placement settings (n62c-bx65)
    # -------------------------------------------------------------------
    st.subheader("Placement settings — how students with disabilities are educated")
    st.caption(
        "How students with disabilities spend their day: full inclusion (≥80% in "
        "general education), partial inclusion, substantially separate, or a "
        "separate school. Lynn vs the statewide mix. Source: DESE SpEd "
        "Characteristics (n62c-bx65)."
    )
    sped_pl = load_dataset("sped_placement")
    if not sped_pl.empty:
        pl = sped_pl[(sped_pl["IND_CAT"] == "Placement")
                     & (sped_pl["IND_DESC"] != "Total Students with Disabilities")].copy()
        if not pl.empty:
            latest_pl = int(pl["SY"].max())
            order = ["Full Inclusion", "Partial Inclusion", "Substantially Separate",
                     "Separate School in District"]
            rows = []
            for code, label in [(LYNN_DISTRICT_CODE, "Lynn"), ("00000000", "Massachusetts")]:
                d = pl[(pl["DIST_CODE"] == code) & (pl["SY"] == latest_pl)]
                for _, rr in d.iterrows():
                    rows.append({"Setting": rr["IND_DESC"], "Series": label, "Pct": rr["IND_PCT"]})
            if rows:
                pl_df = pd.DataFrame(rows)
                fig = px.bar(pl_df, x="Setting", y="Pct", color="Series", barmode="group",
                             category_orders={"Setting": order},
                             color_discrete_map={"Lynn": LEHS_NAVY, "Massachusetts": "#A8B5BD"})
                fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%",
                                  yaxis_title="% of students with disabilities",
                                  xaxis_title="", legend_title="")
                st.plotly_chart(fig, width="stretch")
                st.caption(f"School year {latest_pl}.")


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
            ell_range = st.slider("% English Learner(s) range", 0, 100, (0, 100), step=5)

        filtered = latest.copy()

        def _grade_mask(cols: list[str]) -> pd.Series:
            """Sum across grade-level count columns that actually exist on the
            frame. DESE doesn't ship PK_CNT for every school row (notably the
            alternative academies), so guarding here prevents a KeyError when
            the user toggles a grade band the row doesn't carry."""
            present = [c for c in cols if c in filtered.columns]
            if not present:
                return pd.Series(False, index=filtered.index)
            return filtered[present].sum(axis=1) > 0

        if grade_filter:
            grade_masks = []
            if "PK" in grade_filter:
                grade_masks.append(_grade_mask(["PK_CNT"]))
            if "K-5" in grade_filter:
                grade_masks.append(_grade_mask(
                    ["K_CNT", "G1_CNT", "G2_CNT", "G3_CNT", "G4_CNT", "G5_CNT"]
                ))
            if "Middle" in grade_filter:
                grade_masks.append(_grade_mask(["G6_CNT", "G7_CNT", "G8_CNT"]))
            if "High" in grade_filter:
                grade_masks.append(_grade_mask(["G9_CNT", "G10_CNT", "G11_CNT", "G12_CNT"]))
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
            "ORG_CODE", "ORG_NAME", "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT",
            "HN_PCT", "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT",
        ]].rename(columns={
            "ORG_NAME": "School",
            "TOTAL_CNT": "Enrollment",
            "EL_PCT": "% English Learner(s)",
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

        # DESE accountability classification — latest determination per school,
        # joined on the 8-digit org code. Missing rows (new/alt programs) show
        # an em-dash rather than dropping the school from the table.
        display["ORG_CODE"] = display["ORG_CODE"].astype(str).str.zfill(8)
        _acct_sy = None
        if not acct.empty and {"ORG_CODE", "CLASSIFICATION"}.issubset(acct.columns):
            _acct = acct.copy()
            _acct["ORG_CODE"] = _acct["ORG_CODE"].astype(str).str.zfill(8)
            if "SY" in _acct.columns:
                _acct = _acct.sort_values("SY")
                _acct_sy = int(pd.to_numeric(_acct["SY"], errors="coerce").max())
            _acct = _acct.groupby("ORG_CODE").tail(1)
            display = display.merge(
                _acct[["ORG_CODE", "CLASSIFICATION"]].rename(
                    columns={"CLASSIFICATION": "Classification"}
                ),
                on="ORG_CODE", how="left",
            )
            display["Classification"] = display["Classification"].fillna("—")

        # One-click link to each school's official DESE profile page.
        display["DESE profile"] = display["ORG_CODE"].map(
            lambda c: (
                f"https://profiles.doe.mass.edu/profiles/student.aspx"
                f"?orgcode={c}&orgtypecode=6"
            )
        )
        display = display.drop(columns=["ORG_CODE"])

        st.dataframe(
            display.sort_values("School").style.apply(highlight_lehs, axis=1),
            width="stretch", hide_index=True, height=500,
            column_config={
                "DESE profile": st.column_config.LinkColumn(
                    "DESE profile", display_text="profile ↗",
                ),
            },
        )
        if _acct_sy is not None:
            st.caption(
                f"**Classification** is DESE's SY {_acct_sy} accountability "
                f"determination (accountability_summary parquet). "
                f"**DESE profile** opens the school's official page at "
                f"profiles.doe.mass.edu."
            )

        # -------------------------------------------------------------------
        # Scatter: enrollment vs % English Learner(s)
        # -------------------------------------------------------------------
        st.subheader("Lynn schools — Enrollment vs. % English Learner(s)")

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
            xaxis_title="Enrollment", yaxis_title="% English Learner(s)",
        )
        st.plotly_chart(fig, width="stretch")

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
            a = a[(a["STU_GRP"] == "All Students") & (a["ATTEND_PERIOD"] == "End of Year")]
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

        # -------------------------------------------------------------------
        # Variance flags — which schools sit far from the district norm?
        # z-scores vs. the unweighted mean of Lynn schools with published
        # data, on two metrics already in this table: chronic absence and
        # MCAS % M+E (row-mean of whichever M+E columns a school reports).
        # |z| >= 1.5 gets flagged. Wording stays neutral — a flag means
        # "far from the district norm", in either direction, not a rating.
        # -------------------------------------------------------------------
        Z_FLAG = 1.5

        def _zscore(s: pd.Series) -> pd.Series:
            s = pd.to_numeric(s, errors="coerce")
            sd = s.std()
            if pd.isna(sd) or sd == 0:
                return pd.Series([pd.NA] * len(s), index=s.index)
            return (s - s.mean()) / sd

        _na_series = pd.Series([pd.NA] * len(perf), index=perf.index)
        _z_chron = (
            _zscore(perf["PCT_CHRON_ABS_10"])
            if "PCT_CHRON_ABS_10" in perf.columns else _na_series
        )
        _mcas_cols = [c for c in [
            "MCAS G10 ELA M+E%", "MCAS G10 Math M+E%",
            "MCAS 3-8 ELA M+E%", "MCAS 3-8 Math M+E%",
        ] if c in perf.columns]
        _z_mcas = (
            _zscore(perf[_mcas_cols].mean(axis=1)) if _mcas_cols else _na_series
        )

        def _flag_label(zc, zm) -> str:
            notes = []
            if pd.notna(zc) and abs(zc) >= Z_FLAG:
                notes.append(
                    f"chronic absence {'above' if zc > 0 else 'below'} "
                    f"district norm (z {zc:+.1f})"
                )
            if pd.notna(zm) and abs(zm) >= Z_FLAG:
                notes.append(
                    f"MCAS M+E {'above' if zm > 0 else 'below'} "
                    f"district norm (z {zm:+.1f})"
                )
            return "; ".join(notes)

        perf["Stands out"] = [
            _flag_label(zc, zm) for zc, zm in zip(_z_chron, _z_mcas)
        ]

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
                     width="stretch", hide_index=True, height=500)

        # Filtered callout listing the flagged schools, with enrollment n so
        # small-school volatility is visible next to each flag.
        _flagged = perf[perf["Stands out"] != ""].merge(
            filtered[["ORG_CODE", "TOTAL_CNT"]], on="ORG_CODE", how="left",
        )
        if not _flagged.empty:
            _lines = []
            for _, fr in _flagged.sort_values("ORG_NAME").iterrows():
                _n_txt = (
                    f"{int(fr['TOTAL_CNT']):,} students"
                    if pd.notna(fr.get("TOTAL_CNT")) else "enrollment n/a"
                )
                _lines.append(f"- **{fr['ORG_NAME']}** ({_n_txt}): {fr['Stands out']}")
            st.markdown(
                "**Statistical stand-outs** — schools at least 1.5 standard "
                "deviations from the unweighted mean of Lynn schools on a "
                "metric in this table:\n" + "\n".join(_lines)
            )
            st.caption(
                "A flag is descriptive, not a quality rating — it marks a "
                "value far from the district norm in either direction. "
                "Smaller schools (see the enrollment shown) can swing on a "
                "handful of students, so read their flags with extra caution."
            )

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
                st.metric("Weighted % English Learner(s)", f"{wtd_ell:.0%}")
        with c3:
            if total_enr > 0:
                wtd_li = (filtered["TOTAL_CNT"] * filtered["LI_PCT"]).sum() / total_enr
                st.metric("Weighted % Low Income", f"{wtd_li:.0%}")
        with c4:
            st.metric("Schools shown", f"{len(filtered)}")


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
    "School choice / outflow": load_dataset("school_choice"),
    "Early education (Pre-K & K)": load_dataset("early_education"),
    "SpEd placement settings": load_dataset("sped_placement"),
    "Accountability classifications": acct,
})

page_footer()
