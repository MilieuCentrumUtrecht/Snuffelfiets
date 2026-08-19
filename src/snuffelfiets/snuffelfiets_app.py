from pathlib import Path

import streamlit as st

from snuffelfiets import snuffelfiets_streamlit


PACKAGE_ROOT = Path(__file__).parent


st.set_page_config(
    page_title="Snuffelfiets dashboard",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
    )


# initialize
ckan_secret = "CKAN_API_KEY" in st.secrets.keys()
st_init = {
    "package_root": PACKAGE_ROOT,
    "data_directory": PACKAGE_ROOT / "static" / "data",
    "api_key": st.secrets["CKAN_API_KEY"] if ckan_secret else "",
}
for k, v in st_init.items():
    if k not in st.session_state:
        st.session_state[k] = v


with st.sidebar:

    snuffelfiets_streamlit.page_navigation()

    st.session_state.api_key = st.text_input(
        "CKAN API key",
        value=st.session_state.api_key,
        disabled=True,
        )

    st.session_state.data_directory = st.text_input(
        "Snuffelfiets data directory",
        value=PACKAGE_ROOT / "static" / "data",
        )

    st.divider()
