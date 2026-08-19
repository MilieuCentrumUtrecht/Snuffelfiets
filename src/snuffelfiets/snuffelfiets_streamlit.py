from pathlib import Path

import streamlit as st


def page_navigation():
    """Create navigation panel for pages of Snuffelfiets app."""

    package_root = st.session_state.package_root

    filepath = package_root / "static" / "images" / "cropped-logo-mcu-1-1.png"
    st.logo(
        filepath,
        size="medium",
        link="https://mcu.nl/",
        icon_image=None,
        )

    with st.expander("Info", expanded=False):
        st.caption(
            """
            Appje gemaakt door de dataclub van 
            [Milieucentrum Utrecht](https://mcu.nl)
            om Snuffelfiets data te bekijken en analyseren.
            De code is te vinden op de 
            [MCU GitHub voor Snuffelfiets]
            (https://github.com/MilieuCentrumUtrecht/Snuffelfiets).
            """
            )

    with st.expander("Navigatie", expanded=True):

        st.page_link(
            package_root / "snuffelfiets_app.py",
            label="Overzicht", icon="🚲",
            )
        st.page_link(
            package_root / "pages" / "sodaq.py",
            label="Sodaq", icon="🧪",
            )
        st.page_link(
            package_root / "pages" / "testfeatures.py",
            label="Testpage", icon="🧪",
            )

    st.divider()
