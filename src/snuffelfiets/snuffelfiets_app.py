from pathlib import Path
from importlib.resources import files

import streamlit as st

from snuffelfiets import snuffelfiets_streamlit

st.set_page_config(
    page_title="Snuffelfiets dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
    )


# initialize
ckan_secret = "CKAN_API_KEY" in st.secrets.keys()
st_init = {
    "api_key": st.secrets["CKAN_API_KEY"] if ckan_secret else "",
    'map_center': None,  # TODO: prov center from rapportage
    'map_polys': None,
    "level": "provincie",
    "statnaam": ["Utrecht"],
    'selection': [],
    "legend_orientation": "horizontal",
    }
snuffelfiets_streamlit.init_session_state(st_init)


with st.sidebar:

    snuffelfiets_streamlit.page_navigation()

    st.session_state.api_key = st.text_input(
        "CKAN API key",
        value=st.session_state.api_key,
        disabled=True,
        )

    st.text_input(
        "Snuffelfiets data directory",
        key="data_directory",
        value=str(Path("~").expanduser() / "snuffelfiets_data"),
        on_change=snuffelfiets_streamlit.validate_directory,
        )

    snuffelfiets_streamlit.map_bounding()

    st.divider()
