import streamlit as st

from snuffelfiets import snuffelfiets_streamlit

with st.sidebar:
    snuffelfiets_streamlit.page_navigation()

st.toast("Just testing stuff here!", icon="🧪")

st.balloons()
