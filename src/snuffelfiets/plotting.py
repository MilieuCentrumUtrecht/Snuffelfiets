#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het plotten van Snuffelfiets data.

"""

import json
import urllib.request
from pathlib import Path

from folium.folium import Map
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.axes import Axes
from matplotlib.collections import PathCollection
from matplotlib.markers import MarkerStyle
import plotly.graph_objects as go
import plotly.figure_factory as ff
import plotly.express as px
from plotly.colors import hex_to_rgb
import pandas as pd
from itertools import product
from PIL import Image, ImageDraw
import folium


def scatter_mapbox(df, plot_args={}, layout_args={}):
    """Maak een scatter plot on the map."""

    plot_args_defaults = dict(
        data_frame=df,
        lat="latitude",
        lon="longitude",
        color="pm2_5",
        center=dict(lat=52.090695, lon=5.121314),
        zoom=10,
        animation_frame=None,
    )

    layout_args_defaults = dict(
        mapbox_style="carto-positron",
        margin=dict(b=0, t=0, l=0, r=0),
    )

    plot_args = {**plot_args_defaults, **plot_args}
    layout_args = {**layout_args_defaults, **layout_args}

    fig = px.scatter_mapbox(**plot_args)
    fig.update_layout(**layout_args)

    return fig


def hexbin_mapbox(df, hexagon_size=None, hexbin_args={}, layout_args={}):
    """Maak een hexbin plot."""

    default_hexbin_args = dict(
        data_frame=df,
        lat="latitude",
        lon="longitude",
        agg_func=np.average,
        color="pm2_5",
        animation_frame=None,
        color_continuous_scale=["green", "red"],
        range_color=[0, 50],
        show_original_data=False,
        nx_hexagon=200,
        min_count=6,
        opacity=0.3,
        labels={"color": "PM2.5"},
        center=dict(lat=52.090695, lon=5.121314),
        zoom=10,
    )
    default_layout_args = dict(
        mapbox_style="carto-positron",
        margin=dict(b=0, t=0, l=0, r=0),
    )

    hexbin_args = {**default_hexbin_args, **hexbin_args}
    layout_args = {**default_layout_args, **layout_args}

    if hexagon_size is not None:
        hexbin_args["nx_hexagon"] = np.ceil(
            (df["longitude"].max() - df["longitude"].min()) / hexagon_size,
        ).astype("int")

    if hexbin_args["nx_hexagon"] > 500:
        print("Too many hexagons; please increase hexagon_size")
        return

    fig = ff.create_hexbin_mapbox(**hexbin_args)
    fig.update_layout(**layout_args)

    return fig


def line_mapbox(df, plot_args={}, layout_args={}):
    """Maak een line plot."""

    plot_args_defaults = dict(
        data_frame=df,
        lat="latitude",
        lon="longitude",
        color="rit_id",
        center=dict(lat=52.090695, lon=5.121314),
        zoom=10,
        animation_frame=None,
    )

    layout_args_defaults = dict(
        mapbox_style="carto-positron",
        margin=dict(b=0, t=0, l=0, r=0),
    )

    plot_args = {**plot_args_defaults, **plot_args}
    layout_args = {**layout_args_defaults, **layout_args}

    fig = px.line_mapbox(**plot_args)
    fig.update_layout(**layout_args)

    return fig


def save_fig(fig, outputstem, fig_formats=["html", "pdf"]):
    """Save de figuur."""

    for fig_format in fig_formats:
        if fig_format == "html":
            fig.write_html(f"{outputstem}.{fig_format}")
        else:
            fig.write_image(f"{outputstem}.{fig_format}")


def discrete_colorscale(bvals=[], colors=[]):
    """Functie to create discrete colorscale.

    bvals -  list of values bounding intervals/ranges of interest
    colors - list of rgb or hex color codes for values in [bvals[k], bvals[k+1]], 0 <= k < len(bvals)-1
    returns  a nonuniform   discrete colorscale
    """

    if not bvals:
        bvals = [
            0,
            3,
            6,
            9,
            12,
            18,
            24,
            30,
            38,
            46,
            60,
            100,
            100,
        ]
    if not colors:
        colors_hex = [
            "#0020c5",
            "#006df8",
            "#2dcdfb",
            "#c4ecfd",
            "#fffed0",
            "#fffc4d",
            "#f4e645",
            "#ffb255",
            "#ff9845",
            "#fe7626",
            "#ff0a17",
            "#dc0625",
        ]
        colors = [f"rgb{hex_to_rgb(c)}" for c in colors_hex]

    if len(bvals) != len(colors) + 1:
        raise ValueError(
            f"len boundaries {len(bvals)} should be equal to len colours + 1 = {len(colors)+1}"
        )

    bvals = sorted(bvals)
    nvals = [
        (v - bvals[0]) / (bvals[-1] - bvals[0]) for v in bvals
    ]  # normalized values

    dcolorscale = []
    for k in range(len(colors)):
        dcolorscale.extend([[nvals[k], colors[k]], [nvals[k + 1], colors[k]]])

    return dcolorscale


def download_borders_utrecht(directory, year=2023, levels=["gemeente", "provincie"]):
    """Download PDOK data to file.

    # NOTE: This is a workaround for an error on the API call
    """

    filepaths = []
    for level in levels:
        filepath = Path(directory, f"{level}_gegeneraliseerd_{year:d}.geojson")
        if not Path.exists(filepath):
            url = f"https://service.pdok.nl/cbs/gebiedsindelingen/{year:d}/wfs/v1_0?request=GetFeature&service=WFS&version=2.0.0&typeName={level}_gegeneraliseerd&outputFormat=json"
            urllib.request.urlretrieve(url, filepath)
        filepaths.append(filepath)

    return filepaths


def get_borders_utrecht(
    directory,
    filename_provincies="provincies_gegeneraliseerd_2023.geojson",
    filename_gemeenten="gemeenten_gegeneraliseerd_2023.geojson",
):
    """Return the provincial and township borders of Utrecht."""

    provincies = load_polygons_geojson(directory, filename_provincies)
    names = ["Utrecht"]
    provincies = select_polygons(provincies, names)

    gemeenten = load_polygons_geojson(directory, filename_gemeenten)
    names = [
        "Amersfoort",
        "Baarn",
        "De Bilt",
        "Bunnik",
        "Bunschoten",
        "Eemnes",
        "Houten",
        "IJsselstein",
        "Leusden",
        "Lopik",
        "Montfoort",
        "Nieuwegein",
        "Oudewater",
        "Renswoude",
        "Rhenen",
        "De Ronde Venen",
        "Soest",
        "Stichtse Vecht",
        "Utrecht",
        "Utrechtse Heuvelrug",
        "Veenendaal",
        "Vijfheerenlanden",
        "Wijk bij Duurstede",
        "Woerden",
        "Woudenberg",
        "Zeist",
    ]
    gemeenten = select_polygons(gemeenten, names)

    return provincies, gemeenten


def load_polygons_geojson(directory, filename):
    """ "Read a json file."""

    p = Path(directory, filename).expanduser()
    with open(p) as json_file:
        polygons = json.load(json_file)

    return polygons


