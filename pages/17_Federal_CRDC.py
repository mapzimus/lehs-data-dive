"""Section 17 — Federal CRDC (Civil Rights Data Collection)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, GATEWAY_PEER_COLOR, LEHS_GOLD, LEHS_NAVY
from utils.constants import LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset

st.set_page_config(page_title="Federal CRDC | LEHS", page_icon="📊", layout="wide")
sidebar_attribution()

# The school-name CRDC carries for Lynn English High (no DESE ORG_CODE in CRDC).
LEHS_CRDC_NAME = "Lynn English High"
SIBLING_NAMES = ["Lynn English High", "Classical High",
                 "Lynn Vocational Technical Institute"]

st.title("Federal CRDC — Civil Rights Data Collection")
st.markdown(
    "The CRDC is a biennial federal collection from the U.S. Department of "
    "Education's Office for Civil Rights. It captures things the state datasets "
    "don't: school-based arrests, law-enforcement referrals, restraint and "
    "seclusion, AP/IB course offerings, and support-staff counts. This page "
    "shows the most recent public-use release, **school year 2021-22**, for "
    "Lynn English High and its same-district peers."
)
st.caption(
    "Source: U.S. Dept. of Education, Office for Civil Rights — 2021-22 CRDC "
    "public-use file (civilrightsdata.ed.gov). **Caveats:** 2021-22 was a "
    "pandemic-recovery year, so counts may not reflect typical patterns; and "
    "the public-use file applies small random perturbations and suppresses very "
    "small cells to protect student privacy, so subgroup counts are approximate "
    "and may not sum exactly to totals."
)

discipline = load_dataset("crdc_discipline")
offerings = load_dataset("crdc_offerings")
staffing = load_dataset("crdc_staffing")

if discipline.empty and offerings.empty and staffing.empty:
    st.info(
        "CRDC parquet files are scaffolded but empty — run "
        "`python scripts/04_download_crdc.py` to download the 2021-22 federal "
        "release and build them. See data/raw/crdc/README.md if the headless "
        "download cannot complete."
    )
    st.markdown(
        "When populated, this page surfaces:\n"
        "- **Support-staff ratios** — counselors / nurses / social workers / "
        "psychologists per student vs. professional recommendations.\n"
        "- **AP / IB & advanced-course offerings** — what each Lynn school "
        "actually offers (a key equity-of-access measure).\n"
        "- **Discipline disaggregated** by race, disability, and English-learner "
        "status (in/out-of-school suspension, expulsion, arrest, referral)."
    )
    st.stop()


def _lehs_row(df: pd.DataFrame) -> pd.Series | None:
    if df.empty or "SCHOOL_NAME" not in df.columns:
        return None
    hit = df[df["SCHOOL_NAME"].astype(str).str.strip() == LEHS_CRDC_NAME]
    return hit.iloc[0] if not hit.empty else None


# ---------------------------------------------------------------------------
# Support staffing
# ---------------------------------------------------------------------------
st.divider()
st.header("Support-staff ratios")
st.caption(
    "Full-time-equivalent (FTE) school counselors, nurses, social workers, and "
    "psychologists, from the 2021-22 CRDC. The American School Counselor "
    "Association recommends one counselor for every 250 students."
)

if not staffing.empty:
    staff = staffing.copy()
    for c in ("COUNSELOR_FTE", "NURSE_FTE", "SOCIAL_WORKER_FTE",
              "PSYCHOLOGIST_FTE", "LAW_ENFORCEMENT_FTE", "TEACHER_FTE",
              "STUDENT_ENROLLMENT"):
        if c in staff.columns:
            staff[c] = pd.to_numeric(staff[c], errors="coerce")

    lehs = _lehs_row(staff)
    if lehs is not None and pd.notna(lehs.get("STUDENT_ENROLLMENT")) and lehs["STUDENT_ENROLLMENT"] > 0:
        enr = float(lehs["STUDENT_ENROLLMENT"])
        c1, c2, c3, c4 = st.columns(4)

        def _ratio(fte):
            return f"{enr / fte:,.0f} : 1" if pd.notna(fte) and fte else "—"

        c1.metric("Students per counselor", _ratio(lehs.get("COUNSELOR_FTE")),
                  help="ASCA recommends 250 : 1.")
        c2.metric("Students per nurse", _ratio(lehs.get("NURSE_FTE")))
        c3.metric("Students per social worker", _ratio(lehs.get("SOCIAL_WORKER_FTE")))
        c4.metric("Students per psychologist", _ratio(lehs.get("PSYCHOLOGIST_FTE")))

    # Same-district comparison: students per counselor at the three big HS.
    sib = staff[staff["SCHOOL_NAME"].isin(SIBLING_NAMES)].copy()
    sib = sib[(sib["STUDENT_ENROLLMENT"] > 0) & (sib["COUNSELOR_FTE"] > 0)]
    if not sib.empty:
        sib["per_counselor"] = sib["STUDENT_ENROLLMENT"] / sib["COUNSELOR_FTE"]
        sib = sib.sort_values("per_counselor")
        colors = [LEHS_NAVY if n == LEHS_CRDC_NAME else GATEWAY_PEER_COLOR
                  for n in sib["SCHOOL_NAME"]]
        fig = go.Figure(go.Bar(
            x=sib["per_counselor"], y=sib["SCHOOL_NAME"], orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f} : 1" for v in sib["per_counselor"]],
            textposition="auto",
        ))
        fig.add_vline(x=250, line_dash="dash", line_color=LEHS_GOLD,
                      annotation_text="ASCA 250:1", annotation_position="top")
        fig.update_layout(**DEFAULT_LAYOUT,
                          title="Students per school counselor — Lynn high schools",
                          xaxis_title="Students per counselor FTE")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Support-staff data is unavailable in the current build.")

# ---------------------------------------------------------------------------
# Course offerings
# ---------------------------------------------------------------------------
st.divider()
st.header("Advanced course offerings & access")
st.caption(
    "Whether each Lynn school offers AP, IB, and gatekeeper advanced courses, "
    "plus how many students are enrolled in AP. What a school *offers* is a "
    "civil-rights measure of equitable access to college-level coursework."
)

if not offerings.empty:
    off = offerings.copy()
    for c in ("AP_COURSE_COUNT", "AP_ENROLLED_TOTAL"):
        if c in off.columns:
            off[c] = pd.to_numeric(off[c], errors="coerce")

    lehs_o = _lehs_row(off)
    if lehs_o is not None:
        c1, c2, c3 = st.columns(3)
        ap_courses = lehs_o.get("AP_COURSE_COUNT")
        ap_enr = lehs_o.get("AP_ENROLLED_TOTAL")
        c1.metric("LEHS — distinct AP courses",
                  f"{int(ap_courses)}" if pd.notna(ap_courses) else "—")
        c2.metric("LEHS — students enrolled in AP",
                  f"{int(ap_enr):,}" if pd.notna(ap_enr) else "—")
        offered = [lbl for lbl, col in (("IB", "IB_OFFERED"), ("Calculus", "CALC_OFFERED"),
                                        ("Physics", "PHYSICS_OFFERED"),
                                        ("Geometry", "GEO_OFFERED"),
                                        ("Algebra II", "ALGEBRA_II_OFFERED"))
                   if str(lehs_o.get(col)).strip().lower() == "yes"]
        c3.metric("LEHS — advanced courses offered",
                  f"{len(offered) + (1 if str(lehs_o.get('AP_OFFERED')).lower() == 'yes' else 0)}")

    # AP enrollment across the district's high schools.
    ap_df = off[off["AP_ENROLLED_TOTAL"].notna() & (off["AP_ENROLLED_TOTAL"] > 0)].copy()
    if not ap_df.empty:
        ap_df = ap_df.sort_values("AP_ENROLLED_TOTAL", ascending=True)
        colors = [LEHS_NAVY if n == LEHS_CRDC_NAME else GATEWAY_PEER_COLOR
                  for n in ap_df["SCHOOL_NAME"]]
        fig = go.Figure(go.Bar(
            x=ap_df["AP_ENROLLED_TOTAL"], y=ap_df["SCHOOL_NAME"], orientation="h",
            marker_color=colors,
            text=[f"{int(v):,}" for v in ap_df["AP_ENROLLED_TOTAL"]],
            textposition="auto",
        ))
        fig.update_layout(**DEFAULT_LAYOUT,
                          title="Students enrolled in AP — Lynn high schools (2021-22)",
                          xaxis_title="AP-enrolled students")
        st.plotly_chart(fig, use_container_width=True)

    # Offering matrix (Yes/No) for the schools that offer any advanced course.
    flag_cols = ["AP_OFFERED", "IB_OFFERED", "CALC_OFFERED", "PHYSICS_OFFERED",
                 "GEO_OFFERED", "ALGEBRA_II_OFFERED"]
    have_flags = [c for c in flag_cols if c in off.columns]
    matrix = off[off[have_flags].apply(
        lambda r: (r.astype(str).str.lower() == "yes").any(), axis=1)]
    if not matrix.empty:
        nice = {"AP_OFFERED": "AP", "IB_OFFERED": "IB", "CALC_OFFERED": "Calculus",
                "PHYSICS_OFFERED": "Physics", "GEO_OFFERED": "Geometry",
                "ALGEBRA_II_OFFERED": "Algebra II"}
        show = matrix[["SCHOOL_NAME"] + have_flags].rename(columns={"SCHOOL_NAME": "School", **nice})
        st.markdown("**Advanced-course offering matrix**")
        st.dataframe(show, use_container_width=True, hide_index=True)
else:
    st.info("Course-offering data is unavailable in the current build.")

# ---------------------------------------------------------------------------
# Discipline
# ---------------------------------------------------------------------------
st.divider()
st.header("Discipline, disaggregated")
st.caption(
    "Out-of-school suspension counts at Lynn English High by student group, from "
    "the 2021-22 CRDC. The federal collection's signature feature is its "
    "race / disability / English-learner breakdown. **Small-n caution:** "
    "these are raw, privacy-perturbed counts (not rates); subgroup figures are "
    "approximate and small cells may be suppressed."
)

if not discipline.empty:
    disc = discipline.copy()
    metric_cols = ["ISS_COUNT", "OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT",
                   "EXPULSION_COUNT", "ARREST_COUNT", "LE_REFERRAL_COUNT",
                   "RESTRAINT_PHYSICAL", "SECLUSION_COUNT"]
    for c in metric_cols:
        if c in disc.columns:
            disc[c] = pd.to_numeric(disc[c], errors="coerce")

    lehs_d = disc[disc["SCHOOL_NAME"].astype(str).str.strip() == LEHS_CRDC_NAME]
    race = lehs_d[(lehs_d["GROUP_DIM"] == "race")].copy()
    race["TOTAL_OSS"] = race[["OSS_SINGLE_COUNT", "OSS_MULTIPLE_COUNT"]].sum(axis=1, min_count=1)
    race = race[race["TOTAL_OSS"].fillna(0) > 0].sort_values("TOTAL_OSS")
    if not race.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Suspended once",
                             x=race["OSS_SINGLE_COUNT"], y=race["GROUP"],
                             orientation="h", marker_color=LEHS_NAVY))
        fig.add_trace(go.Bar(name="Suspended more than once",
                             x=race["OSS_MULTIPLE_COUNT"], y=race["GROUP"],
                             orientation="h", marker_color=LEHS_GOLD))
        fig.update_layout(**DEFAULT_LAYOUT, barmode="stack",
                          title="LEHS out-of-school suspensions by race/ethnicity (2021-22)",
                          xaxis_title="Students")
        st.plotly_chart(fig, use_container_width=True)

    # All-students summary across discipline measures (LEHS).
    tot = lehs_d[lehs_d["GROUP_DIM"] == "total"]
    if not tot.empty:
        row = tot.iloc[0]
        labels = {"ISS_COUNT": "In-school suspension",
                  "OSS_SINGLE_COUNT": "Out-of-school (once)",
                  "OSS_MULTIPLE_COUNT": "Out-of-school (multiple)",
                  "EXPULSION_COUNT": "Expulsions",
                  "ARREST_COUNT": "School-based arrests",
                  "LE_REFERRAL_COUNT": "Referrals to law enforcement"}
        summary = pd.DataFrame(
            {"Measure": list(labels.values()),
             "LEHS students (all groups)": [row.get(k) for k in labels]}
        )
        st.markdown("**LEHS discipline summary — all students**")
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with st.expander("Full discipline table (all schools × student groups)"):
        st.dataframe(disc, use_container_width=True, height=400)
else:
    st.info("Discipline data is unavailable in the current build.")

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

page_footer()
