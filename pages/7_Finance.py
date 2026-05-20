"""Section 7 — Finance & Resource Allocation."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY
from utils.constants import LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
from utils.data_loader import load_dataset
from utils.interpret import sy_label

LCHS_COLOR = LEHS_GOLD

st.set_page_config(page_title="Finance | LEHS", page_icon="💰", layout="wide")
sidebar_attribution()

st.title("Finance & Resource Allocation")
st.markdown(
    "School-level expenditures by category, teacher compensation, and "
    "federal-vs-state-and-local funding split — drawn from DESE's School "
    "Expenditures by Spending Category dataset. Lynn English vs. Lynn "
    "Classical comparisons isolate school-level effects within the same "
    "district budget."
)

school_exp = load_dataset("school_expenditures")
dist_exp = load_dataset("district_expenditures")
if school_exp.empty:
    st.info("Data is temporarily unavailable. Please check back later.")
    st.stop()

lehs_exp = school_exp[school_exp["ORG_CODE"] == LEHS_SCHOOL_CODE].copy()
lehs_exp["IND_VALUE"] = pd.to_numeric(lehs_exp["IND_VALUE"], errors="coerce")

lchs_exp = school_exp[school_exp["ORG_CODE"] == LCHS_SCHOOL_CODE].copy()
lchs_exp["IND_VALUE"] = pd.to_numeric(lchs_exp["IND_VALUE"], errors="coerce")

# ---------------------------------------------------------------------------
# Total per-pupil trend — LEHS vs LCHS
# ---------------------------------------------------------------------------

st.header("Total Per-Pupil Expenditure")

def _total_per_pupil(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        (df["IND_CAT"] == "Total A+B+C")
        & (df["IND_SUBCAT"] == "Total Expenditures")
    ].sort_values("SY")

total_exp = _total_per_pupil(lehs_exp)
total_lchs = _total_per_pupil(lchs_exp)

if not total_exp.empty:
    latest = total_exp.iloc[-1]
    prior = total_exp.iloc[-2] if len(total_exp) > 1 else None

    c1, c2 = st.columns([1, 3])
    with c1:
        st.metric(
            f"LEHS Per Pupil (FY {int(latest['SY'])})",
            f"${latest['IND_VALUE']:,.0f}",
            f"${latest['IND_VALUE']-prior['IND_VALUE']:+,.0f} vs SY {int(prior['SY'])}" if prior is not None else "",
        )
        if not total_lchs.empty:
            latest_l = total_lchs.iloc[-1]
            diff = latest["IND_VALUE"] - latest_l["IND_VALUE"]
            st.metric(
                f"LCHS Per Pupil (FY {int(latest_l['SY'])})",
                f"${latest_l['IND_VALUE']:,.0f}",
                f"${diff:+,.0f} LEHS – LCHS",
            )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=total_exp["SY"], y=total_exp["IND_VALUE"], mode="lines+markers",
        name="Lynn English", line=dict(color=LEHS_NAVY, width=3),
    ))
    if not total_lchs.empty:
        fig.add_trace(go.Scatter(
            x=total_lchs["SY"], y=total_lchs["IND_VALUE"], mode="lines+markers",
            name="Lynn Classical", line=dict(color=LCHS_COLOR, width=2, dash="dash"),
        ))
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                      yaxis_title="$ per pupil", xaxis_title="Fiscal Year")
    with c2:
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Spending breakdown by category (latest year)
# ---------------------------------------------------------------------------

st.header("Spending Breakdown by Category")

latest_year = int(lehs_exp["SY"].max())
st.caption(f"Fiscal Year {latest_year}")

# Combine instructional + non-instructional spending across all funding sources
breakdown = lehs_exp[
    (lehs_exp["SY"] == latest_year)
    & (lehs_exp["IND_CAT"].str.contains("Expenditures", na=False))
    & (~lehs_exp["IND_CAT"].str.startswith("Sub-Total"))
    & (lehs_exp["IND_CAT"] != "Total A+B+C")
].copy()

if not breakdown.empty:
    # Aggregate by IND_SUBCAT across funding sources
    agg = breakdown.groupby("IND_SUBCAT")["IND_VALUE"].sum().reset_index().sort_values("IND_VALUE", ascending=True)
    fig = px.bar(agg, x="IND_VALUE", y="IND_SUBCAT", orientation="h",
                 color_discrete_sequence=[LEHS_NAVY],
                 text=agg["IND_VALUE"].apply(lambda x: f"${x:,.0f}"))
    fig.update_traces(textposition="outside")
    fig.update_layout(**DEFAULT_LAYOUT, xaxis_tickformat="$,.0f",
                       xaxis_title="$ per pupil", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Federal vs State/Local
# ---------------------------------------------------------------------------

st.header("Funding Source — Federal vs. State & Local")

fund_trend = lehs_exp[
    lehs_exp["IND_CAT"].str.contains("Expenditures", na=False)
    & ~lehs_exp["IND_CAT"].str.startswith("Sub-Total")
    & (lehs_exp["IND_CAT"] != "Total A+B+C")
].copy()
fund_trend["Source"] = fund_trend["IND_CAT"].apply(
    lambda x: "Federal" if "Federal" in x else "State & Local"
)
fund_summary = fund_trend.groupby(["SY", "Source"])["IND_VALUE"].sum().reset_index()

if not fund_summary.empty:
    fig = px.bar(
        fund_summary, x="SY", y="IND_VALUE", color="Source", barmode="stack",
        color_discrete_map={"Federal": LEHS_GOLD, "State & Local": LEHS_NAVY},
    )
    fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                       yaxis_title="$ per pupil", xaxis_title="Fiscal Year")
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Teacher salaries
# ---------------------------------------------------------------------------

st.header("Teacher Compensation")

def _ind(df: pd.DataFrame, subcat: str) -> pd.DataFrame:
    return df[
        (df["IND_CAT"] == "Teacher Salaries") & (df["IND_SUBCAT"] == subcat)
    ].sort_values("SY")

salary = _ind(lehs_exp, "Average Teacher Salary")
salary_l = _ind(lchs_exp, "Average Teacher Salary")
teach_per_100 = _ind(lehs_exp, "Teachers per 100 FTE students")
teach_per_100_l = _ind(lchs_exp, "Teachers per 100 FTE students")

c1, c2 = st.columns(2)
if not salary.empty:
    latest_sal = salary.iloc[-1]
    with c1:
        m1, m2 = st.columns(2)
        with m1:
            st.metric(f"LEHS Avg Salary ({int(latest_sal['SY'])})",
                      f"${latest_sal['IND_VALUE']:,.0f}")
        if not salary_l.empty:
            with m2:
                latest_l = salary_l.iloc[-1]
                st.metric(f"LCHS Avg Salary ({int(latest_l['SY'])})",
                          f"${latest_l['IND_VALUE']:,.0f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=salary["SY"], y=salary["IND_VALUE"],
                                 mode="lines+markers", name="Lynn English",
                                 line=dict(color=LEHS_NAVY, width=3)))
        if not salary_l.empty:
            fig.add_trace(go.Scatter(x=salary_l["SY"], y=salary_l["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Classical",
                                     line=dict(color=LCHS_COLOR, width=2, dash="dash")))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                          yaxis_title="Average salary",
                          title="Average teacher salary trend")
        st.plotly_chart(fig, use_container_width=True)

if not teach_per_100.empty:
    latest_r = teach_per_100.iloc[-1]
    with c2:
        m1, m2 = st.columns(2)
        with m1:
            st.metric(f"LEHS Teachers/100 ({int(latest_r['SY'])})",
                      f"{latest_r['IND_VALUE']:.1f}")
        if not teach_per_100_l.empty:
            with m2:
                latest_lr = teach_per_100_l.iloc[-1]
                st.metric(f"LCHS Teachers/100 ({int(latest_lr['SY'])})",
                          f"{latest_lr['IND_VALUE']:.1f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=teach_per_100["SY"], y=teach_per_100["IND_VALUE"],
                                 mode="lines+markers", name="Lynn English",
                                 line=dict(color=LEHS_NAVY, width=3)))
        if not teach_per_100_l.empty:
            fig.add_trace(go.Scatter(x=teach_per_100_l["SY"], y=teach_per_100_l["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Classical",
                                     line=dict(color=LCHS_COLOR, width=2, dash="dash")))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Teachers per 100 students",
                          title="Staffing intensity trend")
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Lynn district context
# ---------------------------------------------------------------------------

st.header("Lynn Public Schools — District Context")

if not dist_exp.empty:
    d = dist_exp[dist_exp["DIST_CODE"] == LYNN_DISTRICT_CODE].copy()
    d["IND_VALUE"] = pd.to_numeric(d["IND_VALUE"], errors="coerce")

    total_district = d[d["IND_SUBCAT"].str.contains("Total", case=False, na=False)].copy()
    if not total_district.empty:
        latest_d = total_district[total_district["SY"] == total_district["SY"].max()]
        st.dataframe(
            latest_d[["IND_CAT", "IND_SUBCAT", "IND_VALUE"]].assign(
                **{"$": latest_d["IND_VALUE"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—")}
            )[["IND_CAT", "IND_SUBCAT", "$"]].rename(columns={
                "IND_CAT": "Category", "IND_SUBCAT": "Indicator",
            }),
            use_container_width=True, hide_index=True,
        )

st.divider()

st.subheader("Cost-per-outcome (derived)")
st.caption(
    "Ratios that connect spending to outcomes — $ spent per graduate, per "
    "college-bound student. Built from the master panel that joins finance "
    "to DART graduation and college-enrollment indicators. Available on the "
    "**Correlation Lab** page where you can explore spending-vs-outcome "
    "relationships directly."
)