def select_polygons(polygons_in, names, prop="statnaam"):
    """Select a subset of the (CBS) geojson by name."""

    polygons = {}
    polygons["type"] = polygons_in["type"]
    feats = [
        feat for feat in polygons_in["features"] if feat["properties"][prop] in names
    ]
    polygons["features"] = feats

    return polygons


def add_marker(amap, lat: float, lon: float, text: str) -> Map:
    """Add a marker to a map

    Supports `folium.Map` and plotly maps.

    Args:
        amap: Map to which the marker should be added
        lat: Latitude the marker should be put
        lat: Longitude the marker should be put
        text: Text added to the marker
    """
    if isinstance(amap, folium.folium.Map):
        folium.RegularPolygonMarker(
            [lat, lon],
            popup=text,
            fill_color="#00ff40",
            number_of_sides=3,
            radius=10,
        ).add_to(my_map)
    else:
        amap.add_trace(
            go.Scattermapbox(
                lat=[lat],
                lon=[lon],
                mode="markers",
                marker_size=14,
                text=[text],
            ),
            1,
            1,
        )
    return amap


def add_title(fig, text=None, df=None):
    """Add a title to a figure

    Supports plotly maps.

    Args:
        fig: Figure to which the title should be added
        text: The title
        df: `pd.DataFrame` containing "recording_timestamp", which will be
            used as title
    """
    if text is None and df is None:
        raise Exception
    elif text is not None:
        pass
    elif df is not None:
        text = df["recording_timestamp"].iloc[0]
        pass
    else:
        raise Exception
    fig = fig.update_layout(
        title=go.layout.Title(
            text=text,
            xref="paper",
            x=0.55,
            yref="paper",
            y=1,
        )
    )
    return fig


