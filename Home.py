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
        st.Page("pages/13_Maps.py", title="Maps", url_path="Maps"),
    ],
    "The School (LEHS)": [
        st.Page("pages/1_School_Profile.py", title="School Profile", url_path="School_Profile"),
        st.Page("pages/2_Academic_Performance.py", title="Academic Performance", url_path="Academic_Performance"),
        st.Page("pages/3_ELL_Pipeline.py", title="ELL Pipeline", url_path="ELL_Pipeline"),
        st.Page("pages/4_College_and_Career.py", title="College & Career", url_path="College_and_Career"),
        st.Page("pages/5_Success_After_HS.py", title="Success After HS", url_path="Success_After_HS"),
        st.Page("pages/6_Teachers_and_Workforce.py", title="Teachers & Workforce", url_path="Teachers_and_Workforce"),
        st.Page("pages/7_Finance.py", title="Finance", url_path="Finance"),
        st.Page("pages/8_Discipline_and_Climate.py", title="Discipline & Climate", url_path="Discipline_and_Climate"),
        st.Page("pages/16_Where_Students_Live.py", title="Where Students Live", url_path="Where_Students_Live"),
        st.Page("pages/18_Cohort_Tracking.py", title="Cohort Tracking", url_path="Cohort_Tracking"),
        st.Page("pages/17_Federal_CRDC.py", title="Federal CRDC", url_path="Federal_CRDC"),
    ],
    "Lynn": [
        st.Page("pages/15_Lynn_District_Dashboard.py", title="District Dashboard", url_path="Lynn_District_Dashboard"),
        st.Page("pages/14_All_Lynn_Schools.py", title="All Lynn Schools", url_path="All_Lynn_Schools"),
        st.Page("pages/10_Lynn_District_and_Siblings.py", title="District & Siblings", url_path="Lynn_District_and_Siblings"),
        st.Page("pages/19_Lynn_Overview.py", title="City Overview", url_path="Lynn_Overview"),
        st.Page("pages/9_Community_Context.py", title="Community Context", url_path="Community_Context"),
    ],
    "Comparison": [
        st.Page("pages/11_Gateway_Peer_Comparison.py", title="Gateway Cities", url_path="Gateway_Peer_Comparison"),
        st.Page("pages/12_Correlation_Lab.py", title="Correlation Lab", url_path="Correlation_Lab"),
    ],
    "About": [
        st.Page("pages/99_Methodology.py", title="Methodology", url_path="Methodology"),
    ],
}

pg = st.navigation(nav)
pg.run()
