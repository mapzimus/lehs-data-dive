"""
Section 3 — English Learners.

The central narrative thread: tracking English Learner outcomes from initial
proficiency through MCAS and into the years after reclassification.
"""

import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY, SUBGROUP_PALETTE
from utils.constants import LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE, PROCESSED_DIR
from utils.data_loader import load_dataset
from utils.interpret import sy_label

st.set_page_config(page_title="ELL Pipeline | LEHS", page_icon="🌐", layout="wide")
sidebar_attribution()

st.title("English Learners")
st.markdown(
    "Lynn serves one of the highest concentrations of English Learners in "
    "Massachusetts. This section follows EL students from initial ACCESS "
    "scores through MCAS and into the years after they reclassify."
)

enrollment = load_dataset("enrollment_demographics")
mcas = load_dataset("mcas_achievement")
if enrollment.empty or mcas.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# ELL enrollment share over time
# ---------------------------------------------------------------------------

st.header("How big is the EL population at LEHS?")

lehs_enroll = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY").copy()
current = lehs_enroll.iloc[-1]

enroll_sy_lbl = sy_label(int(current["SY"]))
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric(f"LEHS ELL count (enrolled, SY {enroll_sy_lbl})", f"{int(current['EL_CNT']):,}")
with c2:
    st.metric("LEHS % English Learner", f"{current['EL_PCT']:.0%}")
with c3:
    st.metric("% First Language Not English", f"{current['FLNE_PCT']:.0%}")
with c4:
    st.metric("% Hispanic/Latino", f"{current['HL_PCT']:.0%}")

st.caption(
    f"**Two EL counts appear on this page.** The **{int(current['EL_CNT']):,} enrolled** "
    "figure above counts students currently flagged as English Learners. "
    "The ACCESS section below reports a different number — students who sat the "
    "ACCESS test that spring — so the two figures measure different populations "
    "and will not match."
)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=lehs_enroll["SY"], y=lehs_enroll["EL_PCT"], mode="lines+markers",
    name="Lynn English",
    line=dict(color=SUBGROUP_PALETTE["English Learner"], width=3),
))
fig.update_layout(
    **DEFAULT_LAYOUT,
    title="English Learner share — Lynn English, 1992-present",
    yaxis_tickformat=".0%",
    yaxis_title="% English Learner",
    xaxis_title="School Year",
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "The EL share at LEHS has more than doubled since the early 2000s — a "
    "dramatic shift in who the school serves and what supports are required. "
    "For cross-school comparison, see "
    "[Lynn Schools](/Lynn_Schools?embed=true) (Compare group)."
)

st.divider()

# ---------------------------------------------------------------------------
# WIDA ACCESS statewide context
# ---------------------------------------------------------------------------

st.header("WIDA ACCESS — Statewide Context (2025)")
st.caption(
    "ACCESS for ELLs is the annual English language proficiency assessment. "
    "Statewide aggregates from MA DESE's WIDA report are shown below; "
    "school- and district-level outcomes for Lynn and LEHS follow in the next section."
)

