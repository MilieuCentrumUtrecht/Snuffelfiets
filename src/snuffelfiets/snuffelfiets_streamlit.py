from pathlib import Path
from importlib.resources import files

import streamlit as st

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


def init_session_state(
        items: dict = {},
        ) -> None:
    """Ensure session_state initialization."""

    package_root = files("snuffelfiets")

    st_init = {
        "package_root": package_root,
        "data_directory": package_root / "static" / "data",
    }
    st_init = {**items, **st_init}
    for k, v in st_init.items():
        if k not in st.session_state:
            st.session_state[k] = v


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


