"""Section 7 — Finance & Resource Allocation."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY
from utils.constants import IMAGES_DIR, LCHS_SCHOOL_CODE, LEHS_SCHOOL_CODE, LYNN_DISTRICT_CODE
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

# Three-school visual identity strip — the rest of this section's metrics
# trio (LEHS, LCHS, Lynn Tech) maps directly to these logos in the same
# left-to-right order.
_t_l, _t_m, _t_r = st.columns(3)
with _t_l:
    st.image(str(IMAGES_DIR / "lehs-bulldog.png"), width=70, caption="Lynn English")
with _t_m:
    st.image(str(IMAGES_DIR / "lchs-rams.png"), width=70, caption="Lynn Classical")
with _t_r:
    st.image(str(IMAGES_DIR / "lynn-tech-logo.png"), width=70, caption="Lynn Tech")

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
# Phase C — Teacher Salary in Gateway-City context. The per-school comparison
# above (LEHS vs LCHS vs Lynn Tech) is useful but every Lynn school operates
# under the same district pay scale — so it understates variation. The peer
# comparison below puts Lynn's average teacher salary against the other 25
# MA Gateway Cities, where contract negotiations vary independently.
# ---------------------------------------------------------------------------

st.header("Teacher Pay vs. Gateway-City Peers")
st.markdown(
    "Average teacher salary is set at the **district** level — every Lynn "
    "school pays from the same scale. To see whether Lynn pays competitively, "
    "the comparison that matters is against other MA Gateway Cities: similar "
    "demographic profile, similar fiscal pressures, independently negotiated "
    "contracts."
)

if not dist_exp.empty:
    dsal = dist_exp[
        (dist_exp["IND_CAT"] == "Teacher Salaries")
        & (dist_exp["IND_SUBCAT"] == "Average Teacher Salary")
    ].copy()
    dsal["IND_VALUE"] = pd.to_numeric(dsal["IND_VALUE"], errors="coerce")
    dsal["SY"] = pd.to_numeric(dsal["SY"], errors="coerce").astype("Int64")
    dsal = dsal.dropna(subset=["IND_VALUE", "SY"])

    if dsal.empty:
        st.info("No district-level teacher-salary rows found.")
    else:
        latest_dy = int(dsal["SY"].max())
        latest_dsal = dsal[dsal["SY"] == latest_dy].copy()
        lynn_row = latest_dsal[latest_dsal["DIST_CODE"] == LYNN_DISTRICT_CODE]
        peer_med = latest_dsal["IND_VALUE"].median()
        peer_max = latest_dsal["IND_VALUE"].max()
        peer_min = latest_dsal["IND_VALUE"].min()

        c1, c2, c3 = st.columns(3)
        if not lynn_row.empty:
            lynn_sal = lynn_row.iloc[0]["IND_VALUE"]
            rank = int((latest_dsal["IND_VALUE"] > lynn_sal).sum() + 1)
            total_n = len(latest_dsal)
            with c1:
                st.metric(
                    f"Lynn avg teacher salary (FY {latest_dy})",
                    f"${lynn_sal:,.0f}",
                    f"Rank {rank} of {total_n} Gateway Cities",
                )
            with c2:
                diff = lynn_sal - peer_med
                st.metric(
                    "vs. Gateway peer median",
                    f"${peer_med:,.0f}",
                    f"{diff:+,.0f} vs Lynn",
                )
        with c3:
            st.metric(
                "Gateway range",
                f"${peer_min/1000:.0f}K – ${peer_max/1000:.0f}K",
                help="Lowest to highest average teacher salary across the 26 MA Gateway-City districts.",
            )

        # Peer ranking — latest year
        ranked = latest_dsal.sort_values("IND_VALUE", ascending=True).copy()
        ranked["is_lynn"] = ranked["DIST_CODE"] == LYNN_DISTRICT_CODE
        ranked["label"] = ranked["IND_VALUE"].apply(lambda x: f"${x:,.0f}")

        st.markdown(f"**Gateway-City average teacher salaries — FY {latest_dy}**")
        fig = px.bar(
            ranked, x="IND_VALUE", y="DIST_NAME", orientation="h", text="label",
            color="is_lynn",
            color_discrete_map={True: LEHS_GOLD, False: LEHS_NAVY},
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.add_vline(
            x=peer_med, line_dash="dash", line_color="#455A64",
            annotation_text=f"Peer median ${peer_med:,.0f}",
            annotation_position="top",
        )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            xaxis_tickprefix="$", xaxis_tickformat=",.0f",
            xaxis_title="Average teacher salary",
            yaxis_title="",
            showlegend=False,
            height=max(420, 22 * len(ranked)),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Trend — Lynn vs peer median over time
        peer_trend = (
            dsal.groupby("SY")["IND_VALUE"]
            .median()
            .reset_index()
            .rename(columns={"IND_VALUE": "PeerMedian"})
        )
        lynn_trend = (
            dsal[dsal["DIST_CODE"] == LYNN_DISTRICT_CODE][["SY", "IND_VALUE"]]
            .rename(columns={"IND_VALUE": "Lynn"})
        )
        trend = peer_trend.merge(lynn_trend, on="SY", how="outer").sort_values("SY")
        if not trend.empty and len(trend) > 1:
            st.markdown("**Trend — Lynn vs. Gateway peer median**")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trend["SY"], y=trend["Lynn"], mode="lines+markers",
                name="Lynn", line=dict(color=LEHS_GOLD, width=3),
            ))
            fig.add_trace(go.Scatter(
                x=trend["SY"], y=trend["PeerMedian"], mode="lines+markers",
                name="Gateway peer median", line=dict(color=LEHS_NAVY, width=2, dash="dash"),
            ))
            fig.update_layout(
                **DEFAULT_LAYOUT,
                yaxis_tickprefix="$", yaxis_tickformat=",.0f",
                yaxis_title="Average teacher salary",
                xaxis_title="Fiscal Year",
                legend_title="",
            )
            st.plotly_chart(fig, use_container_width=True)

        st.caption(
            "Average teacher salary reflects the joint effect of pay scale and "
            "workforce experience mix — a district with a more senior workforce "
            "will show a higher average even on the same scale. Pair with "
            "*% Experienced Teachers* on the Teachers & Workforce page to "
            "separate the two."
        )

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

# ---------------------------------------------------------------------------
# Chapter 70 — state aid + required spending. District-level only (Chapter 70
# is a district funding formula, not a school-level allocation).
# ---------------------------------------------------------------------------

st.header("Chapter 70 — State Aid & Required Spending")
st.markdown(
    "**Chapter 70** is Massachusetts's main K–12 funding formula. The "
    "**foundation budget** is the state-determined *minimum* a district must "
    "spend, computed from enrollment, grade levels, and student demographics "
    "(low-income, ELL, special ed). **Required Net School Spending (NSS)** is "
    "what the district is legally obligated to contribute toward that floor. "
    "**Actual NSS** is what the district actually spent. Spending *above* the "
    "required minimum means the city is investing beyond the state floor; "
    "spending *below* triggers state intervention."
)

ch70 = load_dataset("chapter70_aid")
if ch70.empty:
    st.info(
        "Chapter 70 data not yet processed — run `python scripts/01_download_e2c.py`."
    )
else:
    ch70["SY"] = pd.to_numeric(ch70["SY"], errors="coerce").astype("Int64")
    for col in ["REQ_NSS_AMT", "ACTL_NSS_AMT", "OVR_UND_REQ_AMT", "FDN_BDGT_AMT",
                "ACTL_NSS_PCT_OF_REQ_NSS", "ACTL_NSS_PCT_OF_FDN_BUDG"]:
        if col in ch70.columns:
            ch70[col] = pd.to_numeric(ch70[col], errors="coerce")

    lynn_ch70 = ch70[ch70["DIST_CODE"] == LYNN_DISTRICT_CODE].sort_values("SY")

    if lynn_ch70.empty:
        st.info("No Chapter 70 rows found for Lynn — check DIST_CODE filter.")
    else:
        latest_year = int(lynn_ch70["SY"].max())
        latest = lynn_ch70[lynn_ch70["SY"] == latest_year].iloc[0]
        prior = lynn_ch70[lynn_ch70["SY"] == latest_year - 1]
        prior = prior.iloc[0] if not prior.empty else None

        # Hero metrics
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(
                f"Foundation Budget (SY {sy_label(latest_year)})",
                f"${latest['FDN_BDGT_AMT']/1e6:.1f}M" if pd.notna(latest["FDN_BDGT_AMT"]) else "—",
                help="State-set minimum spending floor for Lynn, given the city's student population.",
            )
        with c2:
            st.metric(
                "Required NSS",
                f"${latest['REQ_NSS_AMT']/1e6:.1f}M" if pd.notna(latest["REQ_NSS_AMT"]) else "—",
                help="What Lynn is legally required to spend on schools this year.",
            )
        with c3:
            st.metric(
                "Actual NSS",
                f"${latest['ACTL_NSS_AMT']/1e6:.1f}M" if pd.notna(latest["ACTL_NSS_AMT"]) else "—",
                help="What Lynn actually spent on schools.",
            )
        with c4:
            ovr_und = latest["OVR_UND_REQ_AMT"]
            if pd.notna(ovr_und):
                label = "Over required" if ovr_und >= 0 else "Under required"
                delta_str = None
                if prior is not None and pd.notna(prior["OVR_UND_REQ_AMT"]):
                    diff = (ovr_und - prior["OVR_UND_REQ_AMT"]) / 1e6
                    delta_str = f"{diff:+.1f}M vs SY {sy_label(latest_year - 1)}"
                st.metric(
                    label,
                    f"${abs(ovr_und)/1e6:.1f}M",
                    delta_str,
                    help="Actual NSS minus Required NSS. Positive = Lynn invested above the state-required floor.",
                )

        # Trend — foundation budget vs required NSS vs actual NSS, Lynn over time
        st.markdown(f"**Lynn's foundation budget vs. required vs. actual spending (SY 2008 – {sy_label(latest_year)})**")
        trend_long = lynn_ch70.melt(
            id_vars=["SY"],
            value_vars=["FDN_BDGT_AMT", "REQ_NSS_AMT", "ACTL_NSS_AMT"],
            var_name="Series", value_name="Amount",
        ).dropna(subset=["Amount"])
        SERIES_LABELS = {
            "FDN_BDGT_AMT": "Foundation Budget",
            "REQ_NSS_AMT":  "Required NSS",
            "ACTL_NSS_AMT": "Actual NSS",
        }
        SERIES_COLORS = {
            "Foundation Budget": "#90A4AE",  # gray — the floor
            "Required NSS":      LEHS_NAVY,
            "Actual NSS":        LEHS_GOLD,
        }
        trend_long["Series"] = trend_long["Series"].map(SERIES_LABELS)
        fig = px.line(
            trend_long, x="SY", y="Amount", color="Series", markers=True,
            color_discrete_map=SERIES_COLORS,
        )
        fig.update_layout(
            **DEFAULT_LAYOUT,
            yaxis_title="Dollars",
            yaxis_tickprefix="$", yaxis_tickformat=".2s",
            xaxis_title="School Year",
            legend_title="",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "The Student Opportunity Act of 2019 substantially increased the "
            "foundation budget formula's weight for low-income and ELL students "
            "— Gateway Cities like Lynn benefited disproportionately."
        )

        # Gateway-city peer comparison — actual NSS vs required, latest year
        peers_ch70 = ch70[
            (ch70["SY"] == latest_year)
            & (ch70["DIST_CODE"] != "00000000")  # exclude state totals
        ].dropna(subset=["OVR_UND_REQ_AMT"]).copy()
        if not peers_ch70.empty:
            peers_ch70["pct_of_req"] = peers_ch70["ACTL_NSS_PCT_OF_REQ_NSS"]
            peers_ch70 = peers_ch70.sort_values("pct_of_req", ascending=True)
            peers_ch70["is_lynn"] = peers_ch70["DIST_CODE"] == LYNN_DISTRICT_CODE
            peers_ch70["label"] = peers_ch70.apply(
                lambda r: f"{r['pct_of_req']*100:.0f}%", axis=1
            )

            st.markdown(f"**Gateway-City peers — Actual NSS as % of Required (SY {sy_label(latest_year)})**")
            fig = px.bar(
                peers_ch70, x="pct_of_req", y="DIST_NAME", orientation="h", text="label",
                color="is_lynn",
                color_discrete_map={True: LEHS_GOLD, False: LEHS_NAVY},
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.add_vline(
                x=1.0, line_dash="dash", line_color="#455A64",
                annotation_text="Required minimum (100%)",
                annotation_position="top",
            )
            fig.update_layout(
                **DEFAULT_LAYOUT,
                xaxis_tickformat=".0%",
                xaxis_title="Actual NSS as % of Required NSS",
                yaxis_title="",
                showlegend=False,
                height=max(420, 22 * len(peers_ch70)),
            )
            st.plotly_chart(fig, use_container_width=True)
            st.caption(
                "Every Gateway City spends at least the required minimum (everyone "
                "is at or above 100%) — districts under 100% face state intervention. "
                "How *far* above the floor each city goes reflects local fiscal "
                "capacity and political will."
            )

        st.caption(
            f"Source: DESE Chapter 70 Foundation Budget & Net School Spending. "
            f"Data lags by ~2 years; latest available is SY {sy_label(latest_year)}. "
            "District-level only — Chapter 70 is a district funding formula, "
            "not a school-level allocation."
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

