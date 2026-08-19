from pathlib import Path

import pandas as pd

import streamlit as st

from snuffelfiets import (
    analyse,
    snuffelfiets_streamlit,
    )


with st.sidebar:
    snuffelfiets_streamlit.page_navigation()


st_init = {
}
for k, v in st_init.items():
    if k not in st.session_state:
        st.session_state[k] = v


@st.cache_data
def load_dataframe_sodaq_air(
    filepaths: list[Path],
    ) -> pd.DataFrame:
    """Load a dataframe from Sodaq Air CSV files."""

    df = pd.concat([pd.read_csv(filepath) for filepath in filepaths], axis=0)

    df['entity_id'] = df['imei'].astype('category')

    # preproc
    rit_splitter_interval = 1800
    df = analyse.bewerk_timestamp(
        df, split=True, col_name="created_at", format_="%Y-%m-%dT%H:%M:%S.%f",
        )
    df = analyse.split_in_ritten(
        df, t_seconden=rit_splitter_interval, col_lat="lat", col_lon="lon",
        )
    mapper = {'pm_1': 'pm1_0', 'pm_2_5': 'pm2_5', 'pm_10': 'pm10'}
    df = df.rename(mapper, axis=1)

    df["hour"] = df["date_time"].dt.hour
    df["date"] = df["date_time"].dt.date

    df['imei'] = df['imei'].astype('category')
    df['rit_id'] = df['rit_id'].astype('category')

    return df


with st.sidebar:

    filepaths = st.file_uploader(
        "Upload Sodaq Air CSV files", accept_multiple_files=True,
    )
    if not filepaths:
        prefix='sodaq-air-measurements'
        suffix = ""
        filename = st.text_input(
            "Filename", f"{prefix}{suffix}.csv", on_change=None,
            )
        filepaths = [Path(st.session_state.data_directory) / filename]

    df_orig = load_dataframe_sodaq_air(filepaths)


st.dataframe(df_orig)
