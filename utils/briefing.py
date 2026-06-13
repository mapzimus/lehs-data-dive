"""
School Committee briefing PDF for Lynn English High (LEHS).

Builds a concise 1-2 page PDF of LEHS's headline numbers from the processed
DESE parquets, using **text + reportlab tables only** — no chart images. This
keeps generation fast and reliable on Streamlit Cloud (kaleido / headless
chromium is deliberately avoided).

Public entry point:
    build_briefing_pdf() -> bytes

Every percent column in these datasets is stored as a 0-1 FRACTION, so any
value pulled from a *_PCT column is multiplied by 100 before display.
"""

from __future__ import annotations

import datetime
from io import BytesIO

import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.constants import LEHS_SCHOOL_CODE
from utils.data_loader import load_dataset

# Brand navy used for table header rows (the original, non-pastel brand navy —
# pastels are for on-screen charts; a print header wants real contrast).
_NAVY = colors.HexColor("#0A1F44")
_DASH = "—"  # em-dash placeholder for missing values


# ---------------------------------------------------------------------------
# Small data helpers
# ---------------------------------------------------------------------------

def _norm(series: pd.Series) -> pd.Series:
    """Strip the NBSP variants DESE ships in some STU_GRP labels."""
    return series.astype(str).str.replace("\xa0", " ", regex=False).str.strip()


def _yearly(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    """Reduce a pre-filtered frame to one clean (SY, value) row per year."""
    if df.empty or value_col not in df.columns or "SY" not in df.columns:
        return pd.DataFrame(columns=["SY", "value"])
    out = pd.DataFrame(
        {
            "SY": pd.to_numeric(df["SY"], errors="coerce"),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
        }
    ).dropna(subset=["SY", "value"])
    if out.empty:
        return pd.DataFrame(columns=["SY", "value"])
    out["SY"] = out["SY"].astype(int)
    return out.drop_duplicates(subset=["SY"], keep="last").sort_values("SY")


def _fmt(value, is_pct: bool) -> str:
    """Format a single value; fractions (is_pct) are scaled to 0-100."""
    if value is None or pd.isna(value):
        return _DASH
    if is_pct:
        return f"{value * 100:.1f}%"
    return f"{value:,.0f}"


def _fmt_change(latest, prior, is_pct: bool) -> str:
    """Signed latest-minus-prior change; '—' if either year is missing."""
    if latest is None or prior is None or pd.isna(latest) or pd.isna(prior):
        return _DASH
    if is_pct:
        return f"{(latest - prior) * 100:+.1f} pts"
    return f"{latest - prior:+,.0f}"


def _two_years(series: pd.DataFrame):
    """Return (latest_value, prior_value, latest_year) from a (SY, value) frame.

    Defensive: if only one year exists, prior is None; if empty, all None.
    """
    if series.empty:
        return None, None, None
    latest = series.iloc[-1]
    prior = series.iloc[-2] if len(series) >= 2 else None
    return (
        float(latest["value"]),
        (float(prior["value"]) if prior is not None else None),
        int(latest["SY"]),
    )


# ---------------------------------------------------------------------------
# Metric resolvers — each returns a clean (SY, value) frame for LEHS
# ---------------------------------------------------------------------------

def _enroll_series(value_col: str) -> pd.DataFrame:
    df = load_dataset("enrollment_demographics")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    return _yearly(df[df["ORG_CODE"] == LEHS_SCHOOL_CODE], value_col)


def _grad_series() -> pd.DataFrame:
    df = load_dataset("graduation_rates")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["GRAD_RATE_TYPE"] == "4-Year Graduation Rate")
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _yearly(sub, "GRAD_PCT")


def _mcas_series(subject: str) -> pd.DataFrame:
    df = load_dataset("mcas_achievement")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["TEST_GRADE"] == "10")
        & (df["SUBJECT_CODE"] == subject)
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _yearly(sub, "M_PLUS_E_PCT")


def _chronic_abs_series() -> pd.DataFrame:
    df = load_dataset("student_attendance")
    if df.empty:
        return pd.DataFrame(columns=["SY", "value"])
    sub = df[
        (df["ORG_CODE"] == LEHS_SCHOOL_CODE)
        & (df["ATTEND_PERIOD"] == "End of Year")
        & (_norm(df["STU_GRP"]) == "All Students")
    ]
    return _yearly(sub, "PCT_CHRON_ABS_10")


def _sy_label(year) -> str:
    """'2024-25' style school-year label from the spring-end SY integer."""
    if year is None:
        return _DASH
    return f"{year - 1}-{str(year)[-2:]}"


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------

