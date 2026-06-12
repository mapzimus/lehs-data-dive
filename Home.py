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
nav = {
    "": [
        st.Page("pages/home.py", title="Home", default=True, url_path=""),
        st.Page("pages/Maps.py", title="Maps", url_path="Maps"),
    ],
    "The School (LEHS)": [
        st.Page("pages/1_School_Profile.py", title="School Profile", url_path="School_Profile"),
        st.Page("pages/2_Academic_Performance.py", title="Academic Performance", url_path="Academic_Performance"),
        # DESE determination breakdown — the page admins check first, so it
        # sits directly under Academic Performance rather than at the end.
        st.Page("pages/3_Accountability.py", title="State Accountability", url_path="Accountability"),
        # Renamed for the public audience — "ELL Pipeline" is analyst-speak.
        st.Page("pages/4_ELL_Pipeline.py", title="English Learners", url_path="ELL_Pipeline"),
        st.Page("pages/5_College_and_Career.py", title="College & Career", url_path="College_and_Career"),
        # Success After HS now includes the former "After Graduation" cohort
        # tracking content as its hero funnel — one connected story instead of
        # two near-duplicate pages.
        st.Page("pages/6_Success_After_HS.py", title="Success After HS", url_path="Success_After_HS"),
        st.Page("pages/7_Teachers_and_Workforce.py", title="Teachers & Workforce", url_path="Teachers_and_Workforce"),
        st.Page("pages/8_Finance.py", title="Finance", url_path="Finance"),
        st.Page("pages/9_Discipline_and_Climate.py", title="Discipline & Climate", url_path="Discipline_and_Climate"),
        st.Page("pages/10_Athletics.py", title="Athletics", url_path="Athletics"),
        st.Page("pages/11_Where_Students_Live.py", title="Where Students Live", url_path="Where_Students_Live"),
        # Narrative page — sits at the end of "The School (LEHS)" group
        # since it's still LEHS-specific, just historical rather than
        # analytical. Moved out of School Profile so the Profile can be
        # data-only.
        st.Page("pages/12_LEHS_History.py", title="LEHS History", url_path="LEHS_History"),
        # Federal CRDC (civil rights data) — ingest shipped (2021-22), page live.
        st.Page("pages/13_Federal_CRDC.py", title="Civil Rights Data", url_path="Federal_CRDC"),
    ],
    "Lynn": [
        st.Page("pages/Lynn_District.py", title="District", url_path="Lynn_District"),
        st.Page("pages/Lynn_City.py", title="City", url_path="Lynn_City"),
    ],
    "Comparison": [
        # Lifted out of the Lynn District page (formerly its "LEHS vs Siblings"
        # tab) so all peer-comparison views — same-district siblings, gateway
        # cities, cross-topic correlations — share one section of the sidebar.
        st.Page("pages/Lynn_Schools.py", title="Lynn Schools", url_path="Lynn_Schools"),
        st.Page("pages/Gateway_Peer_Comparison.py", title="Gateway Cities", url_path="Gateway_Peer_Comparison"),
        # Renamed for the public audience — "Correlation Lab" reads as jargon.
        st.Page("pages/Correlation_Lab.py", title="Cross-Topic Explorer", url_path="Correlation_Lab"),
    ],
    "About": [
        # Data 101 sits in About because it's an explainer/reference,
        # not analytical content — same family as Methodology.
        st.Page("pages/Data_Literacy.py", title="Data 101", url_path="Data_101"),
        st.Page("pages/99_Methodology.py", title="Methodology", url_path="Methodology"),
    ],
}

pg = st.navigation(nav)
pg.run()
