"""
Data 101 — Reading the Charts.

A beginner-friendly guide to the kinds of charts, percentages, and
statistical caveats this dashboard uses. Targeted at students who've
never seen a dashboard before — assumes zero stats background.

Lives at the top of the sidebar alongside Maps so first-time visitors
(especially LEHS students poking around the data about their own
school) can find it without hunting through analyst-jargon section
names.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.branding import page_footer, sidebar_attribution
from utils.charts import DEFAULT_LAYOUT, LEHS_GOLD, LEHS_NAVY

st.set_page_config(
    page_title="Data 101 | LEHS", page_icon="📊", layout="wide",
)
sidebar_attribution()

# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------

st.title("Data 101 — Reading the Charts")
st.markdown(
    "This dashboard is full of numbers, percentages, and graphs. If you've "
    "never opened a dashboard before, **this is the page to start on**. "
    "No background required — by the end you'll know what every chart on "
    "the site is trying to tell you."
)

st.info(
    "📚 **Who this is for:** Anyone new to data — especially LEHS and "
    "Lynn Public Schools students who want to understand the numbers "
    "about their own school. Teachers and curious community members "
    "welcome too. You can skip around using the sections below."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 1 — What's a dataset?
# ---------------------------------------------------------------------------

st.header("1. What is a dataset?")

st.markdown(
    """
A **dataset** is just a table — like a really big spreadsheet. Each
**row** is a *thing* you're tracking. Each **column** is a *fact* about
that thing. Here's a tiny example, the kind of row you'd see in the
real enrollment dataset behind this dashboard:
"""
)

demo_dataset = pd.DataFrame(
    {
        "School Year": ["2023–24", "2024–25", "2025–26"],
        "School": ["Lynn English High"] * 3,
        "Total Students": [1_690, 1_705, 1_727],
        "% English Learners": ["38%", "40%", "42%"],
        "% Low Income": ["72%", "74%", "75%"],
    }
)
st.dataframe(demo_dataset, hide_index=True, width="stretch")

st.markdown(
    """
- Three **rows**, one per school year.
- Five **columns**, each measuring something different.
- The actual dataset behind the [School Profile](/School_Profile?embed=true) page
  has thousands of rows like these going back to 1992 — but the
  shape is the same.

**A database** is the bigger thing: a *collection of related datasets*
all kept together. This dashboard sits on top of **50+ datasets across
~10 public sources** — MA DESE, the US Census, federal civil-rights
data, athletics records, and original LPS research. Each chart you'll
see is a way of *looking at* one or more of those tables.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Section 2 — Chart types (the main event)
# ---------------------------------------------------------------------------

st.header("2. Chart types and what each one is for")

st.markdown(
    "Different chart types answer different questions. Pick the wrong "
    "chart and the story gets lost. Here are the ones this dashboard "
    "uses most — with a tiny example of each."
)

# --- Bar chart ---
st.subheader("📊 Bar chart — *comparing categories*")

bc_df = pd.DataFrame(
    {
        "School": ["LEHS", "Classical", "Tech", "Frederick Douglass", "Harold Durgin"],
        "Enrollment": [1_727, 1_513, 1_566, 364, 98],
    }
)
fig = px.bar(
    bc_df, x="School", y="Enrollment", text="Enrollment",
    color_discrete_sequence=[LEHS_NAVY],
)
fig.update_traces(textposition="outside")
fig.update_layout(**DEFAULT_LAYOUT, height=320, showlegend=False)
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
- **Use when:** comparing a value across discrete categories (here:
  schools).
- **What to look for:** which bar is tallest, how the bars rank, how
  big the gaps are between bars.
- **In this dashboard:** every page that ranks schools, subjects, or
  subgroups uses a bar chart.

