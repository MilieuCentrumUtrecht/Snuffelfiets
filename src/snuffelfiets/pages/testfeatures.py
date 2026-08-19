import streamlit as st

from snuffelfiets import snuffelfiets_streamlit

snuffelfiets_streamlit.init_session_state()

with st.sidebar:
    snuffelfiets_streamlit.page_navigation()

st.toast("Just testing stuff here!", icon="🧪")

st.balloons()
