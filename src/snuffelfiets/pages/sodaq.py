from pathlib import Path

import pandas as pd
import geopandas as gpd

import streamlit as st

from snuffelfiets import (
    analyse,
    snuffelfiets_streamlit,
    )

from luchtkwaliteit import lml


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


@st.cache_data
def load_lml_data(start, end, obsprop="PM25", thing_ids=[]):

    # add LML # NOTE: one week max!, 100 requests per 5 minutes
    base_url = "https://api.luchtmeetnet.nl/open_api"
    thing_ids =  thing_ids or ["NL10636", "NL10639", "NL10643", "NL10644"]
    if thing_ids:
        return lml.load_dataframe(thing_ids, base_url, obsprop, start, end)


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
        test_data = Path(st.session_state.package_root) / "static" / "data"
        filepaths = [test_data / filename]

    df_orig = load_dataframe_sodaq_air(filepaths)

    # Get lml data for the full day.
    start_ = df_orig["date_time"].min().strftime("%Y-%m-%dT00:00:00")
    end_ = df_orig["date_time"].max().strftime("%Y-%m-%dT23:59:59")
    df_lml_orig = load_lml_data(start_, end_)  # Pre-load Utrecht


with st.sidebar:

    format_ = "%Y-%m-%dT%H:%M:%S"
    start = df_orig["date_time"].min().strftime(format_)
    end = df_orig["date_time"].max().strftime(format_)

    with st.expander("Select interval", expanded=False):

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
        df_lml = df_lml_orig[
            (df_lml_orig[col_name] >= col_range[0]) &
            (df_lml_orig[col_name] <= col_range[1])
            ]

        format_ = "%Y-%m-%dT%H:%M:%S"
        start = df["date_time"].min().strftime(format_)
        end = df["date_time"].max().strftime(format_)

    with st.expander("Select devices", expanded=False):

        ids = []
        ids = ids or df["entity_id"].unique()
        ids = list(ids.astype(str))
        ids_sel = st.selectbox("device_IDs", [""] + ids, index=0)
        if ids_sel:
            ids = [ids_sel]
        if ids:
            df = df.loc[df["entity_id"].astype(str).isin(ids)]

    with st.expander("Select rides", expanded=True):

        ids = list(df.rit_id.unique())
        selection_mode = st.segmented_control(
            "Mode",
            options=["single", "multi"],
            default="multi",
            width="stretch",
            )
        ids_sel = st.segmented_control(
            "Rit IDs",
            options=ids,
            selection_mode=selection_mode,
            default=ids[0] if selection_mode == "single" else ids,
            )
        ids_sel = ids_sel if isinstance(ids_sel, list) else [ids_sel]

        df["size"] = 1.
        df["selected_ride"] = False
        if selection_mode == "single":
            df.loc[df["rit_id"].isin(ids_sel), "selected_ride"] = True
            df = df.sort_values("selected_ride", axis=0, ascending=False)

        df_sel_rides = df.loc[df["rit_id"].isin(ids_sel)]
        min_time = df_sel_rides["date_time"].min()
        max_time = df_sel_rides["date_time"].max()

    with st.expander("Plot settings", expanded=False):

        vars = [
            "pm10",
            "pm2_5",
            "pm1_0",
            "snelheid",
            "battery",
            "uptime",
            "temperature",
            "humidity",
            "entity_id",
            "afstand",
            ]
        color_var = st.selectbox("Variabele", vars, index=1)

        id_var = st.segmented_control(
            "Category axis",
            ["entity_id", "rit_id"],
            default="rit_id",
            width="stretch",
            )

        if pd.api.types.is_numeric_dtype(df[color_var]):
            drange = [0., df[color_var].max()]
            range_color = st.slider(
                "Colour range",
                min_value=drange[0],
                max_value=drange[1],
                value=drange,
                )
        else:
            range_color = [None, None]

        st.session_state["legend_orientation"] = st.segmented_control(
            "Legend orientation",
            ["horizontal", "vertical"],
            default="horizontal",
        )

    st.session_state["lml"] = st.checkbox("Luchtmeetnet", value=False)
    if st.session_state.lml:
        station_numbers_all = [
            f"{station['number']} - {station['location']}"
            for station in snuffelfiets_streamlit.get_stations()
            ]
        defaults = [
            "NL10636 - Utrecht-Kardinaal de Jongweg",
            "NL10639 - Utrecht-Constant Erzeijstraat",
            "NL10643 - Utrecht-Griftpark",
            "NL10644 - Cabauw-Wielsekade",
            ]
        st.session_state["lml_station_numbers"] = st.multiselect(
            "Stations", station_numbers_all, default=defaults
            )

    st.divider()

cols_main = st.columns(2)
con1 = cols_main[0].container()
con2 = cols_main[1].container()

with con1.expander("Ritten - scatter_map", expanded=True):

    aux_df = {}

    geom = gpd.points_from_xy(df["lon"], df["lat"])
    gdf = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
    gdf["hovertext"] = "SOD_" + gdf.index.astype(str) + "___" + gdf.entity_id.astype(str)
    gdf = gdf[[color_var, "size", "selected_ride", "hovertext", "geometry"]]

    if st.session_state.lml:
        aux_df["Landelijk Meetnet"] = snuffelfiets_streamlit.aux_trace_lml(
            st.session_state.lml_station_numbers
            )

    snuffelfiets_streamlit.scatter_map(gdf, color_var, [0., range_color[1]], aux_df)



with st.sidebar:
    # cols = st.columns(2)
    dmaptype = st.radio(
        "Graph type",
        ["scatter", "line", "box"],  #, "violin"],
        horizontal=True,
        width="stretch",
        )

    id_var = st.segmented_control(
        "Segment by ...",
        ["entity_id", "rit_id", "date", "hour"],
        default="rit_id",
        width="stretch",
        )

df = df[["date_time", id_var, color_var]]


if st.session_state.lml:

    thing_ids = [x[:7] for x in st.session_state["lml_station_numbers"]]
    df_lml = df_lml[df_lml.station_number.isin(thing_ids)]

    obsprop = "PM25"

    df_lml = df_lml.rename({obsprop: color_var, 'thing_id': id_var}, axis=1)
    df_lml = df_lml[['date_time', id_var, color_var]]
    df = pd.concat([df, df_lml], axis=0)




with con2.expander("Devices and rides - box plot", expanded=True):

    fig = snuffelfiets_streamlit.box(
        df, id_var, color_var, range_color, dmaptype,
        )
    fig.update_xaxes(range=[min_time, max_time], rangeslider_visible=True)

    st.plotly_chart(fig, width="stretch", config={"scrollZoom": True})
