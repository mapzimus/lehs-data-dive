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

# Per-school chart contrasts compare LEHS against Lynn's two other large
# comprehensive high schools: Lynn Classical (LCHS) and Lynn Vocational
# Technical Institute (LVTI / Lynn Tech). Same district, same budget rules,
# similar enrollment scale — meaningful side-by-side comparison.
LVTI_SCHOOL_CODE = "01630605"
LCHS_COLOR = LEHS_GOLD
LVTI_COLOR = "#26A69A"  # teal — distinct from navy + gold

st.set_page_config(page_title="Finance | LEHS", page_icon="💰", layout="wide")
sidebar_attribution()

st.title("Finance & Resource Allocation")
st.markdown(
    "School-level expenditures by category, teacher compensation, and "
    "federal-vs-state-and-local funding split — drawn from DESE's School "
    "Expenditures by Spending Category dataset. Where chart contrasts "
    "appear, they include Lynn Classical (LCHS) and Lynn Tech (LVTI) "
    "alongside LEHS — same district, same budget rules."
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

lvti_exp = school_exp[school_exp["ORG_CODE"] == LVTI_SCHOOL_CODE].copy()
lvti_exp["IND_VALUE"] = pd.to_numeric(lvti_exp["IND_VALUE"], errors="coerce")

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
total_lvti = _total_per_pupil(lvti_exp)

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
            st.metric(
                f"LCHS Per Pupil (FY {int(latest_l['SY'])})",
                f"${latest_l['IND_VALUE']:,.0f}",
            )
        if not total_lvti.empty:
            latest_t = total_lvti.iloc[-1]
            st.metric(
                f"Lynn Tech Per Pupil (FY {int(latest_t['SY'])})",
                f"${latest_t['IND_VALUE']:,.0f}",
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
    if not total_lvti.empty:
        fig.add_trace(go.Scatter(
            x=total_lvti["SY"], y=total_lvti["IND_VALUE"], mode="lines+markers",
            name="Lynn Tech", line=dict(color=LVTI_COLOR, width=2, dash="dot"),
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
salary_t = _ind(lvti_exp, "Average Teacher Salary")
teach_per_100 = _ind(lehs_exp, "Teachers per 100 FTE students")
teach_per_100_l = _ind(lchs_exp, "Teachers per 100 FTE students")
teach_per_100_t = _ind(lvti_exp, "Teachers per 100 FTE students")

c1, c2 = st.columns(2)
if not salary.empty:
    latest_sal = salary.iloc[-1]
    with c1:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(f"LEHS ({int(latest_sal['SY'])})",
                      f"${latest_sal['IND_VALUE']:,.0f}")
        if not salary_l.empty:
            with m2:
                latest_l = salary_l.iloc[-1]
                st.metric(f"LCHS ({int(latest_l['SY'])})",
                          f"${latest_l['IND_VALUE']:,.0f}")
        if not salary_t.empty:
            with m3:
                latest_t = salary_t.iloc[-1]
                st.metric(f"Lynn Tech ({int(latest_t['SY'])})",
                          f"${latest_t['IND_VALUE']:,.0f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=salary["SY"], y=salary["IND_VALUE"],
                                 mode="lines+markers", name="Lynn English",
                                 line=dict(color=LEHS_NAVY, width=3)))
        if not salary_l.empty:
            fig.add_trace(go.Scatter(x=salary_l["SY"], y=salary_l["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Classical",
                                     line=dict(color=LCHS_COLOR, width=2, dash="dash")))
        if not salary_t.empty:
            fig.add_trace(go.Scatter(x=salary_t["SY"], y=salary_t["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Tech",
                                     line=dict(color=LVTI_COLOR, width=2, dash="dot")))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_tickformat="$,.0f",
                          yaxis_title="Average salary")
        st.plotly_chart(fig, use_container_width=True)

if not teach_per_100.empty:
    latest_r = teach_per_100.iloc[-1]
    with c2:
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric(f"LEHS ({int(latest_r['SY'])})",
                      f"{latest_r['IND_VALUE']:.1f}")
        if not teach_per_100_l.empty:
            with m2:
                latest_lr = teach_per_100_l.iloc[-1]
                st.metric(f"LCHS ({int(latest_lr['SY'])})",
                          f"{latest_lr['IND_VALUE']:.1f}")
        if not teach_per_100_t.empty:
            with m3:
                latest_tr = teach_per_100_t.iloc[-1]
                st.metric(f"Lynn Tech ({int(latest_tr['SY'])})",
                          f"{latest_tr['IND_VALUE']:.1f}")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=teach_per_100["SY"], y=teach_per_100["IND_VALUE"],
                                 mode="lines+markers", name="Lynn English",
                                 line=dict(color=LEHS_NAVY, width=3)))
        if not teach_per_100_l.empty:
            fig.add_trace(go.Scatter(x=teach_per_100_l["SY"], y=teach_per_100_l["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Classical",
                                     line=dict(color=LCHS_COLOR, width=2, dash="dash")))
        if not teach_per_100_t.empty:
            fig.add_trace(go.Scatter(x=teach_per_100_t["SY"], y=teach_per_100_t["IND_VALUE"],
                                     mode="lines+markers", name="Lynn Tech",
                                     line=dict(color=LVTI_COLOR, width=2, dash="dot")))
        fig.update_layout(**DEFAULT_LAYOUT, yaxis_title="Teachers per 100 students")
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

st.header("Spending vs. Outcomes — Gateway-City Districts")
st.markdown(
    "**Does more money buy better outcomes?** The two charts below pair each "
    "MA Gateway-City district's per-pupil spending with its 4-year graduation "
    "rate (top) and its non-grad / dropout share (bottom). Lynn is highlighted; "
    "the dashed line is an OLS fit across all 26 districts."
)

import json  # noqa: E402
from pathlib import Path  # noqa: E402

from utils.constants import PROCESSED_DIR  # noqa: E402

_peer_path: Path = PROCESSED_DIR / "_peer_schools.json"
gateway_codes: dict[str, str] = {}
if _peer_path.exists():
    _peers = json.loads(_peer_path.read_text())
    gateway_codes = {
        city: info["district_code"]
        for city, info in (_peers.get("gateway_main_hs") or {}).items()
        if info.get("district_code")
    }

if not gateway_codes:
    st.info(
        "Gateway-city district codes not available yet — run "
        "`python scripts/07_identify_peer_schools.py` first."
    )
else:
    # Pull per-pupil "Total Expenditures" for each gateway district, latest SY
    pp = dist_exp[
        (dist_exp["IND_CAT"] == "Expenditures Per Pupil")
        & (dist_exp["IND_SUBCAT"] == "Total Expenditures")
        & (dist_exp["DIST_CODE"].isin(gateway_codes.values()))
    ].copy()
    pp["IND_VALUE"] = pd.to_numeric(pp["IND_VALUE"], errors="coerce")
    pp = pp.sort_values("SY").groupby("DIST_CODE").tail(1)[
        ["DIST_CODE", "DIST_NAME", "SY", "IND_VALUE"]
    ].rename(columns={"IND_VALUE": "per_pupil", "SY": "fin_year"})

    # Graduation rate — district aggregate, all students, latest year, 4-yr adjusted
    grad = load_dataset("graduation_rates")
    if not grad.empty:
        grad_d = grad[
            (grad["ORG_TYPE"] == "District")
            & (grad["STU_GRP"] == "All Students")
            & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
            & (grad["DIST_CODE"].isin(gateway_codes.values()))
        ].copy()
        grad_d["GRAD_PCT"] = pd.to_numeric(grad_d["GRAD_PCT"], errors="coerce")
        grad_d["DRPOUT_PCT"] = pd.to_numeric(grad_d.get("DRPOUT_PCT"), errors="coerce")
        grad_d = grad_d.sort_values("SY").groupby("DIST_CODE").tail(1)[
            ["DIST_CODE", "SY", "GRAD_PCT", "DRPOUT_PCT"]
        ].rename(columns={"SY": "grad_year"})

        joined = pp.merge(grad_d, on="DIST_CODE", how="inner")
        if not joined.empty:
            joined["is_lynn"] = joined["DIST_CODE"] == LYNN_DISTRICT_CODE
            joined["hover_label"] = (
                joined["DIST_NAME"]
                + " (FY " + joined["fin_year"].astype(int).astype(str)
                + " / SY " + joined["grad_year"].astype(int).astype(str) + ")"
            )

            def _scatter(y_col: str, y_label: str, ascending_is_good: bool):
                fig = px.scatter(
                    joined,
                    x="per_pupil",
                    y=y_col,
                    text="DIST_NAME",
                    trendline="ols",
                    custom_data=["hover_label", "is_lynn"],
                )
                # Color gateway dots gray, Lynn navy/gold
                colors = [
                    LEHS_GOLD if il else "#B0BEC5" for il in joined["is_lynn"]
                ]
                sizes = [16 if il else 10 for il in joined["is_lynn"]]
                fig.update_traces(
                    selector=dict(mode="markers+text"),
                    marker=dict(color=colors, size=sizes, line=dict(color=LEHS_NAVY, width=1)),
                    textposition="top center",
                    textfont=dict(size=10),
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        f"Per pupil: $%{{x:,.0f}}<br>{y_label}: %{{y:.0%}}<extra></extra>"
                    ),
                )
                fig.update_layout(
                    **DEFAULT_LAYOUT,
                    xaxis_tickformat="$,.0f",
                    yaxis_tickformat=".0%",
                    xaxis_title="Per-pupil total expenditure ($)",
                    yaxis_title=y_label,
                    title=f"{y_label} vs. per-pupil spending — MA Gateway Cities",
                    showlegend=False,
                )
                return fig

            st.plotly_chart(
                _scatter("GRAD_PCT", "4-Year Adjusted Graduation Rate", True),
                use_container_width=True,
            )
            if joined["DRPOUT_PCT"].notna().any():
                st.plotly_chart(
                    _scatter("DRPOUT_PCT", "Dropout Rate", False),
                    use_container_width=True,
                )

            # Quick numeric: spread of per-pupil and outcome ranks for Lynn
            lynn_row = joined[joined["is_lynn"]]
            if not lynn_row.empty:
                lynn_pp = lynn_row.iloc[0]["per_pupil"]
                lynn_grad = lynn_row.iloc[0]["GRAD_PCT"]
                pp_rank = int((joined["per_pupil"] > lynn_pp).sum()) + 1
                grad_rank = int((joined["GRAD_PCT"] > lynn_grad).sum()) + 1
                n = len(joined)
                st.markdown(
                    f"**Lynn's standing among gateway districts:** spends "
                    f"${lynn_pp:,.0f}/pupil (ranks **{pp_rank} of {n}** by spending) "
                    f"and graduates **{lynn_grad:.0%}** in 4 years "
                    f"(ranks **{grad_rank} of {n}** by graduation). If the dot "
                    f"sits *above* the trendline, Lynn is getting more graduation "
                    f"per dollar than peers at similar spending; *below* means less."
                )
        else:
            st.info("No districts had both per-pupil and graduation data for the same year window.")

# >>> auto: csv downloads <<<
try:
    from utils.charts import data_downloads_panel as _dl
    _dl({
        'School expenditures': school_exp,
        'District expenditures': dist_exp,
    })
except NameError:
    # one of the dataset variables wasn't defined on this run
    pass