def _determination_table(styles):
    """Latest accountability determination box (classification/percentile/enrollment)."""
    df = load_dataset("accountability_summary")
    classification, percentile, enrollment, year = _DASH, _DASH, _DASH, None
    if not df.empty:
        sub = df[df["ORG_CODE"] == LEHS_SCHOOL_CODE]
        if not sub.empty:
            row = sub.sort_values("SY").iloc[-1]
            year = int(row["SY"]) if pd.notna(row.get("SY")) else None
            if pd.notna(row.get("CLASSIFICATION")):
                classification = str(row["CLASSIFICATION"])
            pct = pd.to_numeric(pd.Series([row.get("PERCENTILE")]), errors="coerce").iloc[0]
            if pd.notna(pct):
                percentile = f"{pct:.0f} (of 99)"
            enr = pd.to_numeric(pd.Series([row.get("ENROLLMENT")]), errors="coerce").iloc[0]
            if pd.notna(enr):
                enrollment = f"{enr:,.0f}"

    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontSize=9, leading=12)
    label = ParagraphStyle(
        "lab", parent=cell, textColor=colors.whitesmoke, fontName="Helvetica-Bold"
    )
    data = [
        [
            Paragraph("State Classification", label),
            Paragraph("Accountability Percentile", label),
            Paragraph("Reported Enrollment", label),
        ],
        [
            Paragraph(classification, cell),
            Paragraph(percentile, cell),
            Paragraph(enrollment, cell),
        ],
    ]
    table = Table(data, colWidths=[2.8 * inch, 2.0 * inch, 1.9 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("BOX", (0, 0), (-1, -1), 0.75, _NAVY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B7C0CC")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table, year


def _headline_table():
    """Latest / prior / change table for the core headline metrics."""
    # (label, series, is_pct)
    specs = [
        ("Total enrollment", _enroll_series("TOTAL_CNT"), False),
        ("4-year graduation rate", _grad_series(), True),
        ("MCAS Gr.10 ELA — % meeting/exceeding", _mcas_series("ELA"), True),
        ("MCAS Gr.10 Math — % meeting/exceeding", _mcas_series("MATH"), True),
        ("Chronic absenteeism (>=10% of days)", _chronic_abs_series(), True),
    ]

    rows = [["Metric", "School year", "Latest", "Prior year", "Change"]]
    for label, series, is_pct in specs:
        latest, prior, year = _two_years(series)
        rows.append(
            [
                label,
                _sy_label(year),
                _fmt(latest, is_pct),
                _fmt(prior, is_pct),
                _fmt_change(latest, prior, is_pct),
            ]
        )

    table = Table(
        rows,
        colWidths=[2.9 * inch, 0.95 * inch, 0.95 * inch, 1.0 * inch, 0.9 * inch],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 1), (0, -1), "Helvetica"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#B7C0CC")),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F4F8")]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _demographics_line() -> str:
    """One-line demographics summary: % EL, % Low Income, % SWD (latest year)."""
    el, _, year = _two_years(_enroll_series("EL_PCT"))
    li, _, _ = _two_years(_enroll_series("LI_PCT"))
    swd, _, _ = _two_years(_enroll_series("SWD_PCT"))
    yr = f" ({_sy_label(year)})" if year else ""
    return (
        f"<b>Student population{yr}:</b> "
        f"English learners {_fmt(el, True)} &nbsp;&bull;&nbsp; "
        f"Low income {_fmt(li, True)} &nbsp;&bull;&nbsp; "
        f"Students with disabilities {_fmt(swd, True)}."
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def build_briefing_pdf() -> bytes:
    """Assemble a 1-2 page LEHS briefing PDF (text + tables only) and return bytes."""
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "BriefTitle",
        parent=styles["Title"],
        fontSize=18,
        leading=22,
        textColor=_NAVY,
        spaceAfter=2,
        alignment=TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "BriefSub", parent=styles["BodyText"], fontSize=9, leading=12,
        textColor=colors.HexColor("#444444"),
    )
    section_style = ParagraphStyle(
        "BriefSection", parent=styles["Heading2"], fontSize=12, leading=15,
        textColor=_NAVY, spaceBefore=10, spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "BriefBody", parent=styles["BodyText"], fontSize=9.5, leading=13,
    )
    footer_style = ParagraphStyle(
        "BriefFooter", parent=styles["BodyText"], fontSize=8, leading=10,
        textColor=colors.HexColor("#666666"),
    )

    determ_table, acct_year = _determination_table(styles)
    today = datetime.date.today()
    acct_lbl = f" (accountability year {_sy_label(acct_year)})" if acct_year else ""

    story = [
        Paragraph("Lynn English High School &mdash; Data Briefing", title_style),
        Paragraph(
            f"Generated {today:%B %-d, %Y}. Figures are the latest published "
            "Massachusetts DESE data; data years vary by metric and each "
            "table notes its own year.",
            sub_style,
        ),
        Spacer(1, 10),
        Paragraph(f"State Accountability Determination{acct_lbl}", section_style),
        determ_table,
        Paragraph("Headline Metrics", section_style),
        Paragraph(
            "Latest available year versus the prior year for All Students. "
            "Percentages are percentage points; counts are raw numbers.",
            sub_style,
        ),
        Spacer(1, 4),
        _headline_table(),
        Spacer(1, 8),
        Paragraph(_demographics_line(), body_style),
        Spacer(1, 16),
        Paragraph(
            "Source: MA DESE. Generated by the LEHS Data Dive "
            "(maxwellhowegis.com). Figures are school-level aggregates; "
            "no student records.",
            footer_style,
        ),
    ]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
        title="Lynn English High School — Data Briefing",
        author="LEHS Data Dive",
    )
    doc.build(story)
    return buffer.getvalue()
