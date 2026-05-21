"""
Section 12 — Cross-Reference Lab: correlation discovery across domains.

The novel analytical layer no DESE tool provides.
"""

import json

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, GATEWAY_PEER_COLOR, LEHS_GOLD, LEHS_NAVY
from utils.constants import PROCESSED_DIR
from utils.correlations import interpret_r, pearson, regression_line
from utils.data_loader import load_dataset

st.set_page_config(page_title="Correlation Lab | LEHS", page_icon="🔬", layout="wide")
sidebar_attribution()

st.title("Cross-Reference Lab")
st.markdown(
    "Because every dataset lives in the same data model joined on (school, year), "
    "we can ask questions DESE's siloed tools can't. Pick any two metrics "
    "below to explore relationships across the 26 gateway-city high schools."
)

st.caption(
    "**Note:** Correlation is not causation. Patterns here are starting points "
    "for questions, not proof of cause and effect."
)

# ---------------------------------------------------------------------------
# Build the master panel: one row per (school, year) with key indicators
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def build_master_panel() -> pd.DataFrame:
    """Wide panel: rows = (school_code, year), cols = key metrics from all sources."""
    from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE
    peers = json.loads((PROCESSED_DIR / "_peer_schools.json").read_text())
    gateway_codes = [
        info["school_code"] for info in peers["gateway_main_hs"].values()
        if info.get("school_code")
    ]
    # Include BOTH Lynn comprehensive high schools so the gateway scatter
    # shows them as distinct points (LEHS + LCHS). Lynn (district) is the
    # whole 22-school district — comparing it against single-school
    # gateway-city HS would be apples-to-oranges.
    for code in (LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE):
        if code not in gateway_codes:
            gateway_codes.append(code)

    # 1) Enrollment + demographics
    enr = load_dataset("enrollment_demographics")
    enr = enr[enr["ORG_CODE"].isin(gateway_codes)].copy()
    enr_cols = ["SY", "ORG_CODE", "ORG_NAME", "DIST_NAME",
                "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT",
                "HL_PCT", "BAA_PCT", "AS_PCT", "WH_PCT", "FLNE_PCT"]
    base = enr[[c for c in enr_cols if c in enr.columns]].rename(columns={
        "TOTAL_CNT": "Enrollment",
        "EL_PCT": "ELL_pct", "LI_PCT": "LowIncome_pct",
        "SWD_PCT": "SPED_pct", "HN_PCT": "HighNeeds_pct",
        "HL_PCT": "Hispanic_pct", "BAA_PCT": "Black_pct",
        "AS_PCT": "Asian_pct", "WH_PCT": "White_pct",
        "FLNE_PCT": "FirstLangNotEnglish_pct",
    })

    # 2) DART indicators (long → wide)
    dart = load_dataset("dart_success_after_hs")
    dart = dart[(dart["ORG_CODE"].isin(gateway_codes)) & (dart["STU_GRP"] == "All Students")].copy()
    dart["VALUE"] = pd.to_numeric(dart["VALUE"], errors="coerce")

    indicator_aliases = {
        "4-year cohort graduation rate": "GradRate_4yr",
        "5-year cohort graduation rate": "GradRate_5yr",
        "9th to 10th grade promotion rate (first-time 9th graders only)": "Promotion_9to10",
        "Annual dropout rate": "Dropout",
        "Chronically absent rate (% of students absent 10% or more each year)": "ChronicAbsence",
        "Student attendance rate": "AttendanceRate",
        "Students suspended out-of-school at least once": "Suspension_pct",
        "Average student growth percentiles (SGP) in ELA": "SGP_ELA",
        "Average student growth percentiles (SGP) in mathematics": "SGP_Math",
        "Grade 10 students meeting or exceeding expectations in ELA": "MCAS_G10_ELA",
        "Grade 10 students meeting or exceeding expectations in mathematics": "MCAS_G10_Math",
        "Jr/Sr enrolled in one or more AP / IB courses": "AP_Enrolled",
        "Jr/Sr AP test takers scoring 3 or above": "AP_3plus",
        "SAT average score - Mathematics": "SAT_Math",
        "SAT average score - Reading": "SAT_Reading",
        "Grade 12 students who completed FAFSA": "FAFSA",
        "Students enrolled in postsecondary education in the immediate fall after high school graduation": "ImmediateCollege",
        "High school graduates enrolled in 2-year postsecondary education": "College_2yr",
        "High school graduates enrolled in 4-year postsecondary education": "College_4yr",
        "College students persistently enrolled in postsecondary education for the first two years": "CollegePersist",
        "High school graduates who completed MassCore": "MassCore",
    }
    dart_filt = dart[dart["INDICATOR"].isin(indicator_aliases.keys())].copy()
    dart_filt["alias"] = dart_filt["INDICATOR"].map(indicator_aliases)
    dart_wide = dart_filt.pivot_table(
        index=["SY", "ORG_CODE"], columns="alias", values="VALUE", aggfunc="mean"
    ).reset_index()

    # 3) Finance: per-pupil + teacher salary
    sp = load_dataset("school_expenditures")
    sp = sp[sp["ORG_CODE"].isin(gateway_codes)].copy()
    sp["IND_VALUE"] = pd.to_numeric(sp["IND_VALUE"], errors="coerce")
    pp = sp[(sp["IND_CAT"] == "Total A+B+C") & (sp["IND_SUBCAT"] == "Total Expenditures")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "PerPupil"})
    sal = sp[(sp["IND_CAT"] == "Teacher Salaries") & (sp["IND_SUBCAT"] == "Average Teacher Salary")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "AvgTeacherSalary"})
    t_ratio = sp[(sp["IND_CAT"] == "Teacher Salaries") & (sp["IND_SUBCAT"] == "Teachers per 100 FTE students")] \
            [["SY", "ORG_CODE", "IND_VALUE"]].rename(columns={"IND_VALUE": "TeachersPer100"})

    # Join everything
    panel = base.merge(dart_wide, on=["SY", "ORG_CODE"], how="outer")
    panel = panel.merge(pp, on=["SY", "ORG_CODE"], how="left")
    panel = panel.merge(sal, on=["SY", "ORG_CODE"], how="left")
    panel = panel.merge(t_ratio, on=["SY", "ORG_CODE"], how="left")
    return panel


