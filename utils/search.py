"""Lightweight dashboard search — a curated topic index + a sidebar search box.

There's no full-text engine here; instead a hand-built index maps the terms a
visitor is likely to type (MCAS, suspensions, budget, bilingual…) to the page
that answers them. Rendered in every page's sidebar via
`branding.sidebar_attribution`.
"""

import streamlit as st

from utils.i18n import t

# Each entry: (label shown, page path, icon, [search keywords]).
_INDEX: list[tuple[str, str, str, list[str]]] = [
    ("School Profile — demographics & enrollment", "pages/1_School_Profile.py", "📊",
     ["demographics", "enrollment", "students", "race", "ethnicity", "hispanic", "black",
      "asian", "white", "low income", "poverty", "mobility", "attrition", "class size",
      "student teacher ratio", "accountability", "who attends", "grade level"]),
    ("Academic Performance — MCAS", "pages/2_Academic_Performance.py", "📈",
     ["mcas", "test scores", "scores", "ela", "english", "math", "science", "biology",
      "achievement", "growth", "sgp", "proficiency", "meeting exceeding", "scaled score",
      "subgroup gap", "percentile", "grade 10"]),
    ("English Learners", "pages/3_ELL_Pipeline.py", "🌐",
     ["english learner", "ell", "el", "bilingual", "esl", "wida", "access", "flne",
      "language", "spanish", "former el", "reclassification", "immigrant", "newcomer"]),
    ("College & Career", "pages/4_College_and_Career.py", "🎓",
     ["ap", "advanced placement", "ib", "sat", "masscore", "fafsa", "college", "career",
      "pathways", "early college", "dual enrollment", "where grads land", "ipeds",
      "advanced courses", "financial aid"]),
    ("Success After High School", "pages/5_Success_After_HS.py", "🏆",
     ["graduation", "grad rate", "dropout", "college enrollment", "persistence",
      "degree completion", "earnings", "wages", "cohort", "funnel", "postsecondary",
      "9th grade", "after high school", "outcomes", "plans of graduates"]),
    ("Teachers & Workforce", "pages/6_Teachers_and_Workforce.py", "👩‍🏫",
     ["teachers", "staff", "diversity", "teachers of color", "experienced", "in-field",
      "licensed", "retention", "fte", "counselor", "guidance", "social worker",
      "psychologist", "nurse", "support staff", "workforce"]),
    ("Finance — budget & spending", "pages/7_Finance.py", "💵",
     ["finance", "budget", "spending", "per pupil", "expenditures", "salary",
      "teacher salary", "chapter 70", "net school spending", "nss", "money", "cost",
      "dollars", "funding"]),
    ("Discipline & Climate", "pages/8_Discipline_and_Climate.py", "⚖️",
     ["discipline", "suspension", "oss", "out of school suspension", "expulsion",
      "chronic absence", "absenteeism", "attendance", "climate", "safety",
      "disproportionality", "risk ratio", "arrests"]),
    ("Athletics", "pages/9_Athletics.py", "🏟️",
     ["athletics", "sports", "teams", "win", "record", "rivalry", "hall of fame",
      "football", "basketball", "soccer", "championship", "bulldogs"]),
    ("Where Students Live", "pages/16_Where_Students_Live.py", "🏘️",
     ["where students live", "residence", "catchment", "neighborhood density", "kde",
      "address", "distance from school", "map of students"]),
    ("LEHS History", "pages/15_LEHS_History.py", "📜",
     ["history", "founded", "whelan", "alumni", "fire", "goodridge", "timeline",
      "origins", "past", "heritage"]),
    ("Maps", "pages/13_Maps.py", "🗺️",
     ["map", "maps", "census tract", "choropleth", "geography", "gis", "atlas",
      "school locations", "neighborhoods map"]),
    ("Lynn District (LPS)", "pages/Lynn_District.py", "🏛️",
     ["district", "lps", "lynn public schools", "all schools", "feeders",
      "middle schools", "district enrollment", "snapshot"]),
    ("Lynn — the City", "pages/Lynn_City.py", "🏙️",
     ["city", "community", "census", "income", "housing", "rent", "foreign born",
      "employers", "neighborhoods", "tracts", "acs", "population", "language at home"]),
    ("Lynn Schools — side by side", "pages/Lynn_Schools.py", "🆚",
     ["compare", "sibling schools", "classical", "tech", "frederick douglass",
      "harold durgin", "scorecard", "side by side", "peer"]),
    ("Gateway Cities", "pages/11_Gateway_Peer_Comparison.py", "🌆",
     ["gateway", "peer cities", "brockton", "lawrence", "chelsea", "lowell", "holyoke",
      "springfield", "comparison", "26 cities", "scorecard"]),
    ("Cross-Topic Explorer", "pages/12_Correlation_Lab.py", "🔬",
     ["correlation", "cross topic", "explore", "relationship", "regression", "scatter",
      "what moves with what", "composite", "index", "predictor"]),
    ("Data 101 — how to read the charts", "pages/14_Data_Literacy.py", "📚",
     ["data 101", "how to read", "beginner", "chart types", "literacy", "explain",
      "percentages", "what is a dataset", "help"]),
    ("Methodology & Sources", "pages/99_Methodology.py", "📖",
     ["methodology", "sources", "caveats", "data sources", "reproduce", "definitions",
      "suppression", "what we don't know", "limitations"]),
]


def render_sidebar_search() -> None:
    """A compact search box in the sidebar that maps a typed topic to the page
    answering it. Called from sidebar_attribution() so it appears everywhere."""
    with st.sidebar:
        with st.expander(t("🔍 Search"), expanded=False):
            q = st.text_input(
                t("Search the dashboard"),
                placeholder=t("MCAS, suspensions, budget…"),
                label_visibility="collapsed",
                key="_dash_search",
            )
            ql = q.strip().lower()
            if len(ql) < 2:
                st.caption(t("Type a topic — e.g. *graduation*, *AP*, *budget*, *bilingual*."))
                return
            hits: list[tuple[int, str, str, str]] = []
            for label, page, icon, keywords in _INDEX:
                haystack = label.lower() + " " + " ".join(keywords)
                if ql in haystack:
                    # Label matches rank above keyword-only matches.
                    score = 0 if ql in label.lower() else 1
                    hits.append((score, label, page, icon))
            hits.sort(key=lambda h: h[0])
            if not hits:
                st.caption(t("No matches for “{q}”. Try a broader topic.", q=q))
                return
            for _, label, page, icon in hits[:10]:
                st.page_link(page, label=f"{icon} {label}")