wida_path = PROCESSED_DIR / "wida_state_summary.json"
if wida_path.exists():
    wida = json.loads(wida_path.read_text())
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("MA ELs enrolled K-12", f"{wida['total_ell_k12_enrolled']:,}")
    with c2:
        st.metric("Participation rate", f"{wida['participation_rate']:.0%}")
    with c3:
        st.metric("Met reclassification criteria", f"{wida['reclassification']['pct_meeting_criteria']:.1%}")
    with c4:
        st.metric("Avg listening score", f"{wida['avg_proficiency']['listening']:.1f}")

    prof = wida["avg_proficiency"]
    prof_df = pd.DataFrame({
        "Domain": ["Speaking", "Writing", "Reading", "Listening"],
        "Avg Score": [prof["speaking"], prof["writing"], prof["reading"], prof["listening"]],
    })
    fig = go.Figure(go.Bar(
        x=prof_df["Domain"], y=prof_df["Avg Score"],
        text=prof_df["Avg Score"].round(1), textposition="outside",
        textfont=dict(size=13, color="#0A1F44"),
        marker_color=SUBGROUP_PALETTE["English Learner"],
        cliponaxis=False,
    ))
    fig.update_layout(
        **DEFAULT_LAYOUT,
        title="MA statewide avg WIDA score by domain (2025)",
        yaxis=dict(title="Score (1-6)", range=[0, 6.5]),
    )
    # Widen right margin so the threshold-line annotation has room
    fig.update_layout(margin=dict(l=40, r=220, t=50, b=40))
    # Reference line — the 4.2 cutoff applies to a student's OVERALL composite
    # ACCESS score, not to any single domain, so label it as such. Drawing it
    # across the per-domain bars is for orientation only (apples-to-oranges
    # otherwise). Keep the annotation BELOW the line so it doesn't collide with
    # the "4.1" bar-value label sitting just above the Listening bar.
    fig.add_hline(
        y=4.2, line_dash="dash", line_color="gray",
        annotation_text="Overall composite cutoff (4.2) — not a per-domain target",
        annotation_position="bottom right",
        annotation_font=dict(size=11, color="gray"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Bars show the **average score in each domain**. The dashed line marks "
        "the **4.2 overall-composite** cutoff DESE uses for reclassification — a "
        "student is evaluated on their combined score, so a single domain "
        "sitting above or below 4.2 doesn't by itself reclassify anyone."
    )

st.divider()

# ---------------------------------------------------------------------------
# ACCESS outcomes — Lynn & LEHS (DESE E2C reporting elements, puw9-zucz)
# ---------------------------------------------------------------------------

st.header("ACCESS for ELLs — Lynn & LEHS outcomes")
st.caption(
    "The three Title III reporting elements DESE publishes each year: the share "
    "of ELs **making progress** toward English proficiency (RE1), the share who "
    "**attained proficiency** (RE2), and the share who **exited** EL status (RE3). "
    "School- and district-level values, pulled from the DESE E2C hub (puw9-zucz)."
)

el = load_dataset("el_access")
if el.empty:
    st.info("ACCESS reporting-element data is temporarily unavailable.")
else:
    el = el[el["GRADE"] == "ALL"].dropna(subset=["SY"]).copy()
    el["SY"] = el["SY"].astype(int)
    lehs_el = el[el["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY")
    lynn_el = el[(el["DIST_CODE"] == LYNN_DISTRICT_CODE)
                 & (el["ORG_TYPE"] == "District")].sort_values("SY")
    state_el = el[el["ORG_TYPE"] == "State"].sort_values("SY")

    if not lehs_el.empty:
        cur = lehs_el.iloc[-1]
        sy_lbl = f"{int(cur['SY']) - 1}-{str(int(cur['SY']))[-2:]}"
        st.markdown(f"**Lynn English High — SY {sy_lbl}**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("ELs assessed (ACCESS)", f"{int(cur['ENROLLED_CNT']):,}")
        c2.metric("Making progress (RE1)", f"{cur['RE1_PCT']:.0%}")
        c3.metric("Attained proficiency (RE2)", f"{cur['RE2_PCT']:.0%}")
        c4.metric("Exited EL status (RE3)", f"{cur['RE3_PCT']:.0%}")

    # RE1 (making progress) trend — LEHS vs Lynn district vs Massachusetts.
    color_map = {
        "Lynn English": SUBGROUP_PALETTE["English Learner"],
        "Lynn district": LEHS_NAVY,
        "Massachusetts": "#A8B5BD",
    }
    frames = []
    for d, name in [(lehs_el, "Lynn English"),
                    (lynn_el, "Lynn district"),
                    (state_el, "Massachusetts")]:
        if not d.empty:
            t = d[["SY", "RE1_PCT"]].copy()
            t["Series"] = name
            frames.append(t)
    if frames:
        tdf = pd.concat(frames, ignore_index=True).dropna(subset=["RE1_PCT"])
        fig = px.line(tdf, x="SY", y="RE1_PCT", color="Series", markers=True,
                      color_discrete_map=color_map)
        fig.update_layout(
            **DEFAULT_LAYOUT,
            title="ELs making progress toward English proficiency (ACCESS RE1)",
            yaxis_tickformat=".0%",
            yaxis_title="% making progress",
            xaxis_title="School Year",
        )
        st.plotly_chart(fig, use_container_width=True)

        # ----- Honest callout: LEHS RE1 sits far below district + state -----
        # Pull the most recent year shared across all three series.
        def _latest_pct(frame, col):
            f = frame[["SY", col]].dropna()
            return (int(f.iloc[-1]["SY"]), float(f.iloc[-1][col])) if not f.empty else (None, None)

        lehs_yr, lehs_re1 = _latest_pct(lehs_el, "RE1_PCT")
        _, lynn_re1 = _latest_pct(lynn_el, "RE1_PCT")
        _, state_re1 = _latest_pct(state_el, "RE1_PCT")
        if None not in (lehs_re1, lynn_re1, state_re1):
            yr_lbl = sy_label(lehs_yr)
            st.warning(
                f"**LEHS's RE1 runs far below its district and the state, every "
                f"year on record.** In SY {yr_lbl} only **{lehs_re1:.0%}** of "
                f"LEHS English Learners were credited with making progress toward "
                f"proficiency, against **{lynn_re1:.0%}** district-wide and "
                f"**{state_re1:.0%}** statewide — a gap of roughly "
                f"{round((state_re1 - lehs_re1) * 100)} percentage points below "
                "the state. A gap this large and this persistent is worth taking "
                "seriously as a real instructional concern. It can also be "
                "inflated by cohort and reporting nuances at the high-school "
                "level — RE1 is only defined for students who took ACCESS in two "
                "consecutive years, so a school with heavy mid-year mobility or "
                "many newly-arrived ELs has a smaller, choppier denominator. "
                "Either way the pattern warrants a closer look, not a footnote."
            )

        # ----- Companion RE2 (attained proficiency) trend -----
        re2_frames = []
        for d, name in [(lehs_el, "Lynn English"),
                        (lynn_el, "Lynn district"),
                        (state_el, "Massachusetts")]:
            if not d.empty:
                t = d[["SY", "RE2_PCT"]].copy()
                t["Series"] = name
                re2_frames.append(t)
        if re2_frames:
            r2 = pd.concat(re2_frames, ignore_index=True).dropna(subset=["RE2_PCT"])
            if not r2.empty:
                fig2 = px.line(r2, x="SY", y="RE2_PCT", color="Series", markers=True,
                               color_discrete_map=color_map)
                fig2.update_layout(
                    **DEFAULT_LAYOUT,
                    title="ELs attaining English proficiency (ACCESS RE2)",
                    yaxis_tickformat=".0%",
                    yaxis_title="% attaining proficiency",
                    xaxis_title="School Year",
                )
                st.plotly_chart(fig2, use_container_width=True)
                st.caption(
                    "RE2 — the share **attaining** proficiency outright — is a "
                    "higher bar than RE1 and runs lower everywhere. LEHS trails "
                    "its district and the state here too, consistent with the "
                    "RE1 picture above."
                )

    st.caption(
        "RE1 (making progress) is the workhorse Title III accountability metric. "
        "RE3 (exiting) runs high because most ELs who clear the overall ACCESS "
        "threshold are reclassified that same year."
    )

st.divider()

# ---------------------------------------------------------------------------
# LEHS MCAS: ELL vs Former EL vs All Students
# ---------------------------------------------------------------------------

st.header("MCAS Grade 10 — EL Pipeline at LEHS")

mcas_lehs = mcas[(mcas["ORG_CODE"] == LEHS_SCHOOL_CODE) & (mcas["TEST_GRADE"] == "10")].copy()
mcas_lehs["STU_GRP"] = mcas_lehs["STU_GRP"].str.replace("\xa0", " ", regex=False)

ell_groups = ["All Students", "English Learners", "Former English Learners", "Ever English Learners"]
sub = mcas_lehs[mcas_lehs["STU_GRP"].isin(ell_groups)].copy()

color_map = {
    "All Students":             LEHS_NAVY,
    "English Learners":         SUBGROUP_PALETTE["English Learner"],
    "Former English Learners":  SUBGROUP_PALETTE["Former English Learner"],
    "Ever English Learners":    "#FFB300",
}

from utils.stats import subgroup_summary_md  # noqa: E402

for subject_code, subject_label in [("ELA", "English Language Arts"), ("MATH", "Mathematics")]:
    st.subheader(f"Grade 10 {subject_label} — % Meeting or Exceeding")
    d = sub[sub["SUBJECT_CODE"] == subject_code].sort_values("SY")
    if d.empty:
        st.info(f"No {subject_label} data.")
        continue
    fig = px.line(
        d, x="SY", y="M_PLUS_E_PCT", color="STU_GRP", markers=True,
        color_discrete_map=color_map,
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        yaxis_tickformat=".0%",
        yaxis_title="% Meeting + Exceeding",
        xaxis_title="School Year",
    )
    # Former English Learners is a tiny subgroup (n ≈ 12-25 each year) that
    # reconstitutes with different students annually, so its line swings on a
    # one- or two-student basis and its CIs run 20-50 pp wide. Default it to
    # legend-only so the chart leads with the subgroups whose year-to-year
    # movement is interpretable; readers can click it on in the legend.
    fig.update_traces(visible="legendonly",
                      selector=dict(name="Former English Learners"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "**Former English Learners is hidden by default — click it in the "
        "legend to show it.** That subgroup is small (n ≈ 12-25 each year) and "
        "reconstitutes with different students annually, so its line swings on "
        "a one- or two-student basis (a single student is worth ~4-8 points) "
        "and its 95% confidence intervals run 20-50 points wide every year. "
        "Read its position as noise, not trend. **Ever English Learners** "
        "(n ≈ 274) is the stable subgroup to follow for EL-pipeline outcomes."
    )

    # Statistical summary for the latest year — gives the line chart context
    # that DESE's bare percentages don't: how wide is the uncertainty around
    # each subgroup, and is the EL-vs-All gap a real effect?
    latest = d[d["SY"] == d["SY"].max()].copy()
    if not latest.empty:
        summary = subgroup_summary_md(
            latest,
            group_col="STU_GRP",
            pct_col="M_PLUS_E_PCT",
            n_col="STU_CNT",
            reference_group="All Students",
            group_order=ell_groups,
            title=f"SY {int(d['SY'].max()) - 1}-{str(int(d['SY'].max()))[-2:]} snapshot — "
                  f"point estimates with 95% Wilson CIs",
        )
        if summary:
            st.markdown(summary)

st.divider()

# ---------------------------------------------------------------------------
# Former EL by years post-exit (from reporting-element4.xlsx)
# ---------------------------------------------------------------------------

st.header("Former English Learners — by Year Since Exit (Lynn District)")
st.caption(
    "DESE Reporting Element 4 tracks former EL students for up to 4 years "
    "after they exit EL status. Data shown is **Lynn district aggregate** for 2025."
)

fmr_path = PROCESSED_DIR / "former_el_mcas_lynn.csv"
if fmr_path.exists():
    fmr = pd.read_csv(fmr_path)

    if not fmr.empty:
        # Coerce % columns to numeric (they're strings from xlsx)
        for col in ["ELA  E+M %", "Math  E+M %", "STE  E+M %",
                    "ELA Tested #", "Math Tested #", "STE Tested #"]:
            if col in fmr.columns:
                fmr[col] = pd.to_numeric(fmr[col], errors="coerce")

        # Filter to FormerEL group (excludes IEP-only subgroup) and grades 3-8 + g10
        target = fmr[
            (fmr["Group"] == "FormerEL")
            & (fmr["Former EL year"].isin(["1", "2", "3", "4", "All"]))
        ].copy()

        if not target.empty:
            # The CSV's Grade column holds "g3-8" and "10" (not "g10"); the
            # grade-10 filter silently matched nothing until this was fixed.
            for grade in ["g3-8", "10"]:
                sub = target[target["Grade"] == grade].sort_values("Former EL year")
                if sub.empty:
                    continue
                st.subheader(f"Former EL MCAS — Grades {grade.replace('g', '')}")
                # Build a long-format DF for plotting
                long = sub.melt(
                    id_vars=["Former EL year", "ELA Tested #"],
                    value_vars=["ELA  E+M %", "Math  E+M %", "STE  E+M %"],
                    var_name="Subject", value_name="Pct",
                )
                long["Subject"] = long["Subject"].map({
                    "ELA  E+M %": "ELA",
                    "Math  E+M %": "Math",
                    "STE  E+M %": "Science",
                })
                long = long.dropna(subset=["Pct"])

                fig = px.bar(
                    long, x="Former EL year", y="Pct", color="Subject",
                    barmode="group",
                    color_discrete_map={"ELA": "#1976D2", "Math": "#D32F2F", "Science": "#388E3C"},
                )
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    yaxis_tickformat=".0%",
                    yaxis_title="% Meeting + Exceeding",
                    xaxis_title="Years since exiting EL status (All = combined)",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No FormerEL records found in Lynn data.")
else:
    st.info("Former EL achievement data is temporarily unavailable.")

st.caption(
    "Former EL outcomes generally improve with more years post-exit, as students "
    "have more time to consolidate English proficiency while learning content. "
    "DESE monitors former ELs for 4 years to track this trajectory."
)

st.divider()

# ---------------------------------------------------------------------------
# Key narrative
# ---------------------------------------------------------------------------

st.subheader("Why this matters")
st.markdown(
    """
LEHS serves more English Learners and first language not English students
today than at any point in its history. That changes which MCAS scores get
reported, which interventions get funded, which staff capacities matter most,
and how a graduating class looks four years after it walks in.

The **Correlation Lab** lets you cross reference ELL share against outcomes
across all 26 gateway high schools. The **Teachers & Workforce** section
tracks whether staff capacity for ELL instruction has kept pace with the
population growth shown above.
"""
)

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Enrollment & demographics': enrollment,
        'MCAS achievement': mcas,
        'ACCESS (ELL reporting elements)': load_dataset("el_access"),
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