panel = build_master_panel()
if panel.empty:
    st.error("Master panel empty.")
    st.stop()

NUMERIC_COLS = sorted([c for c in panel.columns if pd.api.types.is_numeric_dtype(panel[c]) and c != "SY"])

# ---------------------------------------------------------------------------
# Curated correlations
# ---------------------------------------------------------------------------

st.header("Curated Correlations")
st.caption(
    "Cross-domain questions across all 26 gateway-city HS. Each scatter uses "
    "the most recent year for which both metrics are available per school."
)


@st.cache_data(show_spinner=False)
def _latest_per_school(p: pd.DataFrame) -> pd.DataFrame:
    """For each (school, column), take the most recent year that has a value.
    Avoids dropping schools where the very latest row happens to be NaN for
    the indicator of interest."""
    static_cols = ["ORG_CODE", "ORG_NAME", "DIST_NAME"]
    metric_cols = [c for c in p.columns if c not in static_cols + ["SY"]]
    rows = []
    for org_code, grp in p.groupby("ORG_CODE"):
        grp = grp.sort_values("SY")
        row = {"ORG_CODE": org_code}
        for c in static_cols:
            if c in grp.columns and not grp[c].dropna().empty:
                row[c] = grp[c].dropna().iloc[-1]
        for c in metric_cols:
            non_null = grp[c].dropna()
            row[c] = non_null.iloc[-1] if not non_null.empty else None
        rows.append(row)
    out = pd.DataFrame(rows)
    return out


latest = _latest_per_school(panel)
latest["City"] = latest["DIST_NAME"]
latest["is_lehs"] = latest["ORG_CODE"] == "01630510"

curated_pairs = [
    ("PerPupil", "GradRate_4yr", "Does per-pupil spending correlate with graduation?"),
    ("PerPupil", "MCAS_G10_Math", "Does per-pupil spending correlate with grade-10 math?"),
    ("ELL_pct", "GradRate_4yr", "How does ELL share relate to graduation?"),
    ("ChronicAbsence", "GradRate_4yr", "Chronic absence vs. graduation"),
    ("Promotion_9to10", "GradRate_4yr", "9-to-10 promotion vs. graduation"),
    ("AP_Enrolled", "ImmediateCollege", "AP enrollment vs. immediate college enrollment"),
    ("FAFSA", "ImmediateCollege", "FAFSA completion vs. immediate college"),
    ("LowIncome_pct", "MCAS_G10_ELA", "Low income share vs. grade-10 ELA"),
    ("AvgTeacherSalary", "GradRate_4yr", "Teacher salary vs. graduation"),
]

for x, y, label in curated_pairs:
    if x not in latest.columns or y not in latest.columns:
        continue
    sub = latest[["City", x, y, "is_lehs"]].dropna()
    if len(sub) < 5:
        continue
    stats = pearson(sub, x, y)
    with st.expander(f"{label}  ·  r = {stats['r']:+.2f}  ({interpret_r(stats['r'])})"):
        sub["highlight"] = sub["is_lehs"].map({True: "LEHS", False: "Other Gateway HS"})
        fig = px.scatter(
            sub, x=x, y=y, text="City", color="highlight",
            color_discrete_map={"LEHS": LEHS_GOLD, "Other Gateway HS": GATEWAY_PEER_COLOR},
            trendline="ols",
        )
        fig.update_traces(textposition="top center", textfont_size=10)
        fig.update_layout(**DEFAULT_LAYOUT, xaxis_title=x, yaxis_title=y)
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            f"Pearson r = {stats['r']:+.3f} (p = {stats['p']:.3f}, n = {stats['n']}). "
            f"**Caveat:** correlation across 26 districts doesn't establish cause."
        )