def create_humidity_plot(main_ax, df, x_metric):
    """
    Args:
        main_ax: matplotlib axis on which the data should be plotted
        df: pd.DataFrame containing the to-be-plotted data
        x_metric: Variable plotted on the x-axis
    """
    main_ax.set_xlabel(x_metric)
    main_ax.set_ylabel("temperature")
    tcolor = "black"
    path1: PathCollection = main_ax.scatter(
        df[x_metric], df["temperature"], c=tcolor, label="temperature"
    )

    pcolor = "green"
    ax = secondairy_spines(main_ax, pcolor, ylabel="pressure", xshift=1)
    path2: PathCollection = ax.scatter(
        df[x_metric], df["pressure"], c=pcolor, label="pressure"
    )

    hcolor = "red"
    ax = secondairy_spines(main_ax, hcolor, ylabel="humidity")
    path3: PathCollection = ax.scatter(
        df[x_metric], df["humidity"], c=hcolor, label="humidity"
    )

    lns = [path1, path2, path3]
    labs = [l.get_label() for l in lns]
    ax.legend(lns, labs, loc=0)


def create_overview_plot(dfs, y_metric="pm2_5", x_metric="distance"):
    """Create an overview of the weather of the day

    Args:
        dfs: `pd.DataFrame`s containing the data to be plotted. This is a
            combination of MCU-processed Snuffelfiets data, enchanced with
            KNMI weather information.

    Kwargs:
        y_metric: Metric used for "pollution". Can be a string contained
            in the columns of dfs.
        x_metric: Metric used for "distance". Can be a string contained
            in the columns of dfs.
    """
    fig = plt.figure(layout="constrained")
    gs = GridSpec(3, len(dfs), figure=fig)

    ax1 = fig.add_subplot(gs[0, :])
    axs = [fig.add_subplot(gs[1, ii]) for ii in range(len(dfs))]

    for ii, df in enumerate(dfs):
        ax1.scatter(dfs[ii][x_metric], dfs[ii][y_metric], label=print_id(dfs[ii]))
        create_humidity_plot(axs[ii], dfs[ii], x_metric)
        quantiles = df[["temperature", "pressure", "humidity"]].quantile(
            [0.25, 0.5, 0.75]
        )
        table_ax = fig.add_subplot(gs[2, ii])  # , frame_on=False)
        table_ax.axis("off")
        minus = quantiles.loc[0.25] - quantiles.loc[0.5]
        plus = quantiles.loc[0.75] - quantiles.loc[0.5]
        quantiles = pd.concat([quantiles.loc[0.5], minus, plus], axis="columns")
        formatted = quantiles.apply(
            lambda args: "${:.0f}_{{{:.1f}}}^{{{:.1f}}}$".format(*args), axis="columns"
        ).to_frame()
        formatted.columns = ["$value^{75q}_{25q}$"]
        the_table = pd.plotting.table(
            table_ax,
            formatted,
            loc="center",
            cellLoc="center",
        )
        the_table.set_fontsize(24)
    return fig


    """Select a subset of the (CBS) geojson by name."""

    polygons = {}
    polygons["type"] = polygons_in["type"]
    feats = [
        feat for feat in polygons_in["features"] if feat["properties"][prop] in names
    ]
    polygons["features"] = feats

    return polygons


def get_mapbox_layers(data_directory):
    """Import Utrecht province and township polygons from the web

    Args:
        data_directory: Directory in which the mapbox file will be downloaded

    Returns:
        mapbox_layers: mapboxes in `mapbox_layers` format
    """

    # Download the polygons.
    filepaths = download_borders_utrecht(data_directory)

    # Extract the relevant polygons.
    provincies, gemeenten = get_borders_utrecht(data_directory, *filepaths)

    # Enter into dictionary in the mapbox_layers format.
    mapbox_layers = [
        {
            "name": "Gemeenten",
            "below": "traces",
            "sourcetype": "geojson",
            "type": "line",
            "color": "gray",
            "source": gemeenten,
        },
        {
            "name": "Provincies",
            "below": "traces",
            "sourcetype": "geojson",
            "type": "line",
            "color": "red",
            "source": provincies,
        },
    ]

    return mapbox_layers


