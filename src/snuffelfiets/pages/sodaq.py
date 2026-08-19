from pathlib import Path

import pandas as pd

import streamlit as st

from snuffelfiets import (
    analyse,
    snuffelfiets_streamlit,
    )


snuffelfiets_streamlit.init_session_state()

with st.sidebar:
    snuffelfiets_streamlit.page_navigation()


@st.cache_data
def load_dataframe_sodaq_air(
    filepaths: list[Path],
    ) -> pd.DataFrame:
    """Load a dataframe from Sodaq Air CSV files."""

    df = pd.concat([pd.read_csv(filepath) for filepath in filepaths], axis=0)

    df["entity_id"] = df["imei"].astype("category")

    # preproc
    rit_splitter_interval = 1800
    df = analyse.bewerk_timestamp(
        df, split=True, col_name="created_at", format_="%Y-%m-%dT%H:%M:%S.%f",
        )
    df = analyse.split_in_ritten(
        df, t_seconden=rit_splitter_interval, col_lat="lat", col_lon="lon",
        )
    mapper = {"pm_1": "pm1_0", "pm_2_5": "pm2_5", "pm_10": "pm10"}
    df = df.rename(mapper, axis=1)

    df["hour"] = df["date_time"].dt.hour
    df["date"] = df["date_time"].dt.date

    df["imei"] = df["imei"].astype("category")
    df["rit_id"] = df["rit_id"].astype("category")

    return df


with st.sidebar:

    filepaths = st.file_uploader(
        "Upload Sodaq Air CSV files", accept_multiple_files=True,
    )
    if not filepaths:
        prefix="sodaq-air-measurements"
        suffix = ""
        filename = st.text_input(
            "Filename", f"{prefix}{suffix}.csv", on_change=None,
            )
        filepaths = [Path(st.session_state.data_directory) / filename]

    df_orig = load_dataframe_sodaq_air(filepaths)


with st.sidebar:

    format_ = "%Y-%m-%dT%H:%M:%S"
    start = df_orig["date_time"].min().strftime(format_)
    end = df_orig["date_time"].max().strftime(format_)

    with st.expander(f"Select interval", expanded=False):

        cols = st.columns(2)
        start_date = cols[0].date_input(
            "Start",
            value=df_orig["date_time"].min(),
            min_value=start, max_value=end,
            format="YYYY-MM-DD",
            )
        start_time = cols[1].slider(
            "Tijd start",
            value=df_orig["date_time"].min().time(),
            label_visibility="hidden",
            )

        cols = st.columns(2)
        end_date = cols[0].date_input(
            "Eind",
            value=df_orig["date_time"].max(),
            min_value=start, max_value=end,
            format="YYYY-MM-DD",
            )
        end_time = cols[1].slider(
            "Tijd eind",
            value=df_orig["date_time"].max().time(),
            label_visibility="hidden",
            )

        # Filter on timestamps.
        col_name = "date_time"
        col_range = [
            f"{start_date} {start_time.strftime('%H:%M:%S')}",
            f"{end_date} {end_time.strftime('%H:%M:%S')}",
        ]
        df = df_orig[
            (df_orig[col_name] >= col_range[0]) & 
            (df_orig[col_name] <= col_range[1])
            ]

        format_ = "%Y-%m-%dT%H:%M:%S"
        start = df["date_time"].min().strftime(format_)
        end = df["date_time"].max().strftime(format_)

    with st.expander(f"Select devices", expanded=False):

        ids = []
        ids = ids or df["entity_id"].unique()
        ids_sel = st.selectbox("device_IDs", [""] + ids.astype(str), index=0)
        if ids_sel:
            ids = [ids_sel]
        if ids:
            df = df.loc[df["entity_id"].astype(str).isin(ids)]


st.dataframe(df)