👀 **See it in action:** the [Lynn Schools](/Lynn_Schools?embed=true) page is
wall-to-wall bar charts comparing LEHS to its four sibling high schools.
"""
)

# --- Line chart ---
st.subheader("📈 Line chart — *change over time*")

yrs = list(range(2017, 2026))
line_df = pd.DataFrame(
    {
        "Year": yrs * 2,
        "Subject": ["ELA"] * len(yrs) + ["Math"] * len(yrs),
        "% Meeting + Exceeding": [
            0.44, 0.45, 0.47, None, 0.42, 0.46, 0.48, 0.50, 0.51,
            0.32, 0.33, 0.35, None, 0.28, 0.31, 0.34, 0.36, 0.38,
        ],
    }
).dropna()
fig = px.line(
    line_df, x="Year", y="% Meeting + Exceeding",
    color="Subject", markers=True,
    color_discrete_map={"ELA": LEHS_NAVY, "Math": LEHS_GOLD},
)
fig.update_layout(**DEFAULT_LAYOUT, height=320, yaxis_tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
- **Use when:** showing how a value *changes* across time.
- **What to look for:** the slope (going up or down?), sharp jumps
  (something happened that year), gaps (data wasn't collected — note
  the missing 2020 point above, when COVID cancelled MCAS).
- **In this dashboard:** MCAS trends, enrollment over decades,
  graduation rates by cohort year.

👀 **See it in action:** [MCAS](/Academic_Performance?embed=true)
opens with multi-year MCAS line charts — including that real 2020 gap.
"""
)

# --- Histogram ---
st.subheader("📉 Histogram — *how things are distributed*")

rng = np.random.default_rng(seed=42)
hist_data = rng.normal(loc=70, scale=12, size=400)
hist_data = np.clip(hist_data, 30, 100)
fig = px.histogram(
    pd.DataFrame({"Test Score": hist_data}),
    x="Test Score", nbins=20, color_discrete_sequence=[LEHS_NAVY],
)
fig.update_layout(**DEFAULT_LAYOUT, height=320, yaxis_title="# of students")
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
- **Use when:** you want to see the *shape* of a single column of
  numbers — where most values cluster, how spread out they are, where
  the outliers sit.
- **What to look for:** the peak (the **mode**, most common value),
  the spread (narrow = consistent, wide = lots of variation), the
  tails (a few students way below or way above the rest).
- **Histogram ≠ bar chart**: a bar chart compares categories (apples
  vs. oranges). A histogram chops a *single number* into ranges and
  shows how many values fall in each range.
- **In this dashboard:** MCAS achievement-level distributions, school
  enrollment-size distributions across all MA gateway cities.
"""
)

# --- Scatter plot ---
st.subheader("🔵 Scatter plot — *relationship between two things*")

scatter_df = pd.DataFrame(
    {
        "% Low Income": np.linspace(0.20, 0.90, 26)
        + rng.normal(0, 0.04, 26),
        "% Meeting + Exceeding (ELA)": np.linspace(0.65, 0.30, 26)
        + rng.normal(0, 0.06, 26),
        "City": [
            "Brockton", "Chelsea", "Chicopee", "Everett", "Fall River",
            "Fitchburg", "Haverhill", "Holyoke", "Lawrence", "Leominster",
            "Lowell", "Lynn", "Malden", "Methuen", "New Bedford",
            "Peabody", "Pittsfield", "Quincy", "Revere", "Salem",
            "Springfield", "Taunton", "Westfield", "Worcester",
            "Attleboro", "Barnstable",
        ],
    }
)
fig = px.scatter(
    scatter_df, x="% Low Income", y="% Meeting + Exceeding (ELA)",
    hover_name="City", color_discrete_sequence=[LEHS_NAVY],
    trendline="ols",
)
fig.update_layout(**DEFAULT_LAYOUT, height=350,
                   xaxis_tickformat=".0%", yaxis_tickformat=".0%")
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
- **Use when:** asking *"do these two things move together?"*. One
  variable on the X axis, another on Y, every dot is one observation.
- **What to look for:** if dots form a sloping pattern, the two things
  are *correlated* (move together). The line through the cloud is a
  **trend line** — it summarizes the average pattern.
- **Warning:** correlation is not causation (Section 4). Two things
  can move together without one *causing* the other.
- **In this dashboard:** the [Cross-Topic Explorer](/Correlation_Lab?embed=true)
  is built entirely around scatter plots — pick any two metrics across
  MA's 26 Gateway cities and see if they move together.

👀 **See it in action:** head to the
[Cross-Topic Explorer](/Correlation_Lab?embed=true) and build your own
scatter plot with two metrics you're curious about.
"""
)