st.divider()

# ---------------------------------------------------------------------------
# Custom explorer
# ---------------------------------------------------------------------------

st.header("Custom Correlation Explorer")
st.markdown("Pick any two metrics from the panel.")

c1, c2 = st.columns(2)
with c1:
    x_var = st.selectbox("X variable", options=NUMERIC_COLS,
                          index=NUMERIC_COLS.index("PerPupil") if "PerPupil" in NUMERIC_COLS else 0)
with c2:
    y_var = st.selectbox("Y variable", options=NUMERIC_COLS,
                          index=NUMERIC_COLS.index("GradRate_4yr") if "GradRate_4yr" in NUMERIC_COLS else 1)

scope = st.radio(
    "Scope",
    options=["Gateway HS (cross-section, latest year)",
             "All gateway HS x all years (panel)"],
    horizontal=True,
)

if scope.startswith("Gateway HS (cross"):
    data = latest[["ORG_CODE", "City", x_var, y_var, "is_lehs"]].dropna()
else:
    data = panel[["SY", "ORG_CODE", "DIST_NAME", x_var, y_var]].dropna()
    data["City"] = data["DIST_NAME"]
    data["is_lehs"] = data["ORG_CODE"] == "01630510"

if len(data) >= 3:
    data["highlight"] = data["is_lehs"].map({True: "LEHS", False: "Other"})
    fig = px.scatter(
        data, x=x_var, y=y_var, color="highlight",
        color_discrete_map={"LEHS": LEHS_GOLD, "Other": GATEWAY_PEER_COLOR},
        trendline="ols",
        hover_data=["City"],
    )
    fig.update_layout(**DEFAULT_LAYOUT, xaxis_title=x_var, yaxis_title=y_var)
    st.plotly_chart(fig, use_container_width=True)

    stats = pearson(data, x_var, y_var)
    reg = regression_line(data, x_var, y_var)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("Pearson r", f"{stats['r']:+.3f}")
    with c2: st.metric("p-value", f"{stats['p']:.4f}")
    with c3: st.metric("R²", f"{reg['r_squared']:.3f}")
    with c4: st.metric("n", f"{stats['n']:,}")

    st.caption(f"**Interpretation:** {interpret_r(stats['r'])}")
else:
    st.info("Not enough overlapping data points for these two variables.")

st.divider()

# ---------------------------------------------------------------------------
# Time-lagged within-school correlation
# ---------------------------------------------------------------------------

st.header("Time-Lagged Correlations — Does X today predict Y N years later?")
st.markdown(
    "Pairs the same school's value of metric X in year *Y* with its value of "
    "metric Y in year *Y+lag*. Useful for asking *predictive* questions across "
    "the school cohort lifecycle (e.g., does 9th-grade chronic absenteeism "
    "predict 12th-grade graduation 3 years later?). Each dot is one "
    "(school, base-year) pair across all 26 gateway HS x all years."
)

c1, c2, c3 = st.columns([3, 3, 2])
with c1:
    x_var_lag = st.selectbox(
        "Predictor (X) — measured in base year",
        options=NUMERIC_COLS,
        index=NUMERIC_COLS.index("ChronicAbsence") if "ChronicAbsence" in NUMERIC_COLS else 0,
        key="lag_x",
    )
with c2:
    y_var_lag = st.selectbox(
        "Outcome (Y) — measured in base year + lag",
        options=NUMERIC_COLS,
        index=NUMERIC_COLS.index("GradRate_4yr") if "GradRate_4yr" in NUMERIC_COLS else 1,
        key="lag_y",
    )
with c3:
    lag_years = st.slider("Lag (years)", 0, 6, 3, key="lag_n")

# Build the lagged join: take the panel, shift Y by -lag (so Y becomes value
# at SY+lag for the same school) and merge against X at SY.
panel_for_lag = panel.dropna(subset=["SY", "ORG_CODE"]).copy()
panel_for_lag["SY"] = pd.to_numeric(panel_for_lag["SY"], errors="coerce").astype("Int64")

x_side = panel_for_lag[["SY", "ORG_CODE", "ORG_NAME", "DIST_NAME", x_var_lag]].rename(
    columns={x_var_lag: "x_val"}
).dropna(subset=["x_val", "SY"])
y_side = panel_for_lag[["SY", "ORG_CODE", y_var_lag]].rename(
    columns={y_var_lag: "y_val", "SY": "SY_target"}
).dropna(subset=["y_val", "SY_target"])

