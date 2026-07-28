"""
LEHS Data Dive — entry point.

Builds the sidebar navigation and dispatches to the selected page.
The visible Home page content lives in `pages/home.py`; this file is
purely the dispatcher.

Run locally: `streamlit run Home.py`
"""

import streamlit as st

st.set_page_config(
    page_title="LEHS Data Dive",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar navigation tree. Dict keys render as section headers in the sidebar
# (Streamlit 1.36+ st.navigation). The empty-string key produces an
# ungrouped top-of-sidebar block — Home and Maps live there so they're
# always one click away regardless of which section a visitor is in.
#
# `url_path` is set explicitly on every page so the public URLs stay
# stable even if file-name prefixes change in later phases of the reorg.
# 2026-07 consolidation: closely-related pages were merged into tabbed pages
# to cut sidebar overwhelm (28 -> 21 entries). Each merged page keeps the
# url_path of its most-linked predecessor so the most-shared public links
# keep working:
#   Methodology + Data 101 + Data Gaps + Corrections -> About_the_Data.py (/Methodology)
#   College & Career + Success After HS              -> College_Career_Beyond.py (/College_and_Career)
#   Where Students Live + Feeder Schools             -> Where_Students_Come_From.py (/Where_Students_Live)
#   Lynn Schools + Lynn HS Options                   -> Lynn_Schools_Compared.py (/Lynn_Schools)
#   Discipline & Climate + Student Wellbeing         -> Discipline_Climate_Wellbeing.py (/Discipline_and_Climate)
nav = {
    "": [
        st.Page("pages/home.py", title="Home", default=True, url_path=""),
        st.Page("pages/Maps.py", title="Maps", url_path="Maps"),
        # Site-wide search across page titles + section headings — kept at the
        # top so it's always one click away regardless of section.
        st.Page("pages/Search.py", title="Search", url_path="Search"),
    ],
    "The School (LEHS)": [
        # "What changed this year" — the living-document overview for returning
        # visitors. Lives in the LEHS section (not About) per owner direction so
        # it sits with the school content, not buried with reference pages.
        st.Page("pages/What_Changed.py", title="What Changed This Year", url_path="What_Changed"),
        st.Page("pages/1_School_Profile.py", title="School Profile", url_path="School_Profile"),
        # url_path stays "Academic_Performance" so existing public links keep
        # working — only the display title changed when the page went MCAS-only.
        st.Page("pages/2_Academic_Performance.py", title="MCAS", url_path="Academic_Performance"),
        # Non-MCAS academics (G9 passing, course access, AP, SAT, retention)
        # split out of the old Academic Performance page.
        st.Page("pages/2b_Courses_and_Academics.py", title="Courses & Academics", url_path="Courses_and_Academics"),
        # DESE determination breakdown — the page admins check first, so it
        # sits directly under Academic Performance rather than at the end.
        st.Page("pages/3_Accountability.py", title="State Accountability", url_path="Accountability"),
        # Renamed for the public audience — "ELL Pipeline" is analyst-speak.
        st.Page("pages/4_ELL_Pipeline.py", title="English Learners", url_path="ELL_Pipeline"),
        # Tabs: "Preparing in HS" (pathways, early college, MassCore, plans)
        # + "After Graduation" (grad -> college -> persistence funnel).
        st.Page("pages/College_Career_Beyond.py", title="College, Career & Beyond", url_path="College_and_Career"),
        st.Page("pages/7_Teachers_and_Workforce.py", title="Teachers & Workforce", url_path="Teachers_and_Workforce"),
        st.Page("pages/8_Finance.py", title="Finance", url_path="Finance"),
        # Tabs: "Discipline & Climate" + "Student Wellbeing" (statewide YRBS
        # context plus honest proxy signals — no Lynn student survey exists).
        st.Page("pages/Discipline_Climate_Wellbeing.py", title="Discipline & Wellbeing", url_path="Discipline_and_Climate"),
    ],
    "Students & Community": [
        # Tabs: "Where Students Live" (residential geography) + "Feeder
        # Schools & Projection" (middle-school pipeline, enrollment cone).
        st.Page("pages/Where_Students_Come_From.py", title="Where Students Come From", url_path="Where_Students_Live"),
        st.Page("pages/10_Athletics.py", title="Athletics", url_path="Athletics"),
        # Narrative page — LEHS-specific but historical rather than analytical.
        st.Page("pages/12_LEHS_History.py", title="LEHS History", url_path="LEHS_History"),
        st.Page("pages/Lynn_District.py", title="Lynn District", url_path="Lynn_District"),
        st.Page("pages/Lynn_City.py", title="Lynn City", url_path="Lynn_City"),
    ],
    "Comparison": [
        # Tabs: analytical school-by-school comparison + the family-facing
        # side-by-side of the high schools a Lynn student chooses between.
        st.Page("pages/Lynn_Schools_Compared.py", title="Lynn Schools", url_path="Lynn_Schools"),
        st.Page("pages/Gateway_Peer_Comparison.py", title="Gateway Cities", url_path="Gateway_Peer_Comparison"),
        # Renamed for the public audience — "Correlation Lab" reads as jargon.
        st.Page("pages/Correlation_Lab.py", title="Cross-Topic Explorer", url_path="Correlation_Lab"),
    ],
    "About": [
        # Short, factual narrative reads grounded in the dashboard's data.
        st.Page("pages/Stories.py", title="Stories", url_path="Stories"),
        # Tabs: Methodology & Sources, Data 101, What We Don't Know,
        # Corrections — the whole reference family in one place.
        st.Page("pages/About_the_Data.py", title="About the Data", url_path="Methodology"),
    ],
}

pg = st.navigation(nav)
pg.run()