# --- Choropleth-style explanation ---
st.subheader("🗺️ Choropleth map — *geography*")

st.markdown(
    """
A **choropleth** is a map where each shape (state, town, neighborhood,
census tract) is *colored* by a value — darker means more, lighter
means less. It answers *"where is this happening?"* questions.

You'll see two flavors on this dashboard:
- **City-scale:** Lynn's 22 census tracts shaded by % Low Income,
  language at home, or chronic absence — on the
  [City → Neighborhoods tab](/Lynn_City?embed=true) and on the
  [Maps page](/Maps?embed=true).
- **State-scale:** all 351 MA municipalities shaded by school
  performance, demographics, or finance — on the standalone
  [MA Education Atlas](https://maxwellhowegis.com/ma-atlas/).

👀 **See it in action:** the [Maps](/Maps?embed=true) page is the launch pad
for both interactive maps — try shading Lynn's tracts by a metric you care about.
"""
)

# --- Heatmap ---
st.subheader("🔥 Heatmap — *patterns across two dimensions*")

heat_df = pd.DataFrame(
    {
        "Grade": list("3 4 5 6 7 8 10".split()) * 3,
        "Subject": (["ELA"] * 7) + (["Math"] * 7) + (["Science"] * 7),
        "% M+E": [
            0.39, 0.41, 0.42, 0.40, 0.43, 0.45, 0.49,
            0.32, 0.30, 0.28, 0.27, 0.29, 0.31, 0.34,
            None, None, 0.30, None, None, 0.36, 0.41,
        ],
    }
)
heat_pivot = heat_df.pivot(index="Subject", columns="Grade", values="% M+E")
fig = go.Figure(
    data=go.Heatmap(
        z=heat_pivot.values, x=heat_pivot.columns, y=heat_pivot.index,
        colorscale="Blues", text=heat_pivot.values,
        texttemplate="%{text:.0%}", textfont={"size": 12},
        zmin=0, zmax=0.6,
    )
)
fig.update_layout(**DEFAULT_LAYOUT, height=280, xaxis_title="Grade",
                   yaxis_title="Subject")
st.plotly_chart(fig, width="stretch")