# join condition: y_side.SY_target == x_side.SY + lag
x_side["SY_target"] = x_side["SY"] + lag_years
lagged = x_side.merge(y_side, on=["SY_target", "ORG_CODE"], how="inner")
lagged["is_lehs"] = lagged["ORG_CODE"] == "01630510"
lagged["highlight"] = lagged["is_lehs"].map({True: "LEHS", False: "Other"})
lagged["pair_label"] = (
    lagged["DIST_NAME"].fillna("") + " "
    + lagged["SY"].astype(str) + " -> " + lagged["SY_target"].astype(str)
)

if len(lagged) >= 5:
    fig = px.scatter(
        lagged, x="x_val", y="y_val", color="highlight",
        color_discrete_map={"LEHS": LEHS_GOLD, "Other": GATEWAY_PEER_COLOR},
        trendline="ols",
        hover_data=["pair_label"],
        labels={
            "x_val": f"{x_var_lag} (year Y)",
            "y_val": f"{y_var_lag} (year Y + {lag_years})",
        },
    )
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title=f"{x_var_lag} (year Y)",
        yaxis_title=f"{y_var_lag} (year Y + {lag_years})",
    )
    st.plotly_chart(fig, use_container_width=True)

    stats_lag = pearson(lagged, "x_val", "y_val")
    reg_lag = regression_line(lagged, "x_val", "y_val")
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Pearson r", f"{stats_lag['r']:+.3f}")
    with m2: st.metric("p-value", f"{stats_lag['p']:.4f}")
    with m3: st.metric("R²", f"{reg_lag['r_squared']:.3f}")
    with m4: st.metric("n pairs", f"{stats_lag['n']:,}")
    st.caption(f"**Interpretation:** {interpret_r(stats_lag['r'])}")
    st.caption(
        f"Each pair = one (school, base-year) observation where both metrics "
        f"exist at year Y and Y + {lag_years}. Lag = 0 collapses to a within-"
        f"year correlation across schools."
    )
else:
    st.info(
        f"Not enough (school, year) pairs where both {x_var_lag} (year Y) and "
        f"{y_var_lag} (year Y + {lag_years}) are populated. Try a smaller lag "
        f"or different metrics."
    )

st.divider()

# ---------------------------------------------------------------------------
# Composite indices
# ---------------------------------------------------------------------------

st.header("Composite Indices")
st.caption("Combine multiple indicators into a single ranked score.")

st.subheader("Adjust weights")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: w_grad = st.slider("Grad rate", 0.0, 1.0, 0.3, 0.05)
with c2: w_persist = st.slider("College persist", 0.0, 1.0, 0.2, 0.05)
with c3: w_mcas = st.slider("MCAS Math", 0.0, 1.0, 0.2, 0.05)
with c4: w_chronic = st.slider("Low chronic absence", 0.0, 1.0, 0.15, 0.05)
with c5: w_ap = st.slider("AP enroll", 0.0, 1.0, 0.15, 0.05)

total_weight = w_grad + w_persist + w_mcas + w_chronic + w_ap
if total_weight > 0:
    def z(col):
        if col not in latest.columns:
            return pd.Series(0.0, index=latest.index)
        x = latest[col].dropna()
        if x.std() == 0 or len(x) < 2:
            return pd.Series(0.0, index=latest.index)
        return (latest[col] - x.mean()) / x.std()

    latest["SuccessIndex"] = (
        w_grad * z("GradRate_4yr").fillna(0)
        + w_persist * z("CollegePersist").fillna(0)
        + w_mcas * z("MCAS_G10_Math").fillna(0)
        - w_chronic * z("ChronicAbsence").fillna(0)  # NEGATIVE: low absence = higher score
        + w_ap * z("AP_Enrolled").fillna(0)
    ) / total_weight

    ranked = latest[["City", "ORG_NAME", "SuccessIndex"]].dropna().sort_values(
        "SuccessIndex", ascending=False
    ).reset_index(drop=True)
    ranked["Rank"] = ranked.index + 1
    ranked = ranked[["Rank", "City", "ORG_NAME", "SuccessIndex"]]
    ranked["SuccessIndex"] = ranked["SuccessIndex"].round(2)

    def highlight_lehs(row):
        return ["background-color: #FFF4D6" if row["City"] == "Lynn" else "" for _ in row]

    st.dataframe(ranked.style.apply(highlight_lehs, axis=1),
                 use_container_width=True, hide_index=True)

    lehs_row = ranked[ranked["City"] == "Lynn"]
    if not lehs_row.empty:
        st.success(
            f"**LEHS ranks #{int(lehs_row.iloc[0]['Rank'])} of {len(ranked)} "
            f"gateway-city main HS** on this composite index."
        )

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'Master gateway-HS panel': panel,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

