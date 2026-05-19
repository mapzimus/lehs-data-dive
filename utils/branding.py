"""Shared branding/attribution helpers — call from every page."""

import streamlit as st


AUTHOR_NAME = "Maxwell Howe"
AUTHOR_SITE = "maxwellhowegis.com"


def sidebar_attribution() -> None:
    """Render the author attribution in the sidebar (appears on every page)."""
    st.sidebar.markdown(
        f"""
        ---
        **LEHS Data Dive**
        Built by **{AUTHOR_NAME}**
        [{AUTHOR_SITE}](https://{AUTHOR_SITE})
        """
    )


def page_footer() -> None:
    """Standard footer for every page."""
    st.divider()
    st.caption(
        f"Built by {AUTHOR_NAME} · "
        f"Data: MA DESE E2C Hub, profiles.doe.mass.edu, US Census, "
        f"US Dept of Education · See Methodology for full citations."
    )
