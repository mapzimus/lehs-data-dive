"""What We Still Don't Know — documented data gaps and limitations."""

import pandas as pd
import streamlit as st

from utils.branding import crosslink_callout, page_footer, sidebar_attribution
from utils.constants import LEHS_NAVY

st.set_page_config(page_title="Data Gaps | LEHS", page_icon="🔎", layout="wide")
sidebar_attribution()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("What We Still Don't Know")
st.markdown(
    "A dashboard is only as trustworthy as it is honest about its blind "
    "spots. This page is the catalog of things this site **cannot** show "
    "you — and *why*. Some gaps are about what public agencies publish; "
    "some are about geography; some are about how small numbers get "
    "suppressed to protect students' privacy. None of them are secrets."
)

st.info(
    "This page extends the **Important caveats** section already on the "
    "[Methodology](/Methodology) page. Where a limitation is fully "
    "documented there, we link rather than repeat it. The goal here is one "
    "honest, browsable list of every meaningful gap."
)

st.divider()

# ---------------------------------------------------------------------------
# 1. Student wellbeing / mental health
# ---------------------------------------------------------------------------

st.header("1. Student wellbeing & mental health")

with st.expander("What we'd like to show — and why we can't", expanded=True):
    st.markdown(
        """
**What we'd like to show.** Student-reported wellbeing: mental health,
vaping, sleep, food insecurity, and the kinds of questions a Youth Risk
Behavior Survey (MYRBS) asks — broken out at the school or district level.

**Why we can't.** DESE does not publish student-reported health and
mental-health data at the school/district level in the Education-to-Career
(E2C) pipeline this dashboard is built on. The youth survey results that do
exist are aggregated to a scale that doesn't isolate LEHS or even Lynn.

**The proxy we use instead.** The closest available signals are **adult,
census-tract-level CDC PLACES** health indicators (not student-specific),
plus **chronic-absenteeism** and **counselor-to-student ratios** as
indirect wellbeing measures. These gesture at the question; they don't
answer it.

*In progress:* a dedicated **Wellbeing** page may attempt a district-level
youth-survey ingest. Treat it as experimental — the underlying series may
turn out to be unavailable or too aggregated to publish responsibly.
        """
    )

# ---------------------------------------------------------------------------
# 2. Charter schools
# ---------------------------------------------------------------------------

st.header("2. Charter schools (e.g. KIPP Academy Lynn)")

with st.expander("Why KIPP isn't shown side-by-side", expanded=False):
    st.markdown(
        """
**What we'd like to show.** A Lynn family weighing **KIPP Academy Lynn**
against the district high schools should be able to compare them on the
same charts.

**Why we can't.** Commonwealth charter schools are their own districts;
they are **not part of the Lynn Public Schools datasets** that drive this
dashboard. Pulling KIPP in would mean a separate ingest with its own codes,
and the comparison would need careful caveats (charters enroll by lottery,
not by attendance area).

**The workaround.** Where charter options matter to a family's decision, we
point to them on the [Lynn HS Options](/Lynn_HS_Options) page rather than
folding charter numbers into LEHS's own trend charts.
        """
    )

# ---------------------------------------------------------------------------
# 3. Housing supply
# ---------------------------------------------------------------------------

st.header("3. Housing supply — permits & zoning")

with st.expander("Affordability yes, supply no", expanded=False):
    st.markdown(
        """
**What we'd like to show.** Whether Lynn is *building* housing — permit
counts, zoning capacity, the pipeline of new units.

**Why we can't.** We have housing **affordability** (Zillow home values plus
ACS rent, units, and year-built) but **not** building-permit counts or
zoning. Those live in municipal and regional-planning sources (the City of
Lynn and MAPC), not in the education/Census stack this dashboard draws from.

**The proxy we use instead.** ACS *year-built* distributions hint at how
much of the stock is recent, but they are a snapshot of what exists — not a
measure of what's being added.
        """
    )

# ---------------------------------------------------------------------------
# 4. Student-level cohort tracking
# ---------------------------------------------------------------------------

st.header("4. Following one cohort over time")

with st.expander("Why we can't follow a 9th-grade class to graduation", expanded=False):
    st.markdown(
        """
**What we'd like to show.** True longitudinal tracking — *follow this
specific 9th-grade cohort year by year to graduation and beyond.*

**Why we can't.** Real cohort tracking needs **Lynn SIS student-level
records**, which are confidential and not public. We never have a row per
student.

**The proxy we use instead.** **Aggregate grade-band counts** — how many
9th graders this year, how many 12th graders three years later. That
approximates a cohort but cannot account for students who transfer in or
out, so it is not a true longitudinal measure.
        """
    )

# ---------------------------------------------------------------------------
# 5. ACS geography vs. catchment
# ---------------------------------------------------------------------------

st.header("5. Census geography ≠ the LEHS attendance area")

