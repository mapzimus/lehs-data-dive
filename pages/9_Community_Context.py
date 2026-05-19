"""Section 9 — Community Context (Census ACS for Lynn's 22 census tracts)."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY
from utils.constants import LEHS_SCHOOL_CODE, PROCESSED_DIR
from utils.data_loader import load_dataset

st.set_page_config(page_title="Community Context | LEHS", page_icon="🏘️", layout="wide")
sidebar_attribution()

st.title("Community Context")
st.markdown(
    "The neighborhood Lynn English serves — Census ACS demographics from the "
    "22 census tracts inside Lynn city limits, plus the school-level proxies "
    "that mirror them."
)

# ---------------------------------------------------------------------------
# School-level proxies (LEHS itself)
# ---------------------------------------------------------------------------

st.header("LEHS — Student Composition (as a community mirror)")
st.caption(
    "These are LEHS student-level figures, not Census. They reflect Lynn's "
    "community demographics because the school's catchment overlaps the city."
)

enrollment = load_dataset("enrollment_demographics")
lehs = enrollment[enrollment["ORG_CODE"] == LEHS_SCHOOL_CODE].sort_values("SY") \
    if not enrollment.empty else pd.DataFrame()

if not lehs.empty:
    latest = lehs.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("% First Language Not English", f"{latest['FLNE_PCT']:.0%}")
    with c2: st.metric("% Hispanic/Latino",            f"{latest['HL_PCT']:.0%}")
    with c3: st.metric("% Low Income",                 f"{latest['LI_PCT']:.0%}")
    with c4: st.metric("% English Learner",            f"{latest['EL_PCT']:.0%}")

st.divider()

# ---------------------------------------------------------------------------
# Lynn census tracts — ACS data
# ---------------------------------------------------------------------------

tracts_path = PROCESSED_DIR / "lynn_tracts.geojson"
if not tracts_path.exists():
    st.info("Census ACS data is temporarily unavailable. Please check back later.")
    st.stop()

tracts = gpd.read_file(tracts_path)
for col in ["median_household_income", "foreign_born_pct", "bachelors_or_higher_pct",
            "severe_burden_pct", "non_english_pct", "lang_total", "pop_total"]:
    if col in tracts.columns:
        tracts[col] = pd.to_numeric(tracts[col], errors="coerce")

st.header("Census ACS — Lynn's 22 Census Tracts")
st.caption(
    "5-year ACS estimates (2019–2023). Lynn has 22 census tracts; each is a "
    "neighborhood-scale unit of ~3–6K residents. Variation across these "
    "tracts shows how Lynn is not demographically uniform."
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    med_inc = tracts["median_household_income"].median()
    st.metric("Median household income (Lynn median tract)", f"${med_inc:,.0f}")
with c2:
    fb = tracts["foreign_born_pct"].mean()
    st.metric("Avg % Foreign-born", f"{fb:.0%}")
with c3:
    ba = tracts["bachelors_or_higher_pct"].mean()
    st.metric("Avg % Bachelor's or higher (age 25+)", f"{ba:.0%}")
with c4:
    nm = tracts["non_english_pct"].mean()
    st.metric("Avg % non-English at home", f"{nm:.0%}")

# Comparison to MA state averages (approx, ACS 2023)
st.caption(
    "**Massachusetts state averages for comparison**: median household income "
    "~$96,500 · foreign-born ~17% · bachelor's+ ~46% · non-English at home ~26%. "
    "Lynn's tracts skew significantly lower-income and more foreign-born, with "
    "substantially higher non-English-at-home share."
)

st.divider()

# ---------------------------------------------------------------------------
# Distribution of each variable across the 22 tracts
# ---------------------------------------------------------------------------

st.header("Variation Across Lynn's Census Tracts")
st.caption("Each row is one census tract. Bars show how much spread there is across the city.")

metrics = [
    ("median_household_income", "Median household income", "${:,.0f}", "Greens"),
    ("foreign_born_pct",        "% Foreign-born",          "{:.0%}",   "Purples"),
    ("non_english_pct",         "% Non-English at home",   "{:.0%}",   "Greens"),
    ("bachelors_or_higher_pct", "% Bachelor's or higher",  "{:.0%}",   "Blues"),
    ("severe_burden_pct",       "% Severely rent-burdened","{:.0%}",   "Reds"),
]

for col, label, fmt, palette in metrics:
    if col not in tracts.columns:
        continue
    sub = tracts.dropna(subset=[col]).copy()
    if sub.empty:
        continue
    sub["label"] = sub[col].apply(lambda x: fmt.format(x))
    sub = sub.sort_values(col, ascending=True)

    st.subheader(label)
    fig = px.bar(
        sub, y="NAMELSAD", x=col, orientation="h",
        text="label", color=col, color_continuous_scale=palette,
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        **DEFAULT_LAYOUT,
        xaxis_title=label,
        yaxis_title="",
        coloraxis_showscale=False,
        height=480,
    )
    if "_pct" in col:
        fig.update_layout(xaxis_tickformat=".0%")
    elif col == "median_household_income":
        fig.update_layout(xaxis_tickformat="$,.0f")
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Languages spoken at home — the linguistic landscape
# ---------------------------------------------------------------------------

st.header("Linguistic Landscape")
st.caption(
    "Census ACS at tract level publishes the COLLAPSED language table (13 groups). "
    "Across all 22 Lynn tracts, Spanish is the dominant non-English language. "
    "Granular breakouts (Khmer/Cambodian, Portuguese, Arabic) are suppressed by "
    "Census at tract resolution but are available at the city level."
)

if "non_english_pct" in tracts.columns:
    lang_share = pd.DataFrame({
        "Group": ["English only", "Non-English"],
        "Total speakers (age 5+)": [
            tracts["lang_total"].sum() - tracts.get("dominant_non_english_count", pd.Series([0])).sum() - (
                tracts["lang_total"].sum() * (1 - tracts["non_english_pct"].mean())
            ) if False else (tracts["lang_total"].fillna(0).sum() *
                              (1 - tracts["non_english_pct"].mean())),
            tracts["lang_total"].fillna(0).sum() * tracts["non_english_pct"].mean(),
        ],
    })
    fig = px.pie(
        lang_share, names="Group", values="Total speakers (age 5+)",
        color="Group",
        color_discrete_map={"English only": LEHS_NAVY, "Non-English": LEHS_GOLD},
        hole=0.55,
    )
    fig.update_traces(textinfo="percent+label", textfont_size=12)
    fig.update_layout(**DEFAULT_LAYOUT, height=380)
    st.plotly_chart(fig, width="stretch")

st.divider()

# ---------------------------------------------------------------------------
# Map link
# ---------------------------------------------------------------------------

st.subheader("See the same data geographically")
st.markdown(
    """
The **[Maps section](/Maps)** of this dashboard (opens via the sidebar) opens
the Lynn map, where each tract is rendered as a polygon colored by any of
these indicators. Click any tract for the full detail panel.

For the statewide cartographic comparison, see the
[Massachusetts Education Atlas](https://maxwellhowegis.com/ma-atlas/) — every
public school district in MA colored by 40+ metrics including these community
indicators (where data is available at scale).
"""
)

with st.expander("What's still missing — and how to add it"):
    st.markdown(
        """
- **SAIPE** (district-level child poverty estimates) — `census` Python client,
  small download.
- **EPA EJScreen** — environmental-justice indicators around the school
  (lead, air quality, traffic proximity). Bulk CSV at ejscreen.epa.gov.
- **CDC PLACES** — local health (mental health, uninsured rates).
- **BLS / MA EOLWD** — local labor market and median wages.
- **Town-level ACS for the 25 other Gateway Cities** — would unlock
  side-by-side community-context comparison.

These would each take one focused script-writing session.
"""
    )
