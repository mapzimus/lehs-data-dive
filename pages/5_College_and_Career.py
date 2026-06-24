"""Section 5 — College & Career: pathways, Early College, FAFSA, outcomes.

AP, SAT, MassCore, advanced-coursework, and course-access content moved to
Courses & Academics (pages/2b_Courses_and_Academics.py) — this page now
covers the *pathway and post-graduation* story: designated pathway programs,
Early College participation and credits, FAFSA completion, and where Lynn
graduates actually land.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, data_downloads_panel
from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import get_dart_indicator, load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="College & Career | LEHS", page_icon="🎓", layout="wide")
sidebar_attribution()

st.title("College & Career Readiness")
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
        PATHWAY_LABELS = {
            "Early College": "Early College",
            "Career Technical Education (Chapter 74 Programs)": "Career Tech Ed (Ch. 74)",
            "After Dark": "After Dark (evening CTE)",
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
                    "After Dark (evening CTE)": "#7B9E89",
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
                "those two bars count the same students."
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
    "earn each year, broken out by partner CEEB college. Source: "
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
            ec_agg["pass_rate"] = ec_agg["EARNED_CREDIT_CNT"] / ec_agg["REG_CREDITS_CNT"]
            fig = px.bar(
                ec_agg, y="CEEB_NAME", x="EARNED_CREDIT_CNT", orientation="h",
                color="pass_rate", color_continuous_scale="Greens",
                hover_data={"STU_CNT": True, "REG_CREDITS_CNT": True, "pass_rate": ":.0%"},
                text=ec_agg["EARNED_CREDIT_CNT"].astype(int).astype(str),
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(
                **DEFAULT_LAYOUT,
                height=max(280, 36 * len(ec_agg)),
                xaxis_title="Credits earned",
                xaxis_range=[0, ec_agg["EARNED_CREDIT_CNT"].max() * 1.15],
                yaxis_title="",
                coloraxis_colorbar=dict(title="Pass rate"),
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

page_footer()