def secondairy_spines(axes, color="black", ylabel=None, spine_type="right", xshift=1.1):
    """
    Parameters
    ----------
    axes : `~matplotlib.axes.Axes`
        The `~.axes.Axes` instance where the spine is added.
    spine_type : str
        The spine type. E.g. "right"
    path : `~matplotlib.path.Path`
        The `.Path` instance used to draw the spine.

    Other Parameters
    ----------------
    **kwargs
        Valid keyword arguments are:

        %(Patch:kwdoc)s
    """
    ax: Axes = axes.twinx()
    spine = ax.spines[spine_type]
    spine.set_position(("axes", xshift))
    spine.set_color(color)
    if ylabel:
        ax.set_ylabel(ylabel)
        ax.yaxis.label.set_color(color)
    ax.tick_params(axis="y", colors=color)

    return ax


def plot_hourly(
    df,
    variables=None,
    axs=None,
    plot_kwargs={},
    show=False,
    savefig=False,
    savefig_args=[],
    savefig_kwargs={},
):
    """Plot hourly data scraped from the KNMI API"""
    # ALL seems to be:
    # STN, DD, FH, FF, FX, T, T10N, TD, SQ, Q, DR, RH, P, VV, N, U, WW, IX, M, R, S, O, Y, HH.1, YYYYMMDD.1
    # DD: Windrichting (in graden) gemiddeld over de laatste 10 minuten van het afgelopen uur (360=noord, 90=oost, 180=zuid, 270=west, 0=windstil 990=veranderlijk.
    # FH: Uurgemiddelde windsnelheid (in 0.1 m/s).
    # FF: Windsnelheid (in 0.1 m/s) gemiddeld over de laatste 10 minuten van het afgelopen uur
    # FX: Hoogste windstoot (in 0.1 m/s) over het afgelopen uurvak
    # T: Temperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming
    # T10N: Minimumtemperatuur (in 0.1 graden Celsius) op 10 cm hoogte in de afgelopen 6 uur
    # TD: Dauwpuntstemperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming
    # SQ: Duur van de zonneschijn (in 0.1 uren) per uurvak, berekend uit globale straling (-1 for <0.05 uur)
    # Q: Globale straling (in J/cm2) per uurvak
    # DR: Duur van de neerslag (in 0.1 uur) per uurvak
    # RH: Uursom van de neerslag (in 0.1 mm) (-1 voor <0.05 mm)
    # P: Luchtdruk (in 0.1 hPa) herleid naar zeeniveau, tijdens de waarneming
    # VV: Horizontaal zicht tijdens de waarneming (0=minder dan 100m, 1=100-200m, 2=200-300m,..., 49=4900-5000m, 50=5-6km, 56=6-7km, 57=7-8km, ..., 79=29-30km, 80=30-35km, 81=35-40km,..., 89=meer dan 70km)
    # N: Bewolking (bedekkingsgraad van de bovenlucht in achtsten), tijdens de waarneming (9=bovenlucht onzichtbaar)
    # U: Relatieve vochtigheid (in procenten) op 1.50 m hoogte tijdens de waarneming
    # WW: Weercode (00-99), visueel(WW) of automatisch(WaWa) waargenomen, voor het actuele weer of het weer in het afgelopen uur.
    # IX: Weercode indicator voor de wijze van waarnemen op een bemand of automatisch station (1=bemand gebruikmakend van code uit visuele waarnemingen, 2,3=bemand en weggelaten (geen belangrijk weersverschijnsel, geen gegevens), 4=automatisch en opgenomen (gebruikmakend van code uit visuele waarnemingen), 5,6=automatisch en weggelaten (geen belangrijk weersverschijnsel, geen gegevens), 7=automatisch gebruikmakend van code uit automatische waarnemingen)
    # M: Mist 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming
    # R: Regen 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming
    # S: Sneeuw 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming
    # O: Onweer 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming
    # Y: IJsvorming 0=niet voorgekomen, 1=wel voorgekomen in het voorgaande uur en/of tijdens de waarneming
    # HH.1: Hour
    # YYYMMDD.1: date

    # FH: Uurgemiddelde windsnelheid (in 0.1 m/s).
    # T: Temperatuur (in 0.1 graden Celsius) op 1.50 m hoogte tijdens de waarneming
    # SQ: Duur van de zonneschijn (in 0.1 uren) per uurvak, berekend uit globale straling (-1 for <0.05 uur)
    # P: Luchtdruk (in 0.1 hPa) herleid naar zeeniveau, tijdens de waarneming
    if variables is None:
        variables = ["FH", "T", "SQ", "RH", "P", "DD"]
    df = df[variables]
    angles = df.pop("DD")
    df["Wind speed (m/s)"] = df.pop("FH") / 10
    df["Temperature (oC)"] = df.pop("T") / 10
    df["Sunshine (hours)"] = df.pop("SQ") / 10
    df["Sunshine (fraction of hour)"] = df.pop("Sunshine (hours)") / 10
    df["Precipitation (mm)"] = df.pop("RH") / 10
    df["Pressure (bar)"] = df.pop("P") / 1e4
    # df.index.get_level_values("YYYYMMDD_HH")
    # df = df.drop(["HH.1", "YYYYMMDD.1"], axis="columns")
    # fig = plt.figure(layout="constrained")
    # gs = GridSpec(3, len(dfs), figure=fig)

    # inv_winddir = {v: k for k, v in winddir_mapping.items()}
    boundaries = np.concat((np.arange(0, 382.5, 22.5), [990]))
    wind_direction_map = [
        "N",
        "NO",
        "NO",
        "O",
        "O",
        "ZO",
        "ZO",
        "Z",
        "Z",
        "ZW",
        "ZW",
        "W",
        "W",
        "NW",
        "NW",
        "N",
        "?",
    ]
    wind_directions = angles.copy(deep=True)
    for left, right, wind in zip(boundaries, boundaries[1:], wind_direction_map):
        is_this_direction = angles.between(left, right, inclusive="left")
        wind_directions[is_this_direction] = wind

    # The last index is above 360 degrees. Flip it around
    # right = np.concat([[right[-1] - 360], right[:-1]])
    # KNMI
    # winddir_mapping = {
    # 'NO': 45,
    # 'O': 90,
    # 'ZO': 135,
    # 'Z': 180,
    # 'ZW': 225,
    # 'W': 270,
    # 'NW': 315,
    # 'N': 360, == 0SA

    # Create the plots
    if axs is None:
        axs: Axes = df.plot(subplots=True, **plot_kwargs)  # , legend=False)
    ax0, ax1, ax2, ax3, ax4 = axs
    for ii, ax in enumerate(axs):
        ax.set_ylabel(df.columns[ii])
    ax0.set_title(df.index[0].date())
    # Mark every point in wind speed with its direction
    color = ax0.lines[0]._color
    for xx, yy in df["Wind speed (m/s)"].items():
        angle = angles[xx]
        m = MarkerStyle("$\\uparrow$")
        m._transform.rotate_deg(-angle)
        ax0.scatter(xx, yy, marker=m, color=color, s=200)
        ax0.text(xx, 1.1 * yy, wind_directions[xx])
    # Turn sunshine to a bar plot
    line = ax2.lines[0]
    cc = line.get_color()
    ax2.lines[0].remove()
    ax2.legend()
    ax2.bar(
        df["Sunshine (fraction of hour)"].index,
        df["Sunshine (fraction of hour)"],
        color=cc,
    )

    line = ax3.lines[0]
    cc = line.get_color()
    ax3.lines[0].remove()
    ax3.legend()
    ax3.bar(
        df["Precipitation (mm)"].index,
        df["Precipitation (mm)"],
        color=cc,
    )

    # Images from https://upload.wikimedia.org/wikipedia/commons/f/fc/Weather-symbols.png, Free to use
    if show:
        plt.show()
    if savefig:
        plt.savefig(*savefig_args, **savefig_kwargs)


def tile(file_path, dir_out, width, height, debug=1):
    """Cut an image into tiles"""
    img = Image.open(file_path)
    img1 = ImageDraw.Draw(img)
    ww, hh = img.size

    grid = product(
        range(0, hh - hh % height + 1, height), range(0, ww - ww % width + 1, width)
    )

    parts = []
    for ii, jj in grid:
        box = (jj, ii, jj + width, ii + height)
        img1.rectangle(box, outline=225)
        part = img.crop(box)
        parts.append(part)

    if debug >= 1:
        img.show()

    if debug >= 2:
        for part in parts:
            part.show()
    return parts

