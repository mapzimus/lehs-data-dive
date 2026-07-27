"""College & Career — in-HS preparation plus post-graduation outcomes (former College & Career and Success After HS pages)."""
import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, data_downloads_panel
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label
from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.charts import (
    DEFAULT_LAYOUT,
    LEHS_GOLD,
    LEHS_NAVY,
    SUBGROUP_PALETTE,
    span_years,
    with_year_gaps,
    year_axis,
)
st.set_page_config(page_title="College & Career | LEHS", page_icon="🎓", layout="wide")
sidebar_attribution()

st.title("College, Career & Beyond")
st.markdown(
    "How LEHS students prepare for what comes after high school — and how "
    "they actually fare once they get there. **Preparing in HS** covers "
    "pathways, early college, and MassCore; **After Graduation** follows "
    "graduates into college enrollment, persistence, completion, and the "
    "workforce."
)
_tab_0, _tab_1 = st.tabs(['🎓 Preparing in HS', '🚀 After Graduation'])

with _tab_0:
    # ==== from pages/5_College_and_Career.py ====
    st.header("College & Career Readiness")
    st.markdown(
        "Pathway programs (CTE, Early College, Innovation Pathways), FAFSA "
    "completion, and what actually happens to Lynn graduates — enrollment, "
    "employment, and destination colleges."
    )
    st.page_link(
        "pages/2b_Courses_and_Academics.py",
        label="AP, SAT, and coursework → Courses & Academics",
    )

    pathways = load_dataset("pathways_enrollment")
    ec_part = load_dataset("early_college_participation")
    cco = load_dataset("college_career_outcomes")

    if pathways.empty and ec_part.empty and cco.empty:
        st.info("Data is temporarily unavailable. Please check back later.")
        st.stop()

    # ---------------------------------------------------------------------------
    # Headline metrics — pathway / early-college / outcome tiles. (The AP and
    # MassCore tiles that used to sit here moved with their sections to
    # Courses & Academics.)
    # ---------------------------------------------------------------------------

    st.header("Headline Metrics")

    cols = st.columns(3)

    # Tile 1 — FAFSA completion (DART indicator, stored on a 0–100 scale).
    with cols[0]:
        sub = get_dart_indicator(LEHS_SCHOOL_CODE, "Grade 12 students who completed FAFSA")
        if not sub.empty:
            v = sub.iloc[-1]["VALUE"]
            st.metric("% Completed FAFSA", f"{v:.0f}%")

    # Tile 2 — Early College participation (largest pathway at LEHS). The
    # pathway-level total is the max PROGRAM_CNT within the (SY, PATHWAY) group —
    # same convention as the Pathway Programs chart below.
    with cols[1]:
        if not pathways.empty:
            p_hero = pathways[pathways["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
            p_hero["PROGRAM_CNT"] = pd.to_numeric(p_hero["PROGRAM_CNT"], errors="coerce")
            ec_hero = p_hero[p_hero["PATHWAY"] == "Early College"].dropna(subset=["PROGRAM_CNT"])
            if not ec_hero.empty:
                hero_sy = int(ec_hero["SY"].max())
                hero_n = int(ec_hero[ec_hero["SY"] == hero_sy]["PROGRAM_CNT"].max())
                st.metric(f"Early College students (SY {sy_label(hero_sy)})", f"{hero_n:,}")

    # Tile 3 — postsecondary enrollment one year out (Lynn district cohort), from
    # the College and Career Outcomes file's Total Postsecondary aggregate.
    with cols[2]:
        if not cco.empty:
            cco_hero = cco[cco["DIST_CODE"] == "01630000"].copy()
            cco_hero["OUTCOME_CNT"] = pd.to_numeric(cco_hero["OUTCOME_CNT"], errors="coerce")
            cco_hero["GRAD_CNT"] = pd.to_numeric(cco_hero["GRAD_CNT"], errors="coerce")
            if not cco_hero.empty:
                hero_yr = int(cco_hero["HS_GRAD_YEAR"].max())
                hero_row = cco_hero[
                    (cco_hero["HS_GRAD_YEAR"] == hero_yr)
                    & (cco_hero["OUTCOME_YEAR"] == hero_yr)
                    & (cco_hero["OUTCOME_TYPE"] == "Total Postsecondary Enrollment")
                ]
                if not hero_row.empty and pd.notna(hero_row.iloc[0]["GRAD_CNT"]) and hero_row.iloc[0]["GRAD_CNT"] > 0:
                    pct = hero_row.iloc[0]["OUTCOME_CNT"] / hero_row.iloc[0]["GRAD_CNT"]
                    st.metric(
                        f"Lynn grads in college 1 yr out (Class of {hero_yr})",
                        f"{pct:.0%}",
                    )

    st.divider()

    # ---------------------------------------------------------------------------
    # Pathway program participation
    # ---------------------------------------------------------------------------

    st.header("Pathway Programs")
    st.caption(
        "CTE (Career Technical Education), Early College, and Innovation Career "
    "Pathways are designated programs that give HS students a head start on "
    "post-secondary credits and career exploration."
    )

    if not pathways.empty:
        p = pathways[pathways["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
        if not p.empty:
            # The file lists, per pathway, both a pathway-summary row and its
            # individual sub-program rows (and the labels drift year to year). The
            # pathway-level total is always the largest count within each
            # (SY, PATHWAY) group, so take the max to get one clean number per
            # pathway per year without summing sub-programs.
            p["PROGRAM_CNT"] = pd.to_numeric(p["PROGRAM_CNT"], errors="coerce")
            # "After Dark" is the evening delivery model for the Chapter 74 career-tech
            # programs — it counts the *same* students as "Career Tech Ed (Ch. 74)".
            # Drawing both as separate grouped bars implies they are distinct,
            # additive populations, so we drop the duplicate "After Dark" series and
            # show only the two non-overlapping pathways.
            PATHWAY_LABELS = {
                "Early College": "Early College",
                "Career Technical Education (Chapter 74 Programs)": "Career Tech Ed (Ch. 74)",
            }
            pw = p[p["PATHWAY"].isin(PATHWAY_LABELS)].copy()
            pw["Pathway"] = pw["PATHWAY"].map(PATHWAY_LABELS)
            pw_totals = (
                pw.groupby(["SY", "Pathway"], as_index=False)["PROGRAM_CNT"].max()
                .rename(columns={"PROGRAM_CNT": "Students"})
                .dropna(subset=["Students"])
            )
            if not pw_totals.empty:
                pw_totals["Students"] = pw_totals["Students"].astype(int)
                st.subheader("LEHS students in designated pathways, by year")
                fig = px.bar(
                    pw_totals.sort_values(["SY", "Pathway"]),
                    x="SY", y="Students", color="Pathway", barmode="group",
                    text="Students",
                    color_discrete_map={
                        "Early College": LEHS_NAVY,
                        "Career Tech Ed (Ch. 74)": LEHS_GOLD,
                    },
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT, yaxis_title="Students enrolled",
                    xaxis_title="School Year", legend_title="Pathway",
                )
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "Counts are students enrolled in each designated pathway. Early "
                "College is by far the largest at LEHS and has roughly doubled "
                "since SY 2021-22. The Chapter 74 career-tech programs are "
                "delivered through the after-school \"After Dark\" model, so "
                "they are shown as a single bar to avoid double-counting the "
                "same students."
                )
        else:
            st.info("No LEHS pathways enrollment data (program may not be designated here).")

    # Early College specifically — participants by partner college over time
    if not ec_part.empty:
        ec_lehs = ec_part[
            (ec_part["ORG_CODE"] == LEHS_SCHOOL_CODE)
            & (ec_part["STU_GRP"] == "All Students")
        ].copy()
        if not ec_lehs.empty:
            st.subheader("Early College participation — by partner college")
            ec_lehs["ALL_CNT"] = pd.to_numeric(ec_lehs["ALL_CNT"], errors="coerce")
            # Each student is reported in both a Fall and a Spring term; use the
            # Fall snapshot (fall back to Spring when a year has no Fall row) so we
            # count participants once rather than summing the two terms.
            ec_lehs["_per_rank"] = ec_lehs["PERIOD"].map({"Fall": 0, "Spring": 1})
            ec_snap = (
                ec_lehs.sort_values("_per_rank")
                .groupby(["SY", "CEEB_NAME"], as_index=False)
                .first()
            )
            ec_snap["Partner"] = ec_snap["CEEB_NAME"].replace(
                {"No Data": "Partner not reported"}
            )
            ec_snap = ec_snap.dropna(subset=["ALL_CNT"])
            if not ec_snap.empty:
                ec_snap["ALL_CNT"] = ec_snap["ALL_CNT"].astype(int)
                fig = px.bar(
                    ec_snap.sort_values(["SY", "Partner"]),
                    x="SY", y="ALL_CNT", color="Partner", barmode="stack",
                    text="ALL_CNT",
                    color_discrete_sequence=[LEHS_NAVY, LEHS_GOLD, "#9AA7B8"],
                )
                fig.update_traces(textposition="inside", cliponaxis=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT, yaxis_title="Students participating",
                    xaxis_title="School Year", legend_title="Partner college",
                )
                st.plotly_chart(fig, width="stretch")
                st.caption(
                    "Lynn English partners with North Shore Community College and "
                "Salem State University so students can earn college credit "
                "while still in high school. Participation has grown steadily, "
                "from about 50 students in SY 2020-21 to more than 330 in "
                "SY 2023-24. (The earliest year predates the named partnerships.)"
                )

    st.divider()

    # ---------------------------------------------------------------------------
    # Early college credits earned — by partner CEEB
    # ---------------------------------------------------------------------------

    st.header("Early College Credits — Lynn District")
    st.caption(
        "Above is *participation* (any rows = participating). This section is the "
    "*credit volume*: how many college credits Lynn HS students actually "
    "earn each year, broken out by partner college (identified by its "
    "College Board / CEEB code). Source: "
    "*Early College Credits* dataset."
    )

    early_credits = load_dataset("early_college_credits")
    if not early_credits.empty:
        ec_lynn = early_credits[early_credits["DIST_CODE"] == "01630000"].copy()
        ec_lynn["EARNED_CREDIT_CNT"] = pd.to_numeric(ec_lynn["EARNED_CREDIT_CNT"], errors="coerce")
        ec_lynn["REG_CREDITS_CNT"] = pd.to_numeric(ec_lynn["REG_CREDITS_CNT"], errors="coerce")
        ec_lynn["STU_CNT"] = pd.to_numeric(ec_lynn["STU_CNT"], errors="coerce")

        # Filter to All Students rows, latest year
        ec_all = ec_lynn[ec_lynn["STU_GRP"] == "All Students"].copy()
        if not ec_all.empty:
            latest_ec = int(ec_all["SY"].max())
            ec_latest = ec_all[ec_all["SY"] == latest_ec].copy()
            # Sum across periods if both Fall and Spring present
            ec_agg = (
                ec_latest.groupby("CEEB_NAME", as_index=False)
                         .agg(STU_CNT=("STU_CNT", "sum"),
                              REG_CREDITS_CNT=("REG_CREDITS_CNT", "sum"),
                              EARNED_CREDIT_CNT=("EARNED_CREDIT_CNT", "sum"))
                         .dropna(subset=["EARNED_CREDIT_CNT"])
                         .sort_values("EARNED_CREDIT_CNT")
            )
            if not ec_agg.empty:
                st.subheader(f"Credits earned by partner college (SY {latest_ec - 1}-{str(latest_ec)[-2:]})")
                # Pass rate (earned/registered) sits in a narrow band across partners
                # (~93–95%), so a continuous colorscale would exaggerate a trivial
                # spread and distract from the actual measure (credits earned). Use a
                # single brand color for the bars and keep pass rate in the hover.
                ec_agg["pass_rate"] = ec_agg["EARNED_CREDIT_CNT"] / ec_agg["REG_CREDITS_CNT"]
                fig = px.bar(
                    ec_agg, y="CEEB_NAME", x="EARNED_CREDIT_CNT", orientation="h",
                    hover_data={"STU_CNT": True, "REG_CREDITS_CNT": True, "pass_rate": ":.0%"},
                    text=ec_agg["EARNED_CREDIT_CNT"].astype(int).astype(str),
                )
                fig.update_traces(textposition="outside", cliponaxis=False, marker_color=LEHS_NAVY)
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    height=max(280, 36 * len(ec_agg)),
                    xaxis_title="Credits earned",
                    xaxis_range=[0, ec_agg["EARNED_CREDIT_CNT"].max() * 1.15],
                    yaxis_title="",
                )
                st.plotly_chart(fig, width="stretch")
    else:
        st.info("Early-college credit data not available yet.")

    st.divider()

    # ---------------------------------------------------------------------------
    # College + career outcomes — what happens to Lynn graduates?
    # ---------------------------------------------------------------------------

    st.header("What happens to Lynn graduates? — Outcome breakdown")
    st.caption(
        "DESE's *College and Career Outcomes* dataset tracks each Lynn-district "
    "HS cohort one year out: where they enrolled (in-state public/private "
    "2-yr/4-yr, out-of-state), whether they were employed, or whether their "
    "outcome is missing/unknown."
    )

    if not cco.empty:
        cco_lynn = cco[cco["DIST_CODE"] == "01630000"].copy()
        cco_lynn["OUTCOME_CNT"] = pd.to_numeric(cco_lynn["OUTCOME_CNT"], errors="coerce")
        cco_lynn["GRAD_CNT"] = pd.to_numeric(cco_lynn["GRAD_CNT"], errors="coerce")

        if not cco_lynn.empty:
            latest_cco_year = int(cco_lynn["HS_GRAD_YEAR"].max())
            # Pick the row where OUTCOME_YEAR matches HS_GRAD_YEAR (one year out view)
            snap = cco_lynn[
                (cco_lynn["HS_GRAD_YEAR"] == latest_cco_year)
                & (cco_lynn["OUTCOME_YEAR"] == latest_cco_year)
            ].copy()

            if not snap.empty:
                # Drop the Total Postsecondary aggregate (it's the sum of the
                # itemized in-state public/private + out-of-state rows) so the
                # bar chart isn't doubled.
                itemized = snap[~snap["OUTCOME_TYPE"].isin(["Total Postsecondary Enrollment"])].copy()
                itemized = itemized.sort_values("OUTCOME_CNT", ascending=True)
                grad_total = int(snap["GRAD_CNT"].iloc[0])
                itemized["pct_of_cohort"] = itemized["OUTCOME_CNT"] / grad_total
                itemized["label"] = itemized.apply(
                    lambda r: (
                        f"{int(r['OUTCOME_CNT']):,} "
                    f"({r['pct_of_cohort']:.0%})"
                    ), axis=1,
                )

                st.subheader(
                    f"{latest_cco_year} Lynn district cohort — {grad_total:,} grads"
                )
                color_map_outcome = {
                    "Total Missing":          "#90A4AE",
                    "In-State Public 4-Year": LEHS_NAVY,
                    "In-State Public 2-Year": "#A6C8E8",
                    "In-State Private":       "#8294AE",
                    "Out-of-State":           LEHS_GOLD,
                    "Total Employed":         "#9CCFC4",
                }
                fig = px.bar(
                    itemized, y="OUTCOME_TYPE", x="OUTCOME_CNT", orientation="h",
                    color="OUTCOME_TYPE", color_discrete_map=color_map_outcome,
                    text="label",
                )
                fig.update_traces(textposition="outside")
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    xaxis_title="Graduates",
                    yaxis_title="",
                    showlegend=False,
                    height=380,
                )
                st.plotly_chart(fig, width="stretch")

                missing_pct = float(
                    itemized.loc[itemized["OUTCOME_TYPE"] == "Total Missing", "pct_of_cohort"].iloc[0]
                ) if (itemized["OUTCOME_TYPE"] == "Total Missing").any() else None
                if missing_pct is not None and missing_pct > 0.25:
                    st.warning(
                        f"**Note:** {missing_pct:.0%} of the cohort has no "
                    f"reportable outcome (not enrolled in any tracked "
                    f"institution, no W-2 earnings, or simply unmatched). "
                    f"That suppression bites hardest at the bottom of the "
                    f"pipeline — students with missing outcomes are "
                    f"disproportionately likely to be disconnected."
                    )
    else:
        st.info("College/career outcomes data not available yet.")

    st.divider()

    # ---------------------------------------------------------------------------
    # Where Lynn grads land (IPEDS / College Scorecard)
    # ---------------------------------------------------------------------------

    st.header("Where Lynn grads land — destination college profiles")
    st.caption(
        "Top colleges Lynn graduates enroll in, with institutional data from the "
    "federal College Scorecard / IPEDS. Source: scripts/05_download_ipeds.py."
    )

    ipeds = load_dataset("ipeds_destinations")
    if ipeds.empty:
        st.info(
            "Destination college data not yet populated. The ingest scaffold is "
        "at scripts/05_download_ipeds.py — it queries College Scorecard's "
        "free API; rate-limited demo key may return empty."
        )
    else:
        display_cols = {
            "INSTITUTION": "Institution",
            "STATE": "State",
            "SECTOR": "Sector",
            "GRAD_RATE_150": "Grad rate (150%)",
            "COST_IN_STATE": "In-state cost",
            "COST_OUT_STATE": "Out-of-state cost",
            "PELL_PCT": "% Pell recipients",
            "BLACK_PCT": "% Black",
            "HISP_PCT": "% Hispanic",
            "WHITE_PCT": "% White",
            "ASIAN_PCT": "% Asian",
        }
        # Drop any enrichment column that is entirely empty so we never render a
        # wall of em-dashes — the College Scorecard demo key frequently returns
        # institution names only. If nothing but names came back, show the names as
        # a clean list with an honest note instead of a one-real-column table.
        enrich_cols = [c for c in display_cols if c != "INSTITUTION" and c in ipeds.columns]
        populated = [c for c in enrich_cols if ipeds[c].notna().any()]
        if not populated:
            st.info(
                "We have the destination institution names below, but the College "
            "Scorecard enrichment (grad rate, cost, demographics) isn't "
            "populated in this build — so rather than a table of blanks, here's "
            "the institution list."
            )
            _names = ipeds["INSTITUTION"].dropna().astype(str).tolist()
            st.markdown("\n".join(f"- {n}" for n in _names))
        else:
            have = ["INSTITUTION"] + populated
            display = ipeds[have].rename(columns=display_cols).copy()
            for c in ["Grad rate (150%)", "% Pell recipients", "% Black", "% Hispanic",
                      "% White", "% Asian"]:
                if c in display.columns:
                    display[c] = display[c].apply(
                        lambda x: f"{x:.0%}" if pd.notna(x) and isinstance(x, (int, float)) else "—"
                    )
            for c in ["In-state cost", "Out-of-state cost"]:
                if c in display.columns:
                    display[c] = display[c].apply(
                        lambda x: f"${x:,.0f}" if pd.notna(x) and isinstance(x, (int, float)) else "—"
                    )
            st.dataframe(display, width="stretch", hide_index=True, height=420)

    st.divider()

    # ---------------------------------------------------------------------------
    # Downloads + footer
    # ---------------------------------------------------------------------------

    data_downloads_panel({
        "Pathways enrollment": pathways,
        "Early College participation": ec_part,
        "Early College credits": early_credits,
        "College & career outcomes": cco,
        "IPEDS destinations": ipeds,
    })

with _tab_1:
    # ==== from pages/6_Success_After_HS.py ====
    st.header("Success After High School")
    st.markdown(
        "**The headline question every parent, teacher, and school committee "
    "member asks: of every 100 9th-graders who walk into LEHS, how many "
    "graduate, how many enroll in college, and how many are still there "
    "a year later?** This page follows the full pipeline from 9th-grade "
    "entry through degree completion and into the workforce."
    )

    dart = load_dataset("dart_success_after_hs")
    grad = load_dataset("graduation_rates")
    prog = load_dataset("student_progression_hs_to_postsec")
    if dart.empty or grad.empty:
        st.info("Data is temporarily unavailable. Please check back later.")
        st.stop()

    # ---------------------------------------------------------------------------
    # Cohort funnel — the hero. Of every 100 9th-graders, how many reach each
    # stage? This used to be a separate "Cohort Tracking" page; folded in here
    # because it's the same Success story.
    # ---------------------------------------------------------------------------

    YEAR2_INDICATOR = "Student progression from high school through second year of postsecondary education"
    DEGREE_INDICATOR = "Student progression from high school through postsecondary degree completion"

    cohort_n = grad_n = enr_n = pers_n = None
    latest_cohort = None
    lehs_prog = pd.DataFrame()
    lehs_y2_all = pd.DataFrame()

    if not prog.empty:
        prog["DIST_CODE"] = prog["DIST_CODE"].astype(str).str.zfill(8)
        prog["ORG_CODE"] = prog["ORG_CODE"].astype(str).str.zfill(8)
        lehs_prog = prog[prog["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
        lehs_y2_all = lehs_prog[
            (lehs_prog["INDICATOR"] == YEAR2_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
        ].sort_values("COHORTYR")

        if not lehs_y2_all.empty:
            latest = lehs_y2_all.iloc[-1]
            latest_cohort = int(latest["COHORTYR"])
            cohort_n = int(latest["COHORT_CNT"])
            grad_n = int(latest["GRAD_CNT"]) if pd.notna(latest["GRAD_CNT"]) else 0
            enr_n = int(latest["IMMEDIATEENR_CNT"]) if pd.notna(latest["IMMEDIATEENR_CNT"]) else 0
            pers_n = int(latest["PERSIST_CNT"]) if pd.notna(latest["PERSIST_CNT"]) else 0

    if cohort_n:
        st.header(f"The Cohort Funnel — {latest_cohort - 4}–{latest_cohort} Class")
        st.caption(
            f"All Students who entered LEHS as 9th-graders before the SY "
        f"{latest_cohort - 1}-{str(latest_cohort)[-2:]} graduation, tracked "
        f"through their second year of college."
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Entered 9th grade", f"{cohort_n:,}", "baseline cohort")
        with c2:
            st.metric("Graduated high school", f"{grad_n:,}",
                      f"{grad_n / cohort_n:.0%} of cohort", delta_color="off")
        with c3:
            st.metric("Enrolled in college", f"{enr_n:,}",
                      f"{enr_n / cohort_n:.0%} of cohort", delta_color="off")
        with c4:
            st.metric("Still enrolled year 2", f"{pers_n:,}",
                      f"{pers_n / cohort_n:.0%} of cohort", delta_color="off")

        stages = ["Entered 9th grade", "Graduated", "Enrolled in college", "Persisted to year 2"]
        counts = [cohort_n, grad_n, enr_n, pers_n]
        pcts = [c / cohort_n for c in counts]
        labels = [f"{c:,}<br>({p:.0%})" for c, p in zip(counts, pcts)]

        fig = go.Figure(
            go.Funnel(
                y=stages, x=counts, text=labels, textposition="inside",
                textfont=dict(color="white", size=14),
                marker=dict(color=[LEHS_NAVY, "#8294AE", "#9CCFC4", LEHS_GOLD]),
                connector=dict(line=dict(color="#B0BEC5", width=1)),
            )
        )
        fig.update_layout(**DEFAULT_LAYOUT, height=360)
        st.plotly_chart(fig, width="stretch")

        st.markdown(
            f"**The headline number:** of every 100 LEHS 9th-graders, "
        f"~{round(grad_n / cohort_n * 100)} graduate, "
        f"~{round(enr_n / cohort_n * 100)} enroll in college, and only "
        f"**~{round(pers_n / cohort_n * 100)} are still in college a year later**."
        )

        st.divider()

    # ---------------------------------------------------------------------------
    # Pipeline metrics — headline DART indicators
    # ---------------------------------------------------------------------------

    st.header("Headline Pipeline Metrics")

    metrics_to_show = [
        ("4-year cohort graduation rate", "4-Year Grad Rate", "pct"),
        ("9th to 10th grade promotion rate (first-time 9th graders only)", "9-10 Promotion", "pct"),
        ("Annual dropout rate", "Annual Dropout", "pct"),
        ("Students enrolled in postsecondary education in the immediate fall after high school graduation",
         "Immediate College Enrollment", "pct"),
        ("College students persistently enrolled in postsecondary education for the first two years",
         "College Persistence (yr 2)", "pct"),
        ("Grade 12 students who completed FAFSA", "FAFSA Completed", "pct"),
    ]

    cols = st.columns(3)
    for i, (ind, label, fmt) in enumerate(metrics_to_show):
        sub = get_dart_indicator(LEHS_SCHOOL_CODE, ind)
        if sub.empty:
            continue
        latest = sub.iloc[-1]
        prior = sub.iloc[-2] if len(sub) > 1 else None
        val = latest["VALUE"]
        # DART percentage indicators are stored as 0-100 (e.g., 81.5 for 81.5%),
        # not 0-1 fractions
        if fmt == "pct":
            display = f"{val:.1f}%"
        else:
            display = f"{val:,.0f}"
        delta = ""
        if prior is not None and pd.notna(prior["VALUE"]):
            diff = val - prior["VALUE"]
            unit = "pts" if fmt == "pct" else ""
            delta = f"{diff:+.1f} {unit} vs SY {int(prior['SY'])}"
        with cols[i % 3]:
            st.metric(label, display, delta)

    st.divider()

    # ---------------------------------------------------------------------------
    # Graduation rate trend by student group
    # ---------------------------------------------------------------------------

    st.header("4-Year Graduation Rate by Student Group")

    g = grad[
        (grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
    ].copy()
    g["STU_GRP"] = g["STU_GRP"].astype(str).str.replace("\xa0", " ")

    priority_groups = [
        "All Students",
        "English Learner", "English Learners", "Former English Learners",
        "Hispanic or Latino", "Black or African American", "Asian", "White",
        "Low Income", "Students with Disabilities", "High Needs",
    ]
    g_focus = g[g["STU_GRP"].isin(priority_groups)].copy()

    if not g_focus.empty:
        color_map_grad = {
            "All Students":                LEHS_NAVY,
            "English Learners":            SUBGROUP_PALETTE["English Learner"],
            "English Learner":             SUBGROUP_PALETTE["English Learner"],
            "Former English Learners":     SUBGROUP_PALETTE["Former English Learner"],
            "Hispanic or Latino":          SUBGROUP_PALETTE["Hispanic/Latino"],
            "Black or African American":   SUBGROUP_PALETTE["African American/Black"],
            "Asian":                       SUBGROUP_PALETTE["Asian"],
            "White":                       SUBGROUP_PALETTE["White"],
            "Low Income":                  SUBGROUP_PALETTE["Low Income"],
            "Students with Disabilities":  SUBGROUP_PALETTE["Students w/ Disabilities"],
            "High Needs":                  SUBGROUP_PALETTE["High Needs"],
        }
        # Break any COVID-era reporting gap so the line doesn't connect across a
        # missing year.
        _g_focus_g = with_year_gaps(
            g_focus, "GRAD_PCT", group_col="STU_GRP", years=span_years(g_focus),
        )
        fig = px.line(
            _g_focus_g.sort_values("SY"), x="SY", y="GRAD_PCT", color="STU_GRP",
            markers=True, color_discrete_map=color_map_grad,
        )
        fig.update_traces(connectgaps=False)
        fig.update_layout(
            **DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="4-Year Grad Rate",
            xaxis_title="Cohort Year",
        )
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

    crosslink_callout(
        "Graduation and dropout are core ESSA accountability indicators — they feed "
    "directly into the determination DESE assigns LEHS each year. The "
    "**Accountability** page shows how heavily on-time graduation and dropout "
    "weigh against the other measures in the school's composite rating.",
        "Accountability",
        "See how graduation feeds the determination →",
    )

    # ---------------------------------------------------------------------------
    # Where the pipeline leaks — subgroup cohort progression (from cohort tracking)
    # ---------------------------------------------------------------------------

    if not prog.empty and latest_cohort is not None:
        st.header(f"Where the Pipeline Leaks — by Subgroup ({latest_cohort - 4}–{latest_cohort} Cohort)")
        st.caption(
            "The headline numbers above hide within-school disparities. Same cohort, "
        "broken out by subgroup. Bar length = share of that subgroup's 9th-grade "
        "entrants who reach each stage. Empty bars are DESE-suppressed (cell <10 students)."
        )

        sub_groups = lehs_prog[
            (lehs_prog["INDICATOR"] == YEAR2_INDICATOR)
            & (lehs_prog["COHORTYR"] == latest_cohort)
            & (lehs_prog["STU_GRP"] != "All Students")
        ].copy()
        sub_groups = sub_groups.assign(
            grad_pct=lambda d: d["GRAD_CNT"] / d["COHORT_CNT"],
            enr_pct=lambda d: d["IMMEDIATEENR_CNT"] / d["COHORT_CNT"],
            pers_pct=lambda d: d["PERSIST_CNT"] / d["COHORT_CNT"],
        )
        sub_groups = sub_groups[sub_groups["COHORT_CNT"] >= 10].copy()
        sub_groups = sub_groups.sort_values("pers_pct", ascending=True, na_position="first")

        if not sub_groups.empty:
            stage_labels = {
                "grad_pct": "Graduated",
                "enr_pct": "Enrolled in college",
                "pers_pct": "Persisted to year 2",
            }
            stage_colors = {
                "Graduated": "#90A4AE",
                "Enrolled in college": LEHS_NAVY,
                "Persisted to year 2": LEHS_GOLD,
            }
            melted = sub_groups.melt(
                id_vars=["STU_GRP", "COHORT_CNT"],
                value_vars=["grad_pct", "enr_pct", "pers_pct"],
                var_name="stage", value_name="pct",
            )
            melted["stage"] = melted["stage"].map(stage_labels)

            fig = px.bar(
                melted, x="pct", y="STU_GRP", color="stage", barmode="group",
                orientation="h", color_discrete_map=stage_colors,
                category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
                text=melted["pct"].apply(lambda x: f"{x:.0%}" if pd.notna(x) else ""),
            )
            fig.update_traces(textposition="outside", textfont=dict(size=10), cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                height=max(360, 28 * len(sub_groups)),
                xaxis_tickformat=".0%",
                xaxis_range=[0, 1.1],
                xaxis_title="Share of 9th-grade entrants reaching each stage",
                yaxis_title="",
                legend_title="",
            )
            st.plotly_chart(fig, width="stretch")

            # Surface the widest gap
            if not sub_groups["pers_pct"].dropna().empty:
                top_row = sub_groups.iloc[-1]
                bot_row = sub_groups.iloc[0]
                top_pct = top_row["pers_pct"]
                bot_pct = bot_row["pers_pct"]
                if pd.notna(top_pct) and pd.notna(bot_pct):
                    st.markdown(
                        f"**The widest gap:** {top_row['STU_GRP']} students persist to "
                    f"college year 2 at **{top_pct:.0%}**, while "
                    f"{bot_row['STU_GRP']} students persist at **{bot_pct:.0%}** "
                    f"— a **{(top_pct - bot_pct) * 100:.0f}-point** spread."
                    )

    st.divider()

    # ---------------------------------------------------------------------------
    # 4-year vs 5-year graduation comparison
    # ---------------------------------------------------------------------------

    st.header("4-Year vs. 5-Year Cohort Graduation")
    st.caption(
        "The 5-year rate gives students an extra year — for English Learner (ELL) "
    "and students with disabilities (SPED) especially, this often shows "
    "meaningful additional graduations."
    )

    g_both = grad[
        (grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (grad["STU_GRP"] == "All Students")
        & (grad["GRAD_RATE_TYPE"].isin([
            "4-Year Adjusted Cohort Graduation Rate",
            "5-Year Adjusted Cohort Graduation Rate",
        ]))
    ].copy()

    if not g_both.empty:
        _g_both_g = with_year_gaps(
            g_both, "GRAD_PCT", group_col="GRAD_RATE_TYPE", years=span_years(g_both),
        )
        fig = px.line(
            _g_both_g.sort_values("SY"), x="SY", y="GRAD_PCT", color="GRAD_RATE_TYPE",
            markers=True,
            color_discrete_map={
                "4-Year Adjusted Cohort Graduation Rate": LEHS_NAVY,
                "5-Year Adjusted Cohort Graduation Rate": LEHS_GOLD,
            },
        )
        fig.update_traces(connectgaps=False)
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Grad Rate")
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # ---------------------------------------------------------------------------
    # Postsecondary enrollment pathway
    # ---------------------------------------------------------------------------

    st.header("Where do LEHS graduates go?")

    immediate = get_dart_indicator(LEHS_SCHOOL_CODE, "Students enrolled in postsecondary education in the immediate fall after high school graduation")
    two_year = get_dart_indicator(LEHS_SCHOOL_CODE, "High school graduates enrolled in 2-year postsecondary education")
    four_year = get_dart_indicator(LEHS_SCHOOL_CODE, "High school graduates enrolled in 4-year postsecondary education")
    persist = get_dart_indicator(LEHS_SCHOOL_CODE, "College students persistently enrolled in postsecondary education for the first two years")

    pathway = pd.concat([
        immediate.assign(Indicator="Any college (immediate)"),
        two_year.assign(Indicator="2-year college"),
        four_year.assign(Indicator="4-year college"),
        persist.assign(Indicator="Persisted 2 years"),
    ])

    if not pathway.empty:
        # DART VALUE is 0-100; chart in raw percent and label axis explicitly.
        # Break any COVID-era reporting gap rather than connecting across it.
        _pathway_g = with_year_gaps(
            pathway, "VALUE", group_col="Indicator", years=span_years(pathway),
        )
        fig = px.line(
            _pathway_g.sort_values("SY"), x="SY", y="VALUE", color="Indicator",
            markers=True,
            color_discrete_map={
                "Any college (immediate)": LEHS_NAVY,
                "2-year college":          "#A6C8E8",
                "4-year college":          LEHS_NAVY,
                "Persisted 2 years":       LEHS_GOLD,
            },
        )
        fig.update_traces(connectgaps=False)
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="% of cohort",
                           yaxis_ticksuffix="%", yaxis_range=[0, 100])
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")
        st.caption(
            "**Indicator definitions** — "
        "**Any college (immediate)**: % of HS graduates who enrolled in any "
        "postsecondary institution the fall directly after graduation. "
        "**2-year / 4-year college**: subsets of the above, by institution type. "
        "**Persisted 2 years**: of the students who enrolled in college, the % "
        "who were still enrolled in their second fall semester (i.e., didn't drop "
        "out after year one). Persistence is a strong predictor of degree "
        "completion."
        )

    st.divider()

    # ---------------------------------------------------------------------------
    # Plans of HS Graduates
    # ---------------------------------------------------------------------------

    st.header("Self-Reported Plans of Graduates")
    st.caption("From end-of-year surveys of departing seniors.")

    plans = load_dataset("plans_of_graduates")
    plans_lehs = plans[plans["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()

    if not plans_lehs.empty:
        plan_cols = {
            "COLL_4YRPUB_PCT": "4-yr Public College",
            "COLL_4YRPRV_PCT": "4-yr Private College",
            "COLL_2YRPUB_PCT": "2-yr Public College",
            "COLL_2YRPRV_PCT": "2-yr Private College",
            "WORK_PCT":        "Work",
            "MILITARY_PCT":    "Military",
            "APPREN_PCT":      "Apprenticeship",
            "OTHER_PLANS_PCT": "Other",
            "UNKNWN_PLANS_PCT":"Unknown",
        }
        plans_long = plans_lehs.melt(
            id_vars="SY", value_vars=list(plan_cols.keys()),
            var_name="Plan", value_name="Pct",
        )
        plans_long["Plan"] = plans_long["Plan"].map(plan_cols)
        plans_long = plans_long.dropna(subset=["Pct"])

        fig = px.area(
            plans_long, x="SY", y="Pct", color="Plan",
            groupnorm=None,
            color_discrete_sequence=list(SUBGROUP_PALETTE.values()),
        )
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat=".0%", yaxis_title="Share of seniors")
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

    st.divider()

    # ---------------------------------------------------------------------------
    # Multi-cohort trend (from cohort tracking) — long view of the pipeline
    # ---------------------------------------------------------------------------

    if not lehs_y2_all.empty:
        st.header("Pipeline Trend — Multiple 9th-grade Cohorts")
        st.caption(
            "Each line is a stage of the pipeline as it has moved over time. "
        "Cohorts graduating 2020–2024 were disrupted as 8th–10th graders; "
        "expect noisier patterns for those years."
        )

        trend_all = lehs_prog[
            (lehs_prog["INDICATOR"] == YEAR2_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
        ].sort_values("COHORTYR").copy()
        trend_all["grad_pct"] = trend_all["GRAD_CNT"] / trend_all["COHORT_CNT"]
        trend_all["enr_pct"] = trend_all["IMMEDIATEENR_CNT"] / trend_all["COHORT_CNT"]
        trend_all["pers_pct"] = trend_all["PERSIST_CNT"] / trend_all["COHORT_CNT"]

        trend_long = trend_all.melt(
            id_vars=["COHORTYR"],
            value_vars=["grad_pct", "enr_pct", "pers_pct"],
            var_name="stage", value_name="pct",
        ).dropna(subset=["pct"])
        trend_long["stage"] = trend_long["stage"].map({
            "grad_pct": "Graduated",
            "enr_pct": "Enrolled in college",
            "pers_pct": "Persisted to year 2",
        })

        fig = px.line(
            trend_long, x="COHORTYR", y="pct", color="stage", markers=True,
            color_discrete_map={
                "Graduated":            "#90A4AE",
                "Enrolled in college":  LEHS_NAVY,
                "Persisted to year 2":  LEHS_GOLD,
            },
            category_orders={"stage": ["Graduated", "Enrolled in college", "Persisted to year 2"]},
        )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_tickformat=".0%",
            yaxis_title="Share of 9th-grade cohort",
            xaxis_title="Graduation cohort year",
            legend_title="",
        )
        if not trend_long.empty:
            fig.update_yaxes(range=[0, max(trend_long["pct"].max() * 1.1, 1.0)])
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

        # ---------------------------------------------------------------------------
        # Six-year degree completion
        # ---------------------------------------------------------------------------

        st.subheader("Degree Completion — 6-Year View")
        st.caption(
            "Following cohorts six years past HS graduation: how many actually "
        "completed a 2-yr or 4-yr degree?"
        )

        lehs_deg = lehs_prog[
            (lehs_prog["INDICATOR"] == DEGREE_INDICATOR) & (lehs_prog["STU_GRP"] == "All Students")
        ].sort_values("COHORTYR")

        if not lehs_deg.empty:
            latest_deg = lehs_deg.iloc[-1]
            deg_year = int(latest_deg["COHORTYR"])
            deg_pct = latest_deg["OBTAINDEGREE_PCT"]
            if pd.notna(deg_pct):
                st.metric(
                    f"Obtained a postsecondary degree ({deg_year - 4}–{deg_year} cohort)",
                    f"{deg_pct:.0%}",
                    help="Share of the 9th-grade cohort that completed a 2-yr or 4-yr degree within ~6 years of HS graduation.",
                )

            deg_trend = lehs_deg.dropna(subset=["OBTAINDEGREE_PCT"]).copy()
            if len(deg_trend) >= 2:
                fig = px.line(deg_trend, x="COHORTYR", y="OBTAINDEGREE_PCT", markers=True)
                fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickformat=".0%",
                    yaxis_title="Share of cohort obtaining a degree",
                    xaxis_title="Cohort year",
                )
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")
        else:
            st.caption("6-year degree-completion data not available for LEHS yet.")

        st.divider()

    # ---------------------------------------------------------------------------
    # Earnings of HS graduates by industry (district-level)
    # ---------------------------------------------------------------------------

    st.header("Earnings of Lynn HS Graduates — Industry View")
    st.caption(
        "DESE's *Average Earnings of HS Graduates by Industry* dataset follows "
    "every Lynn-district HS graduate's W-2 earnings by NAICS industry. "
    "Reported at the district level, so this includes graduates of LEHS, "
    "Classical, Tech, and the alternative HS combined."
    )

    earnings = load_dataset("earnings_by_industry")
    if not earnings.empty:
        e_lynn = earnings[earnings["DIST_CODE"] == "01630000"].copy()
        e_lynn["AVG_EARNINGS"] = pd.to_numeric(e_lynn["AVG_EARNINGS"], errors="coerce")
        e_lynn["EMP_CNT"] = pd.to_numeric(e_lynn["EMP_CNT"], errors="coerce")
        e_lynn["GRAD_CNT"] = pd.to_numeric(e_lynn["GRAD_CNT"], errors="coerce")

        headline = e_lynn[
            (e_lynn["NAICS_DESC"] == "All Students")
            & (e_lynn["HS_GRAD_YEAR"] == e_lynn["EARNINGS_YEAR"])
        ].dropna(subset=["AVG_EARNINGS"]).sort_values("HS_GRAD_YEAR")

        if not headline.empty:
            latest = headline.iloc[-1]
            prior = headline.iloc[-2] if len(headline) > 1 else None
            c1, c2 = st.columns([1, 3])
            with c1:
                st.metric(
                    f"Avg earnings in year of HS graduation "
                f"({int(latest['HS_GRAD_YEAR'])} cohort)",
                    f"${latest['AVG_EARNINGS']:,.0f}",
                    (f"${latest['AVG_EARNINGS']-prior['AVG_EARNINGS']:+,.0f} "
                 f"vs {int(prior['HS_GRAD_YEAR'])}") if prior is not None else "",
                    delta_color="off",
                )
                st.caption(
                    f"Earned by **{int(latest['EMP_CNT']):,}** of "
                f"{int(latest['GRAD_CNT']):,} graduates with reported wages."
                )
            with c2:
                fig = px.line(headline, x="HS_GRAD_YEAR", y="AVG_EARNINGS", markers=True)
                fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickformat="$,.0f",
                    yaxis_title="Average wages in grad year",
                    xaxis_title="High-school graduation cohort",
                )
                year_axis(fig)
                st.plotly_chart(fig, width="stretch")

        if not e_lynn.empty:
            latest_year_e = e_lynn["HS_GRAD_YEAR"].max()
            industries = e_lynn[
                (e_lynn["HS_GRAD_YEAR"] == latest_year_e)
                & (e_lynn["EARNINGS_YEAR"] == latest_year_e)
                & (e_lynn["NAICS_DESC"] != "All Students")
                & (e_lynn["EMP_CNT"].notna())
            ].sort_values("EMP_CNT", ascending=True)
            if not industries.empty:
                st.subheader(
                    f"Where the cohort works — {int(latest_year_e)} graduates "
                f"with reported wages in their grad year"
                )
                st.caption(
                    "Industries with too few graduates (<6) are suppressed by "
                "DESE. The chart below shows only those above that threshold."
                )
                industries["earnings_label"] = industries["AVG_EARNINGS"].apply(
                    lambda x: f"${x:,.0f}" if pd.notna(x) else "—"
                )
                fig = px.bar(
                    industries, y="NAICS_DESC", x="EMP_CNT", orientation="h",
                    color="AVG_EARNINGS", color_continuous_scale="Greens",
                    text=industries["EMP_CNT"].astype(int).astype(str) + " grads",
                    hover_data={"AVG_EARNINGS": ":$,.0f", "GRAD_CNT": True},
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    xaxis_title="Number of graduates employed",
                    xaxis_range=[0, industries["EMP_CNT"].max() * 1.18],
                    yaxis_title="",
                    coloraxis_colorbar=dict(title="Avg $/yr"),
                    height=400,
                )
                st.plotly_chart(fig, width="stretch")
    else:
        st.caption("Earnings data not yet loaded.")

    st.divider()

    # ---------------------------------------------------------------------------
    # Early warning chain
    # ---------------------------------------------------------------------------

    st.header("Early Warning Chain")
    st.caption(
        "These four indicators form a cascade: a student who chronically misses 9th "
    "grade is unlikely to be promoted, less likely to graduate on time, and far "
    "less likely to enroll in college. Tracking them together highlights where "
    "interventions have leverage."
    )

    chain_indicators = [
        ("Chronically absent rate (% of students absent 10% or more each year)", "Chronic Absence"),
        ("9th to 10th grade promotion rate (first-time 9th graders only)", "9-10 Promotion"),
        ("4-year cohort graduation rate", "4-yr Graduation"),
        ("Students enrolled in postsecondary education in the immediate fall after high school graduation",
         "Immediate College"),
    ]

    chain_df = pd.concat([
        get_dart_indicator(LEHS_SCHOOL_CODE, ind).assign(Stage=label)
        for ind, label in chain_indicators
    ])

    if not chain_df.empty:
        _chain_g = with_year_gaps(
            chain_df, "VALUE", group_col="Stage", years=span_years(chain_df),
        )
        fig = px.line(
            _chain_g.sort_values("SY"), x="SY", y="VALUE", color="Stage", markers=True,
            color_discrete_map={
                "Chronic Absence":      "#E89B9B",
                "9-10 Promotion":       "#E0C079",
                "4-yr Graduation":      LEHS_NAVY,
                "Immediate College":    "#9CCFC4",
            },
        )
        fig.update_traces(connectgaps=False)
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Rate (%)",
                           yaxis_ticksuffix="%", yaxis_range=[0, 100])
        year_axis(fig)
        st.plotly_chart(fig, width="stretch")

    with st.expander("How to read this page · methodology"):
        st.markdown(
            """
- **Cohort** means the group of students who first entered 9th grade together,
  not the graduating class. A 2023 cohort started 9th grade around 2019.
- **Immediate enrollment** is in college the fall immediately after HS graduation.
- **Persisted to year 2** = still enrolled in college one year after immediate
  enrollment. Strongest single predictor of degree completion.
- **Stage percentages** in the cohort funnel are always relative to the original
  9th-grade cohort, not to the previous stage.
- **DESE suppression**: cells under 10 students are blanked.
- **Source**: MA DESE Education-to-Career Hub — DART (Success After HS),
  Graduation Rates, Student Progression HS→Postsec, Plans of Graduates,
  Earnings by Industry.
"""
        )

    # >>> auto: csv downloads <<<
    try:
        from utils.charts import data_downloads_panel as _dl
        _dl({
            'DART (Success After HS)': dart,
            'Graduation rates': grad,
            'Plans of graduates': plans,
            'Cohort progression (9th-grade → degree)': prog,
        })
    except NameError:
        pass

page_footer()