with st.expander("Whole-city Lynn, not the precise catchment", expanded=False):
    st.markdown(
        """
**What we'd like to show.** Community context for the **LEHS attendance
area** specifically — the eastern half of the city the school actually
draws from.

**Why we can't.** Census **American Community Survey** data is published for
**whole-city Lynn**, not LEHS's catchment. The exact attendance-area
boundaries aren't published, so any "neighborhood" framing is approximate.
This is the same caveat noted on [Methodology](/Methodology); read every
ACS figure as *Lynn the city*, not *LEHS families*.
        """
    )

# ---------------------------------------------------------------------------
# 6. Suppression of small cells
# ---------------------------------------------------------------------------

st.header("6. Small-group suppression")

with st.expander("Why the smallest subgroups show gaps", expanded=False):
    st.markdown(
        """
**What we'd like to show.** Every student group, every year, at every
school — including the smallest ones.

**Why we can't.** DESE **suppresses any student-group cell with fewer than
10 students** before publishing, to protect individual privacy. So the
smallest subgroups, and small schools like **Frederick Douglass** and
**Harold Durgin**, show blanks or noticeably noisier rates.

**The honest read.** A missing cell is *usually* a suppressed small group,
not a true zero. Where a rate jumps around year to year for a tiny group,
that's sample noise, not necessarily a real change. This rule is documented
in full on [Methodology](/Methodology).
        """
    )

# ---------------------------------------------------------------------------
# 7. Lagging / paused series
# ---------------------------------------------------------------------------

st.header("7. Lagging & paused data series")

with st.expander("Numbers that are older than you'd expect", expanded=False):
    st.markdown(
        """
Not every series is current, and a few are frozen:

- **Earnings outcomes — paused.** DESE **paused updates to the
  Average Earnings of HS Graduates series in 2025** over a methodology issue
  affecting graduates who didn't attend Massachusetts public postsecondary
  institutions. The figures shown are the last published vintage.
- **CRDC — biennial, and pandemic-shaped.** The federal Civil Rights Data
  Collection is released **every two years**; the latest public-use file is
  the **2021–22** school year — a pandemic-recovery year. Its public-use
  release also applies **small random perturbations** to protect privacy, so
  counts are approximate.
- **General lag.** Several DESE indicators (graduation, dropout, extended
  engagement) lag a year behind the determination year. A "latest" chart may
  be reporting a school year that already closed.
        """
    )

# ---------------------------------------------------------------------------
# 8. EJScreen snapshot
# ---------------------------------------------------------------------------

st.header("8. Environmental-justice indicators (EJScreen)")

with st.expander("Currently an empty snapshot", expanded=False):
    st.markdown(
        """
**What we'd like to show.** EPA **EJScreen** environmental-justice
indicators around the school — pollution burden, proximity to hazards, and
the demographic indices that pair with them.

**Why we can't, right now.** The EJScreen dataset is currently an **empty
snapshot** in the pipeline. The source has been in flux, and until a stable
release lands we'd rather show nothing than show a half-loaded layer that
looks authoritative but isn't.
        """
    )

st.divider()

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

st.subheader("At a glance")

gaps = pd.DataFrame(
    [
        ("Student wellbeing / mental health",
         "Not published at school/district level in E2C",
         "Adult CDC PLACES + absenteeism & counselor ratios"),
        ("Charter schools (KIPP Academy Lynn)",
         "Charters are separate districts, not in LPS data",
         "Pointed to on Lynn HS Options, not merged in"),
        ("Housing supply (permits / zoning)",
         "Lives in municipal / MAPC sources, not our stack",
         "ACS affordability & year-built as context only"),
        ("Student-level cohort tracking",
         "Needs confidential Lynn SIS records",
         "Aggregate grade-band counts (approximate)"),
        ("ACS geography vs. catchment",
         "ACS is whole-city Lynn; catchment unpublished",
         "Read ACS as the city, not LEHS families"),
        ("Small-group suppression",
         "DESE blanks cells under 10 students",
         "Treat blanks as suppressed, not zero"),
        ("Lagging / paused series",
         "Earnings paused 2025; CRDC biennial (2021-22)",
         "Latest available vintage, flagged in context"),
        ("EJScreen indicators",
         "Currently an empty snapshot in the pipeline",
         "Omitted until a stable release lands"),
    ],
    columns=["Gap", "Why", "Workaround / proxy"],
)

st.dataframe(gaps, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Crosslink + corrections invite
# ---------------------------------------------------------------------------

crosslink_callout(
    "These limitations are part of the full methodology and source documentation.",
    "Methodology",
    "See Methodology & Sources →",
)

st.markdown(
    """
**Spotted something wrong, or a gap we missed?** This list is meant to be
corrected. If a number looks off, a caveat is out of date, or a dataset has
since been published, please flag it — every fix is recorded in the
[Corrections](/Corrections) log so you can see what changed and when.
    """
)

page_footer()
