from pathlib import Path
from importlib.resources import files

import urllib

import streamlit as st

import geopandas as gpd

import plotly.express as px
import plotly.graph_objects as go

from snuffelfiets import plotting


def page_navigation(
        ) -> None:
    """Create navigation panel for pages of Snuffelfiets app."""

    package_root = files("snuffelfiets")
    image_dir = package_root / "static" / "images"
    filepath = image_dir / "cropped-logo-mcu-1-1.png"
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
            "snuffelfiets_app.py",
            label="Overzicht", icon="🚲",
            )
        st.page_link(
            "pages/sodaq.py",
            label="Sodaq", icon="🧪",
            )
        st.page_link(
            "pages/testfeatures.py",
            label="Testpage", icon="🧪",
            )

    st.divider()


def init_session_state(
        items: dict = {},
        ) -> None:
    """Ensure session_state initialization."""

    st_init = {
        "package_root": files("snuffelfiets"),
        "data_directory": str(Path("~").expanduser() / "snuffelfiets_data"),
    }
    st_init = {**items, **st_init}
    for k, v in st_init.items():
        if k not in st.session_state:
            st.session_state[k] = v

    validate_directory()


def validate_directory():
    """Ensure a directory for external data."""
    Path(st.session_state.data_directory).mkdir(parents=True, exist_ok=True)


def box(df, id_var, color_var, range_color, dmaptype="box"):
    """Plot the data over time or categories."""

    df[id_var] = df[id_var].astype("category")

    plot_args = dict(
        # x=id_var,
        # y=color_var,
        color=id_var,
        range_y=range_color,
        height=800,
        )

    if id_var == "entity_id":
        df["entity_id"] = "D-" + df["entity_id"].astype("str")
    elif id_var == "hour":
        plot_args["category_orders"] = {"hour": list(range(24))}

    if dmaptype == "scatter":
        fig = px.scatter(df, x="date_time", y=color_var, **plot_args)
    elif dmaptype == "line":
        fig = px.line(df, x="date_time", y=color_var, **plot_args)
        fig.update_traces(connectgaps=False)
    elif dmaptype == "violin":
        fig = px.violin(df, x=id_var, y=color_var, **plot_args)
    else:  # dmaptype == "box":
        fig = px.box(df, x=id_var, y=color_var, **plot_args)

    if len(df[id_var].unique()) > 20:
        fig.update_xaxes(rangeslider_visible=True)

    return fig


def scatter_map(df, color_var="pm2_5", range_color=[0., 40.], aux_df={}):
    """Draw the data points on a map."""

    # TODO: zoom and center to bounds
    plot_args = dict(
        lat=df.geometry.y,
        lon=df.geometry.x,
        color=color_var,
        color_continuous_scale="Plasma",
        range_color=range_color,
        hover_name=df.index,
        zoom=10,
        center=st.session_state.map_center,
        height=800,
        map_style="carto-positron",
        title=f"Metingen - gekleurd voor {color_var}",
        # size="size",
        animation_frame="selected_ride",
        )
    fig_map = plotting.scatter_map(df, plot_args)

    for name, aux_df in aux_df.items():
        d = dict(
            name=name,
            mode="markers",
            lon=aux_df.geometry.x,
            lat=aux_df.geometry.y,
            hovertext=aux_df.hovertext,
            )
        fig_map.add_trace(go.Scattermap(**d))

    for d in st.session_state.map_polys:
        fig_map.add_trace(go.Scattermap(**d))

    # fig_map.update_geos(fitbounds="locations")

    st.plotly_chart(fig_map, key="fig_map", width="stretch",
        selection_mode=("points", "box", "lasso"),
        on_select=update_selections,
        height=800,
    )


def update_selections():
    """Update session_state with selected points on the map."""

    st.session_state["selection"] = [
        p["hovertext"] for p in st.session_state.fig_map["selection"]["points"]
        ]


def download_borders(directory, year, level, gentype='gegeneraliseerd'):
    """Download borders from PDOK."""

    if level.startswith('gemeente'): level = 'gemeente'

    filename = f'{level}_{gentype}_{year:d}.geojson'
    filepath = Path(directory, filename)

    if not Path.exists(filepath):

        base_url = 'https://service.pdok.nl/cbs/gebiedsindelingen'
        service = 'GetFeature&service=WFS&version=2.0.0'
        typename = f'typeName={level}_{gentype}'
        outputformat = f'outputFormat=json'
        cosys = f'srsName=EPSG:4326'
        request_string = f'{service}&{typename}&{outputformat}&{cosys}'
        url = f'{base_url}/{year:d}/wfs/v1_0?request={request_string}'

        urllib.request.urlretrieve(url, filepath)

    return filepath


def get_bounds(year=2023, level="provincie", statnaam=["Utrecht"]):

    level = st.session_state["level"]
    statnaam = st.session_state["names"]

    filepath = download_borders(st.session_state.data_directory, year, level)

    df_bounds = gpd.read_file(filepath).to_crs(epsg=4326)

    df_bounds = df_bounds[df_bounds.statnaam.isin(statnaam)]

    polys = []
    for naam in statnaam:
        df_poly = df_bounds[df_bounds.statnaam==naam]
        d = {"name": f"{level} {naam}", "mode": "lines"}
        d["lat"], d["lon"], aux = plotting.geometry2latlon(df_poly)
        polys.append(d)

    df_dissolved = df_bounds.dissolve()
    map_center = {
        "lat": df_dissolved.centroid.y.values[0],
        "lon": df_dissolved.centroid.x.values[0],
        }

    return df_bounds, map_center, polys


def map_bounding():
    level = st.segmented_control(
        "Map focus",
        options=["provincie", "gemeente"],
        default="provincie",
        )
    filepath = download_borders(st.session_state.data_directory, 2023, level)
    df_bounds = gpd.read_file(filepath).to_crs(epsg=4326)
    names = st.multiselect(f"Naam {level}", list(df_bounds["statnaam"]), default=["Utrecht"])
    st.session_state["level"] = level
    st.session_state["names"] = names
    map_filter = st.segmented_control(
        "restrict",
        options=["within bounding box", "within polygons", "no filtering"],
        default="within bounding box",
        )
    df_bounds, map_center, d = get_bounds()  # FIXME: orig
    st.session_state["map_center"] = map_center
    st.session_state["map_polys"] = d

    return map_filter, df_bounds
