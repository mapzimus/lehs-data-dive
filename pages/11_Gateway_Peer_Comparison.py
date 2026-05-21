"""Section 11 — Gateway Peer Comparison: LEHS vs. 25 gateway-city main HS."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, GATEWAY_PEER_COLOR, LEHS_GOLD, LEHS_NAVY
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE, PROCESSED_DIR
from utils.data_loader import load_dataset

st.set_page_config(
    page_title="Gateway Peer Comparison | LEHS", page_icon="🏙️", layout="wide"
)
sidebar_attribution()

st.title("Gateway Peer Comparison")
st.markdown(
    "LEHS and **Lynn Classical High School (LCHS)** benchmarked against the main "
    "comprehensive high school in each of the other 25 Massachusetts Gateway "
    "Cities — similar urban contexts and demographic profiles."
)
st.caption(
    "Note: \"Lynn\" by itself refers to the whole district (16k+ students across "
    "22 schools). LEHS and LCHS are the two largest comprehensive high schools "
    "inside that district — both shown here for fair school-to-school comparison."
)

# Load the peer-schools manifest
peer_file = PROCESSED_DIR / "_peer_schools.json"
if not peer_file.exists():
    st.info("Peer comparison data is temporarily unavailable. Please check back later.")
    st.stop()
peers = json.loads(peer_file.read_text())
gateway_main = peers["gateway_main_hs"]

# Build city -> school_code dict
city_to_school = {
    city: info["school_code"] for city, info in gateway_main.items() if info.get("school_code")
}
school_to_city = {v: k for k, v in city_to_school.items()}
gateway_codes = list(city_to_school.values())

# Add LCHS alongside LEHS so the Lynn comparison isn't "one school vs 25 cities"
if LCHS_SCHOOL_CODE not in gateway_codes:
    gateway_codes.append(LCHS_SCHOOL_CODE)
    school_to_city[LCHS_SCHOOL_CODE] = "Lynn"

# Friendly labels — distinguishes LEHS / LCHS from each other and from other Lynn rows
LYNN_SCHOOL_LABELS = {
    LEHS_SCHOOL_CODE: "Lynn — LEHS",
    LCHS_SCHOOL_CODE: "Lynn — LCHS",
}

enrollment = load_dataset("enrollment_demographics")
dart = load_dataset("dart_success_after_hs")
grad = load_dataset("graduation_rates")
school_exp = load_dataset("school_expenditures")

if enrollment.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

# ---------------------------------------------------------------------------
# Build the scorecard panel
# ---------------------------------------------------------------------------

st.header("Latest-Year Scorecard")

latest_enr_year = int(enrollment["SY"].max())

# Enrollment + demographics
enr = enrollment[
    (enrollment["ORG_CODE"].isin(gateway_codes)) & (enrollment["SY"] == latest_enr_year)
].copy()
scorecard = enr[[
    "ORG_CODE", "ORG_NAME", "DIST_NAME",
    "TOTAL_CNT", "EL_PCT", "LI_PCT", "SWD_PCT", "HN_PCT", "HL_PCT",
]].rename(columns={
    "TOTAL_CNT": "Enrollment",
    "EL_PCT": "% ELL",
    "LI_PCT": "% Low Income",
    "SWD_PCT": "% SPED",
    "HN_PCT": "% High Needs",
    "HL_PCT": "% Hispanic/Latino",
})
scorecard["City"] = scorecard.apply(
    lambda r: LYNN_SCHOOL_LABELS.get(r["ORG_CODE"], r["DIST_NAME"]),
    axis=1,
)

# Add DART indicators: graduation, immediate college, FAFSA
def pivot_dart(indicator: str, label: str) -> pd.DataFrame:
    sub = dart[
        (dart["ORG_CODE"].isin(gateway_codes))
        & (dart["INDICATOR"] == indicator)
        & (dart["STU_GRP"] == "All Students")
    ].copy()
    sub["VALUE"] = pd.to_numeric(sub["VALUE"], errors="coerce")
    latest = sub.sort_values("SY").groupby("ORG_CODE").tail(1)
    return latest[["ORG_CODE", "VALUE"]].rename(columns={"VALUE": label})

grad_4yr = pivot_dart("4-year cohort graduation rate", "4yr Grad Rate")
immediate = pivot_dart(
    "Students enrolled in postsecondary education in the immediate fall after high school graduation",
    "Immediate College",
)
fafsa = pivot_dart("Grade 12 students who completed FAFSA", "% FAFSA")
chronic = pivot_dart(
    "Chronically absent rate (% of students absent 10% or more each year)", "% Chronic Absence",
)
ap_3plus = pivot_dart("Jr/Sr AP test takers scoring 3 or above", "% AP 3+")

for d in [grad_4yr, immediate, fafsa, chronic, ap_3plus]:
    scorecard = scorecard.merge(d, on="ORG_CODE", how="left")

# Per-pupil spending (latest)
if not school_exp.empty:
    sp = school_exp[
        (school_exp["ORG_CODE"].isin(gateway_codes))
        & (school_exp["IND_CAT"] == "Total A+B+C")
        & (school_exp["IND_SUBCAT"] == "Total Expenditures")
    ].copy()
    sp["IND_VALUE"] = pd.to_numeric(sp["IND_VALUE"], errors="coerce")
    sp_latest = sp.sort_values("SY").groupby("ORG_CODE").tail(1)[["ORG_CODE", "IND_VALUE"]]
    sp_latest = sp_latest.rename(columns={"IND_VALUE": "$ Per Pupil"})
    scorecard = scorecard.merge(sp_latest, on="ORG_CODE", how="left")

scorecard = scorecard.sort_values("Enrollment", ascending=False)
display_cols = [
    "City", "ORG_NAME", "Enrollment", "% ELL", "% Low Income", "% High Needs",
    "% Hispanic/Latino", "4yr Grad Rate", "Immediate College", "% FAFSA",
    "% AP 3+", "% Chronic Absence", "$ Per Pupil",
]
display = scorecard[display_cols].rename(columns={"ORG_NAME": "School"}).copy()

# Format
for col in ["% ELL", "% Low Income", "% High Needs", "% Hispanic/Latino",
            "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP 3+", "% Chronic Absence"]:
    display[col] = display[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
display["Enrollment"] = display["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
display["$ Per Pupil"] = display["$ Per Pupil"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")

# Highlight LEHS + LCHS rows (Lynn's two main comprehensive HS)
def highlight_lynn_schools(row):
    if str(row["City"]).startswith("Lynn"):
        return ["background-color: #FFF4D6"] * len(row)
    return [""] * len(row)

st.dataframe(display.style.apply(highlight_lynn_schools, axis=1),
             use_container_width=True, hide_index=True)
st.caption(f"School year {latest_enr_year}. Lynn schools (LEHS + LCHS) highlighted in gold.")

st.divider()

# ---------------------------------------------------------------------------
# Scatter: per-pupil spending vs. graduation rate
# ---------------------------------------------------------------------------

st.header("Where does LEHS fall? Per-Pupil Spending vs. Outcomes")

st.subheader("Per-pupil spending vs. 4-year graduation rate")

scatter_df = scorecard.dropna(subset=["$ Per Pupil", "4yr Grad Rate"]).copy()
if not scatter_df.empty:
    scatter_df["highlight"] = scatter_df["City"].apply(
        lambda x: "Lynn HS" if str(x).startswith("Lynn") else "Other Gateway HS"
    )
    fig = px.scatter(
        scatter_df, x="$ Per Pupil", y="4yr Grad Rate",
        text="City", color="highlight",
        color_discrete_map={"Lynn HS": LEHS_GOLD, "Other Gateway HS": GATEWAY_PEER_COLOR},
        trendline="ols",
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_tickformat="$,.0f",
        yaxis_tickformat=".0%",
        xaxis_title="$ per pupil",
        yaxis_title="4-year graduation rate",
    )
    st.plotly_chart(fig, use_container_width=True)

st.subheader("ELL share vs. 4-year graduation rate")
scatter_df2 = scorecard.dropna(subset=["% ELL", "4yr Grad Rate"]).copy()
if not scatter_df2.empty:
    scatter_df2["highlight"] = scatter_df2["City"].apply(
        lambda x: "Lynn HS" if str(x).startswith("Lynn") else "Other Gateway HS"
    )
    fig = px.scatter(
        scatter_df2, x="% ELL", y="4yr Grad Rate",
        text="City", color="highlight",
        color_discrete_map={"Lynn HS": LEHS_GOLD, "Other Gateway HS": GATEWAY_PEER_COLOR},
        trendline="ols",
    )
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(
        **DEFAULT_LAYOUT, xaxis_tickformat=".0%", yaxis_tickformat=".0%",
        xaxis_title="% English Learners", yaxis_title="4-year graduation rate",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Algorithmically-similar peer subset
# ---------------------------------------------------------------------------

st.header("Algorithmically-Similar Peers")
st.caption(
    "Rather than a hand-picked peer list, find the schools whose **demographic "
    "profile** is closest to LEHS in normalized feature space. Distance is "
    "Euclidean across the five demographic dimensions below, each z-score "
    "normalized so no single feature dominates."
)

import numpy as np  # noqa: E402

similarity_features = ["% ELL", "% Low Income", "% High Needs",
                        "% Hispanic/Latino", "Enrollment"]

# Build a clean numeric matrix
sim_df = scorecard[["ORG_CODE", "City", "ORG_NAME"] + similarity_features].copy()
sim_df = sim_df.dropna(subset=similarity_features)

if (
    not sim_df.empty
    and (sim_df["ORG_CODE"] == LEHS_SCHOOL_CODE).any()
):
    # Z-score normalize each feature so that, e.g., enrollment in students
    # doesn't drown out ELL fraction.
    X = sim_df[similarity_features].astype(float).to_numpy()
    mu = X.mean(axis=0)
    sd = X.std(axis=0, ddof=0)
    sd_safe = np.where(sd == 0, 1.0, sd)
    Z = (X - mu) / sd_safe

    lehs_idx = sim_df.index[sim_df["ORG_CODE"] == LEHS_SCHOOL_CODE][0]
    lehs_pos = sim_df.index.get_loc(lehs_idx)
    distances = np.sqrt(((Z - Z[lehs_pos]) ** 2).sum(axis=1))
    sim_df = sim_df.assign(_distance=distances)
    # Keep LEHS + 5 closest peers (excluding LEHS itself)
    closest = sim_df.sort_values("_distance").head(6)

    # Merge full scorecard so the display table has outcomes too
    closest_full = scorecard[scorecard["ORG_CODE"].isin(closest["ORG_CODE"])].copy()
    closest_full = closest_full.merge(
        closest[["ORG_CODE", "_distance"]], on="ORG_CODE", how="left",
    ).sort_values("_distance")

    show_cols = ["City", "ORG_NAME", "_distance"] + similarity_features + [
        "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP 3+", "% Chronic Absence",
    ]
    show = closest_full[show_cols].rename(columns={
        "ORG_NAME": "School", "_distance": "Similarity (lower = more similar)",
    }).copy()
    show["Similarity (lower = more similar)"] = show["Similarity (lower = more similar)"].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "—"
    )
    for col in ["% ELL", "% Low Income", "% High Needs", "% Hispanic/Latino",
                 "4yr Grad Rate", "Immediate College", "% FAFSA", "% AP 3+", "% Chronic Absence"]:
        if col in show.columns:
            show[col] = show[col].apply(lambda x: f"{x:.0%}" if pd.notna(x) else "—")
    show["Enrollment"] = show["Enrollment"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
    st.dataframe(show.style.apply(highlight_lynn_schools, axis=1),
                 use_container_width=True, hide_index=True)

    # Plain-language explanation of who landed in the top-5
    others = closest_full[closest_full["ORG_CODE"] != LEHS_SCHOOL_CODE]["City"].tolist()
    if others:
        st.markdown(
            "**Closest peers by demographic similarity:** "
            + " · ".join(f"**{c}**" for c in others)
            + ". Differences in outcomes across these schools are the "
            "most informative — same kinds of students, different "
            "institutional responses."
        )
    st.caption(
        "Limitation: similarity is computed only across the 26 gateway-city "
        "main HS in the data panel. A future iteration could draw from "
        "all-MA enrollment for a wider 'similar conditions' peer set."
    )