st.markdown(
    """
- **Use when:** you want to see patterns across *two* category
  dimensions at once (here: subject × grade).
- **What to look for:** which cells are darkest (highest values),
  whether one row or column stands out from the others.
- **In this dashboard:** subject-by-grade MCAS performance grids,
  attendance × subgroup tables.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3 — How to read a percentage
# ---------------------------------------------------------------------------

st.header("3. How to read a percentage")

st.markdown(
    """
Percentages are everywhere on this dashboard. They look simple, but
they hide a few traps.

**A percentage is always "out of what?"**
When you see *"42% of LEHS students are English Learners"*, the
**"out of"** is the school's total enrollment — about 1,727 students.
So that's roughly 725 EL students. The percentage *normalizes* the
count so you can compare schools of different sizes.

**Percentage vs. percentage points**
If LEHS's graduation rate goes from 80% to 85%, that's a **5
percentage-point** increase. It is **not** a 5% increase — a 5%
increase from 80% would only get you to 84%. The two phrases mean
different things and journalists mix them up constantly. On this
dashboard, when we say "+5 pts" we mean percentage points.

**Compared to what?**
A single percentage isn't useful by itself. *75% Low Income* sounds
high — but compared to what? On the dashboard you'll always see
percentages next to peer comparisons:
- LEHS's same-district sibling schools
- LPS as a whole
- Other MA Gateway cities (Lawrence, Holyoke, Springfield, …)
- The state average

That's why almost every chart has multiple colored lines or bars
side-by-side — single numbers without context can mislead.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Section 4 — Common pitfalls
# ---------------------------------------------------------------------------

st.header("4. Common pitfalls — what to watch for")

with st.expander("**Mean vs. median** — averages can lie", expanded=False):
    st.markdown(
        """
The **mean** is what most people call "the average" — add up all the
values and divide by how many. The **median** is the middle value when
you sort everything from low to high.

When a few extreme values are pulling the mean around, the median
gives you a fairer picture. Classic example: median household income
in Lynn is **\\$74,715**. The *mean* would be higher, because a small
number of very-wealthy households pull the average up while the typical
Lynn household sits at the median.

This dashboard reports **median** household income, and uses median
home values, median rent, etc. — to keep outliers from skewing the
story.
"""
    )

with st.expander("**Sample size** — 100% of 4 students vs. 100% of 1,000", expanded=False):
    st.markdown(
        """
If a school reports "100% of seniors took the SAT", that means very
different things at LEHS (~400 seniors) than at a tiny program (~10
seniors). Small sample sizes are noisy — one or two unusual students
can swing the percentage wildly.

This is why DESE **suppresses** subgroup numbers below n=10 — the
percentage would be too unstable to publish, and it would also risk
identifying individual students. When you see "—" or "DS" (Data
Suppressed) in a chart, that's why.
"""
    )

with st.expander("**Correlation ≠ causation** — moving together isn't the same as causing", expanded=False):
    st.markdown(
        """
On a scatter plot, if % Low Income and % Meeting MCAS slope downward
together, it's tempting to say "low income causes lower scores". But
correlation just means two things move together — it doesn't say
which causes which, or whether something *else* (housing, healthcare,
family time, instructional minutes) is causing both.

The [Cross-Topic Explorer](/Correlation_Lab?embed=true) is for *spotting*
correlations across MA's 26 gateway cities. Use it to ask questions,
not to declare causes.
"""
    )

with st.expander("**Year-over-year noise vs. real trends**", expanded=False):
    st.markdown(
        """
Any single year's data can wobble for reasons that have nothing to do
with the school: a tough testing day, a cohort that happened to have
more EL students, COVID cancellations (2020).

A real trend shows up across multiple years — three points in a row
going the same direction is much more convincing than one big jump.
That's why most trend charts on this dashboard go back 5+ years.
"""
    )

with st.expander("**Confidence intervals** — the fuzzy bars on some charts", expanded=False):
    st.markdown(
        """
When a chart shows a number with little error bars above and below
(or a shaded band around a line), those are **confidence intervals**.
They tell you how *certain* the measurement is.

A short bar = we're confident in the number. A long bar = the
underlying sample is small or noisy, so the "real" value could be
anywhere in that range. **If two confidence intervals overlap, the
two numbers might actually be the same** — don't read too much into
the difference between them.

👀 **See it in action:** the MCAS trend charts on
[MCAS](/Academic_Performance?embed=true) are where to
practice telling a real trend from year-to-year noise.
"""
    )

st.divider()

# ---------------------------------------------------------------------------
# Section 5 — Try it
# ---------------------------------------------------------------------------

st.header("5. Try it yourself")

st.markdown(
    """
Now you know how to read everything on this site. A few suggested
places to practice:

- **[School Profile](/School_Profile?embed=true)** — bar charts and trend lines
  showing who attends LEHS. Compare year-over-year.
- **[MCAS](/Academic_Performance?embed=true)** — MCAS line
  charts with confidence intervals. Look for trend vs. noise.
- **[Cross-Topic Explorer](/Correlation_Lab?embed=true)** — scatter plots across
  26 MA gateway cities. Pick any two metrics and look for
  correlation. Remember: correlation ≠ causation.
- **[Maps](/Maps?embed=true)** — choropleths at the city and statewide scale.

If anything on the dashboard is confusing, the explanation is
probably back on this page. Bookmark it and come back."""
)

st.divider()
st.caption(
    "Built for students, by a teacher. If you spot something that's "
    "still confusing or want a chart type covered that isn't here, let "
    "Maxwell know via the GitHub link in the footer."
)

page_footer()
