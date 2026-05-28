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

# Building photo — anchors the page in the actual physical school rather
# than a wall of charts. The 1928-built classical-revival main entrance
# on O'Callaghan Way is the most recognizable image of LEHS.
st.image(
    str(IMAGES_DIR / "lehs-building.jpg"),
    use_container_width=True,
    caption="Lynn English High School — main entrance, O'Callaghan Way",
)

# ---------------------------------------------------------------------------
# Leadership — Principal Rardy Pena. Two-column with photo so the reader
# knows who runs the school they're about to read 18 pages of data about.
# ---------------------------------------------------------------------------

_lead_l, _lead_r = st.columns([1, 4])
with _lead_l:
    st.image(str(IMAGES_DIR / "principal-rardy-pena.jpg"), width=160)
with _lead_r:
    st.markdown(
        "### Principal: Rardy Peña  \n"
        "Lynn English High School is led by **Principal Rardy Peña**. "
        "The data on the rest of this page tells a story about students, "
        "demographics, and outcomes — the people leading the school's "
        "response to that story matter just as much."
    )

# ---------------------------------------------------------------------------
# Phase E — DESE ESSA accountability classification. This is the single
# highest-stakes status indicator the state publishes about LEHS; it
# determines whether the school is subject to federal/state intervention
# requirements. Show it up top before any demographic context.
# ---------------------------------------------------------------------------

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
# A broader history of LEHS — not just the data deltas above. Sourced from
# Wikipedia (LEHS + English High School 1892 building + Lynn Public Schools),
# Itemlive (principal-transition coverage), DESE report cards, and the
# Boston Public Library postcard collection.
# ---------------------------------------------------------------------------

st.divider()
st.subheader("A history of Lynn English")
st.caption(
    "How the school went from a Romanesque brick pile on Essex Street in 1892 "
    "to the Classical-Revival campus on Goodridge Street today. "
    "Sourced from Wikipedia, *The Lynn Item*, DESE report cards, and the "
    "Boston Public Library archive."
)

_hist_tab_origin, _hist_tab_today, _hist_tab_leaders, _hist_tab_district = st.tabs([
    "Origins & the 1924 fire",
    "The current building",
    "Recent leadership",
    "District context",
])

with _hist_tab_origin:
    st.markdown(
        """
**Founded 1892** as the city's second high school, English originally lived
at **498 Essex Street** — a Romanesque brick building designed by the firm
of **Wheeler & Northend** and built directly across Liberty Street from
Lynn's first high school (the Old Lynn High School, 1850–51). A James
Street–facing addition by Wheeler & Johnson followed in **1916** as
enrollment grew.

**March 29, 1924 — the fire.** The original 1892 portion was destroyed in
a major fire. One Lynn firefighter was killed in the response. The school
was rebuilt almost immediately as a **T-shaped three-story Jacobethan
structure designed by George A. Cornet**, completed later in 1924, so
classes could resume on the same site.

The post-fire Essex Street building served as Lynn English's home through
**1932**, then was converted to a junior high school, then sat vacant
(documented as such in 1985), and was eventually adapted into residential
units. The building was added to the **National Register of Historic
Places on September 11, 1986**.
        """
    )

with _hist_tab_today:
    st.markdown(
        """
The current Lynn English campus opened on **Goodridge Street in East Lynn
in 1931** — a Classical Revival design with the **Lincoln Foyer** (its
life-sized Abraham Lincoln statue donated by the class of 1934) as the
ceremonial entrance. Construction cost **$1.8M** in 1931 dollars.

A later push to rename the school "Eastern Senior High" was beaten back
when **alumni organized a parade of 2,000+ people** through the city in
defense of the Lynn English name. The name survived; the parade is the
kind of small civic event that ends up in the school's institutional
self-image for generations.

LEHS is today **the largest school in Lynn Public Schools** by enrollment.
        """
    )

with _hist_tab_leaders:
    st.markdown(
        """
**Recent principals**

- **Dr. Rardy Peña** — current principal. Hired Aldred (the first female
  AD in Lynn) in 2025, citing her "understanding of student-athlete
  development."
- **Tessie Mower** — interim principal, **July 1, 2020 →** the permanent
  search. A LEHS alumna and former English Department head, Mower came
  from the vice principal role at Lynn Classical. She started teaching in
  Lynn Public Schools in 1994.
- **Thomas Strangie** — *did not return* for the 2020–21 school year
  after decades of service, following social-media criticism of staff at
  both Lynn English and Lynn Classical. Superintendent Patrick Tutwiler
  framed the transition publicly: "English High is the largest school in
  the Lynn Public Schools and it is a school that in recent weeks has
  indicated a need for change… leadership that can help it heal, first
  and foremost, and evolve."

**Earlier 20th-century note**

In the **1940s–50s**, LEHS was led by **Tom Whelan** — the same Tom
Whelan who'd been an MLB infielder (Boston Braves, 1920) and a
two-sport pro who'd played football alongside Jim Thorpe on the
Canton Bulldogs in 1919–20. He came home to teach, coach baseball,
serve as AD, and eventually as principal. The **Whelan Family
Scholarship** at LEHS is named in his honor.
        """
    )

with _hist_tab_district:
    st.markdown(
        """
**Lynn Public Schools (LPS)** — the district LEHS sits inside — enrolled
**17,447 students across 27 schools** as of June 2024. The LPS high
schools:

- **Lynn English** (9–12) — the focus of this dashboard
- **Lynn Classical** (9–12) — sister school, the Thanksgiving football rival
- **Lynn Vocational & Technical Institute (LVTI / Lynn Tech)** (8–12)
- **Frederick Douglass Collegiate Academy** at North Shore Community College (9–12, opened Fall 2022)
- **Fecteau-Leary Junior/Senior High School** (7–12)

**A few district-context moments worth remembering:**

- Around **2011**, the UN High Commission for Refugees relocated families
  to Lynn from many countries, sharply increasing the district's English
  Learner population — see the *English Learners* page for what that
  looked like at LEHS specifically.
- **2017** — Lynn voters rejected a ballot proposal to fund two new
  middle schools.
- **2018** — Dr. **Patrick Tutwiler** became LPS's first Black
  superintendent; instituted free meals and Operating Protocols.
  Resigned in summer 2022.
- The superintendent position was **vacant** as of mid-2024 per the LPS
  Wikipedia article; current assistant superintendents include Debra
  Ruggiero, Maricel Goris, and Molly Cohen.
        """
    )

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
    "Five key student-group classifications that drive resource allocation, "
    "accountability calculations, and federal/state programmatic support."
)

pop_long = lehs.melt(
    id_vars=["SY"],
    value_vars=["EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "FLNE_PCT"],
    var_name="Group",
    value_name="Pct",
)
pop_labels = {
    "EL_PCT":  "English Learner",
    "LI_PCT":  "Low Income",
    "SWD_PCT": "Students w/ Disabilities",
    "HN_PCT":  "High Needs",
    "FLNE_PCT":"First Lang Not English",
}
pop_long["Group"] = pop_long["Group"].map(pop_labels)
pop_long = pop_long.dropna(subset=["Pct"])

fig = px.line(
    pop_long, x="SY", y="Pct", color="Group", markers=True,
    color_discrete_map={
        "English Learner":          SUBGROUP_PALETTE["English Learner"],
        "Low Income":               SUBGROUP_PALETTE["Low Income"],
        "Students w/ Disabilities": SUBGROUP_PALETTE["Students w/ Disabilities"],
        "High Needs":               SUBGROUP_PALETTE["High Needs"],
        "First Lang Not English":   "#0277BD",
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

