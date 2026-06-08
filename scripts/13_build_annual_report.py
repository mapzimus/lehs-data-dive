"""
Build the 'State of LEHS 2026' annual report PDF.

Pulls cleaned-up versions of each dashboard chart, exports them to PNG via
Plotly + Kaleido, and lays out a multi-page ReportLab document at
reports/state_of_lehs_2026.pdf.

Sections mirror the dashboard:
  1. Cover
  2. Executive summary
  3. School Profile
  4. Academic Performance
  5. ELL Pipeline (2 pages — flagship topic)
  6. College & Career
  7. Success After HS
  8. Teachers & Workforce
  9. Finance
 10. Discipline & Climate
 11. Community Context
 12. Methodology & sources

Run with:
    python scripts/13_build_annual_report.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.constants import (  # noqa: E402
    LCHS_SCHOOL_CODE,
    LEHS_NAVY,
    LEHS_GOLD,
    LEHS_SCHOOL_CODE,
    LYNN_DISTRICT_CODE,
    PROCESSED_DIR,
    REPORTS_DIR,
)

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR = REPORTS_DIR / "_chart_pngs"
TMP_DIR.mkdir(exist_ok=True)
OUT_PDF = REPORTS_DIR / "state_of_lehs_2026.pdf"

# Plotly export config
DEFAULT_LAYOUT = dict(
    template="simple_white",
    font=dict(family="sans-serif", size=14, color=LEHS_NAVY),
    margin=dict(l=50, r=20, t=60, b=50),
)

styles = getSampleStyleSheet()
NAVY = colors.HexColor(LEHS_NAVY)
GOLD = colors.HexColor(LEHS_GOLD)

H1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=NAVY,
                     fontSize=22, spaceAfter=14)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], textColor=NAVY,
                     fontSize=16, spaceAfter=10)
BODY = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=11,
                       leading=15, spaceAfter=8)
CAPTION = ParagraphStyle("Caption", parent=styles["BodyText"], fontSize=9,
                          leading=11, textColor=colors.HexColor("#607D8B"),
                          spaceAfter=10)


# ---------------------------------------------------------------------------
# Plotly → PNG helper
# ---------------------------------------------------------------------------

def fig_to_png(fig: go.Figure, slug: str, width: int = 900, height: int = 500) -> Path:
    fig.update_layout(**DEFAULT_LAYOUT)
    out = TMP_DIR / f"{slug}.png"
    try:
        pio.write_image(fig, str(out), format="png", width=width, height=height, scale=2)
    except Exception as e:
        print(f"  [WARN] kaleido export failed for {slug}: {e}")
        return None
    return out


def embed(slug: str, fig: go.Figure, w: float = 6.5, h: float = 3.5) -> list:
    """Return ReportLab flowables for embedding a chart, or empty list on failure."""
    p = fig_to_png(fig, slug)
    if not p or not p.exists():
        return [Paragraph(f"<i>Chart not available: {slug}</i>", CAPTION)]
    img = Image(str(p), width=w * inch, height=h * inch)
    return [img, Spacer(1, 6)]


# ---------------------------------------------------------------------------
# Data loaders (lightweight — avoid Streamlit)
# ---------------------------------------------------------------------------

def _read(name: str) -> pd.DataFrame:
    p = PROCESSED_DIR / f"{name}.parquet"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_parquet(p)


def _filter_school(df: pd.DataFrame, code: str) -> pd.DataFrame:
    if df.empty:
        return df
    if "ORG_CODE" in df.columns:
        return df[df["ORG_CODE"] == code]
    return df


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def cover_page() -> list:
    flow = []
    flow.append(Spacer(1, 2 * inch))
    flow.append(Paragraph("State of Lynn English High", H1))
    flow.append(Paragraph("Annual Data Report — School Year 2025-26", H2))
    flow.append(Spacer(1, 1.4 * inch))
    flow.append(Paragraph(
        "An independent data narrative drawn from public DESE, federal CRDC, "
        "Census ACS, IPEDS, EPA, and CDC sources. Companion to "
        "<b>lynn-data-dive.streamlit.app</b>.",
        BODY,
    ))
    flow.append(Spacer(1, 0.8 * inch))
    flow.append(Paragraph(f"Compiled {date.today().isoformat()} · Maxwell Howe", CAPTION))
    flow.append(PageBreak())
    return flow


def executive_summary() -> list:
    flow = [Paragraph("Executive Summary", H1)]
    enr = _read("enrollment_demographics")
    lehs = _filter_school(enr, LEHS_SCHOOL_CODE)
    if not lehs.empty:
        latest = lehs.sort_values("SY").iloc[-1]
        rows = [
            ["Total enrollment", f"{int(latest.get('TOTAL_CNT', 0)):,}"],
            ["% English learners",
             f"{float(latest.get('EL_PCT', 0)):.0%}"],
            ["% Low income",
             f"{float(latest.get('LI_PCT', 0)):.0%}"],
            ["% Hispanic/Latino",
             f"{float(latest.get('HL_PCT', 0)):.0%}"],
            ["% Black or African American",
             f"{float(latest.get('BAA_PCT', 0)):.0%}"],
            ["% First language not English",
             f"{float(latest.get('FLNE_PCT', 0)):.0%}"],
        ]
        t = Table(rows, colWidths=[3.5 * inch, 2.0 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GOLD),
            ("TEXTCOLOR",  (0, 0), (-1, -1), NAVY),
            ("FONTNAME",   (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",   (0, 0), (-1, -1), 11),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#CFD8DC")),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ]))
        flow.append(t)
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(
        "Lynn English serves a student body whose share of English learners and "
        "first-language-not-English students puts it among the most linguistically "
        "diverse comprehensive high schools in Massachusetts. This report tracks "
        "the data that matters: who attends, how they perform on state and "
        "federal accountability measures, what happens after graduation, and what "
        "the surrounding community looks like.",
        BODY,
    ))
    flow.append(PageBreak())
    return flow


def school_profile_section() -> list:
    flow = [Paragraph("1. School Profile", H1)]
    enr = _read("enrollment_demographics")
    lehs = _filter_school(enr, LEHS_SCHOOL_CODE).sort_values("SY")
    if not lehs.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=lehs["SY"], y=lehs["TOTAL_CNT"],
                                  mode="lines+markers", name="Enrollment",
                                  line=dict(color=LEHS_NAVY, width=3)))
        fig.update_layout(title="LEHS total enrollment",
                          yaxis_title="Students", xaxis_title="SY")
        flow.extend(embed("enrollment_trend", fig))
    flow.append(Paragraph(
        "Enrollment over time. Lynn English is one of two comprehensive high "
        "schools in Lynn Public Schools, alongside Lynn Classical.",
        CAPTION,
    ))
    flow.append(PageBreak())
    return flow


def academic_perf_section() -> list:
    flow = [Paragraph("2. Academic Performance", H1)]
    mcas = _read("mcas_achievement")
    if not mcas.empty:
        m = mcas[(mcas["ORG_CODE"] == LEHS_SCHOOL_CODE)
                  & (mcas["TEST_GRADE"].astype(str) == "10")
                  & (mcas["STU_GRP"] == "All Students")].copy()
        m["M_PLUS_E_PCT"] = pd.to_numeric(m["M_PLUS_E_PCT"], errors="coerce")
        if not m.empty:
            fig = px.line(m.sort_values("SY"), x="SY", y="M_PLUS_E_PCT",
                          color="SUBJECT_CODE", markers=True,
                          color_discrete_map={"ELA": "#1976D2", "MATH": "#D32F2F", "SCI": "#388E3C"},
                          title="LEHS — Grade 10 MCAS: % Meeting + Exceeding")
            fig.update_layout(yaxis_tickformat=".0%")
            flow.extend(embed("mcas_g10_trend", fig))
    flow.append(PageBreak())
    return flow


def ell_section() -> list:
    flow = [Paragraph("3. ELL Pipeline (Flagship)", H1)]
    enr = _read("enrollment_demographics")
    lehs = _filter_school(enr, LEHS_SCHOOL_CODE).sort_values("SY")
    if not lehs.empty:
        for col in ["EL_PCT", "FLNE_PCT"]:
            lehs[col] = pd.to_numeric(lehs[col], errors="coerce")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=lehs["SY"], y=lehs["EL_PCT"],
                                  mode="lines+markers", name="% English Learners",
                                  line=dict(color="#388E3C", width=3)))
        fig.add_trace(go.Scatter(x=lehs["SY"], y=lehs["FLNE_PCT"],
                                  mode="lines+markers",
                                  name="% First-lang not English",
                                  line=dict(color="#0277BD", width=3)))
        fig.update_layout(title="LEHS — ELL + FLNE share over time",
                          yaxis_tickformat=".0%")
        flow.extend(embed("ell_share", fig))
    flow.append(Paragraph(
        "Lynn English's ELL share is among the highest in the state. The "
        "first-language-not-English line is the leading indicator: many of "
        "these students will be re-classified to ELL after intake testing.",
        CAPTION,
    ))
    flow.append(PageBreak())
    return flow


def college_section() -> list:
    flow = [Paragraph("4. College & Career", H1)]
    dart = _read("dart_success_after_hs")
    if not dart.empty:
        ap = dart[(dart["ORG_CODE"] == LEHS_SCHOOL_CODE)
                   & (dart["INDICATOR"].str.contains("AP test takers", case=False, na=False))
                   & (dart["STU_GRP"] == "All Students")].copy()
        ap["VALUE"] = pd.to_numeric(ap["VALUE"], errors="coerce")
        if not ap.empty:
            fig = px.line(ap.sort_values("SY"), x="SY", y="VALUE", markers=True,
                          color="INDICATOR",
                          title="LEHS — AP indicators")
            fig.update_layout(yaxis_title="%", yaxis_tickformat=".0f")
            flow.extend(embed("ap_trend", fig))

    ipeds = _read("ipeds_destinations")
    if not ipeds.empty:
        top = ipeds.head(10)
        rows = [["Institution", "State", "Grad rate (150%)"]]
        for _, r in top.iterrows():
            gr = r.get("GRAD_RATE_150")
            rows.append([str(r.get("INSTITUTION", "—"))[:40],
                          str(r.get("STATE", "—") or "—"),
                          f"{gr:.0%}" if pd.notna(gr) else "—"])
        t = Table(rows, colWidths=[3.8 * inch, 0.8 * inch, 1.4 * inch])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
            ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ]))
        flow.append(Paragraph("Top destination colleges (IPEDS / College Scorecard)", H2))
        flow.append(t)
    flow.append(PageBreak())
    return flow


def success_section() -> list:
    flow = [Paragraph("5. Success After High School", H1)]
    grad = _read("graduation_rates")
    if not grad.empty:
        g = grad[(grad["ORG_CODE"] == LEHS_SCHOOL_CODE)
                  & (grad["GRAD_RATE_TYPE"] == "4-Year Adjusted Cohort Graduation Rate")
                  & (grad["STU_GRP"] == "All Students")].copy()
        g["GRAD_PCT"] = pd.to_numeric(g["GRAD_PCT"], errors="coerce")
        if not g.empty:
            if g["GRAD_PCT"].max() > 1.5:
                g["GRAD_PCT"] = g["GRAD_PCT"] / 100
            fig = px.line(g.sort_values("SY"), x="SY", y="GRAD_PCT", markers=True,
                          title="LEHS — 4-year cohort graduation rate")
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(yaxis_tickformat=".0%")
            flow.extend(embed("grad_trend", fig))
    flow.append(PageBreak())
    return flow


def workforce_section() -> list:
    flow = [Paragraph("6. Teachers & Workforce", H1)]
    s = _read("staffing_race_gender")
    if not s.empty:
        s_lehs = s[(s["ORG_CODE"] == LEHS_SCHOOL_CODE)
                    & (s["JOBCLASS"].astype(str).str.lower() == "teacher")].copy()
        if not s_lehs.empty:
            latest = s_lehs.sort_values("SY").iloc[-1]
            rows = [["Group", "Headcount FTE"]]
            for col, label in [("WH_CNT", "White"), ("HL_CNT", "Hispanic/Latino"),
                                ("BAA_CNT", "Black/African American"),
                                ("AS_CNT", "Asian"), ("MNHL_CNT", "Multi-race")]:
                v = pd.to_numeric(latest.get(col), errors="coerce")
                rows.append([label, f"{v:.0f}" if pd.notna(v) else "—"])
            t = Table(rows, colWidths=[3.0 * inch, 2.0 * inch])
            t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), NAVY),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
                                    ("FONTSIZE", (0, 0), (-1, -1), 11)]))
            flow.append(Paragraph("LEHS teacher headcount by race/ethnicity (latest year)", H2))
            flow.append(t)
    flow.append(PageBreak())
    return flow


def finance_section() -> list:
    flow = [Paragraph("7. Finance", H1)]
    dexp = _read("district_expenditures")
    if not dexp.empty:
        d = dexp[dexp["DIST_CODE"] == LYNN_DISTRICT_CODE].copy()
        d["IND_VALUE"] = pd.to_numeric(d["IND_VALUE"], errors="coerce")
        pp = d[d["IND_CAT"].astype(str).str.contains("Per Pupil", case=False, na=False)
                & d["IND_SUBCAT"].astype(str).str.contains("Total Expenditures", case=False, na=False)]
        pp = pp.sort_values("SY")
        if not pp.empty:
            fig = px.line(pp, x="SY", y="IND_VALUE", markers=True,
                          title="Lynn district — per-pupil expenditure")
            fig.update_traces(line=dict(color=LEHS_NAVY, width=3))
            fig.update_layout(yaxis_tickformat="$,.0f")
            flow.extend(embed("per_pupil", fig))
    flow.append(PageBreak())
    return flow


def discipline_section() -> list:
    flow = [Paragraph("8. Discipline & Climate", H1)]
    att = _read("student_attendance")
    if not att.empty:
        a = att[(att["ORG_CODE"].isin([LEHS_SCHOOL_CODE, LCHS_SCHOOL_CODE]))
                 & (att["STU_GRP"] == "All Students")
                 & (att["ATTEND_PERIOD"] == "End of Year")].copy()
        a["PCT_CHRON_ABS_10"] = pd.to_numeric(a["PCT_CHRON_ABS_10"], errors="coerce")
        a["School"] = a["ORG_CODE"].map({LEHS_SCHOOL_CODE: "LEHS", LCHS_SCHOOL_CODE: "LCHS"})
        if not a.empty:
            fig = px.line(a.sort_values("SY"), x="SY", y="PCT_CHRON_ABS_10",
                          color="School", markers=True,
                          color_discrete_map={"LEHS": LEHS_NAVY, "LCHS": LEHS_GOLD},
                          title="Chronic absenteeism — LEHS vs LCHS")
            fig.update_layout(yaxis_tickformat=".0%")
            flow.extend(embed("chronic_abs", fig))
    flow.append(Paragraph(
        "Federal CRDC and DESE statereport disaggregated discipline data are "
        "wired into the live dashboard once the per-row parsers are tuned to "
        "current endpoint layouts. See scripts 03 + 04 in the data pipeline.",
        CAPTION,
    ))
    flow.append(PageBreak())
    return flow


def community_section() -> list:
    flow = [Paragraph("9. Community Context", H1)]
    flow.append(Paragraph(
        "Lynn's 22 census tracts span a wide range of household income, "
        "foreign-born share, and non-English-at-home prevalence. The live "
        "dashboard pairs Census ACS with EPA EJScreen + CDC PLACES tract-level "
        "indicators to ground the school data in community context.",
        BODY,
    ))
    flow.append(PageBreak())
    return flow


def methodology_section() -> list:
    flow = [Paragraph("Methodology & Sources", H1)]
    sources = [
        ("MA DESE Education-to-Career Hub (Socrata)", "educationtocareer.data.mass.gov"),
        ("MA DESE Profiles statereport", "profiles.doe.mass.edu/statereport"),
        ("Federal CRDC (Civil Rights Data Collection)", "civilrightsdata.ed.gov"),
        ("NCES IPEDS / College Scorecard", "collegescorecard.ed.gov"),
        ("US Census ACS 5-year tract-level", "data.census.gov"),
        ("EPA EJScreen", "epa.gov/ejscreen"),
        ("CDC PLACES", "chronicdata.cdc.gov"),
        ("MassGIS shapefiles", "mass.gov/orgs/massgis"),
    ]
    rows = [["Source", "URL"]] + [list(r) for r in sources]
    t = Table(rows, colWidths=[3.0 * inch, 3.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#CFD8DC")),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
    ]))
    flow.append(t)
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(
        "All charts and tables are reproducible via the open-source pipeline at "
        "github.com/mapzimus/lehs-data-dive. Run "
        "<font face='Courier'>python scripts/refresh_all.py</font> to rebuild "
        "every parquet file, then "
        "<font face='Courier'>python scripts/13_build_annual_report.py</font> "
        "to regenerate this PDF.",
        CAPTION,
    ))
    return flow


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Building {OUT_PDF.name}")
    doc = SimpleDocTemplate(
        str(OUT_PDF), pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title="State of LEHS 2026", author="Maxwell Howe",
    )
    flow = []
    flow.extend(cover_page())
    flow.extend(executive_summary())
    flow.extend(school_profile_section())
    flow.extend(academic_perf_section())
    flow.extend(ell_section())
    flow.extend(college_section())
    flow.extend(success_section())
    flow.extend(workforce_section())
    flow.extend(finance_section())
    flow.extend(discipline_section())
    flow.extend(community_section())
    flow.extend(methodology_section())
    doc.build(flow)
    print(f"  Wrote {OUT_PDF} ({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
