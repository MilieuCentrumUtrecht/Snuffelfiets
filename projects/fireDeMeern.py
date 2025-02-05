# This project generated report-grade plots for the fire at
# de Meern from 2024-09-06. See https://www.rtvutrecht.nl/nieuws/3783761/grote-brand-op-industrieterrein-in-de-meern-brandweer-aan-het-nablussen
# and https://vru.nl/incidenten/industriebrand-strijkviertel-de-meern/
# The first reports of the fire were at 6:00. The fire was under control at
# 11:07, but the fire department was still extinguishing until
# "late in the evening"

# Imports and convenience functions.

import calendar
from datetime import datetime
from itertools import product
from pathlib import Path
from PIL import Image, ImageDraw
import os

import folium
from folium.folium import Map
from knmi.metadata import variables as knmi_variables
from knmi.knmi import winddir_mapping
import matplotlib.pyplot as plt
from matplotlib.collections import PathCollection
from matplotlib.axes import Axes
from matplotlib.gridspec import GridSpec
from matplotlib.transforms import Transform
from matplotlib.markers import MarkerStyle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.graph_objects import Figure as PlotlyFigure
import selenium


# from snuffelfiets import inlezen, opschonen, analyse, plotting
from snuffelfiets.plotting import (
    scatter_mapbox,
    discrete_colorscale,
    download_borders_utrecht,
    get_borders_utrecht,
)
from snuffelfiets.inlezen import call_api
from snuffelfiets.opschonen import correct_units
from snuffelfiets.analyse import (
    haversine,
    calculate_distance_to_point,
    bewerk_timestamp,
    import_knmi_data,
)
from IPython import embed


def get_period_info(period_spec, year, quarter, month):
    """Return an id-string and the months for the chosen period."""

    quarters = {
        "Q1": [1, 2, 3],
        "Q2": [4, 5, 6],
        "Q3": [7, 8, 9],
        "Q4": [10, 11, 12],
    }
    periods = {
        "jaar": {
            "period_id": f"{year}",
            "months": list(range(1, 13)),
        },
        "kwartaal": {
            "period_id": f"{year}_{quarter}",
            "months": quarters[quarter],
        },
        "maand": {
            "period_id": f"{year}_{month:02d}",
            "months": [month],
        },
    }
    period_id = periods[period_spec]["period_id"]
    months = periods[period_spec]["months"]

    return period_id, months


def get_center():
    """Return coordinates for the center of provincie Utrecht."""

    # coordinaten van de uiterste punten van de provincie Utrecht
    b = {
        "N": [52.303634, 5.013507],
        "Z": [51.858631, 5.040462],
        "O": [51.954780, 5.627990],
        "W": [52.226808, 4.794457],
    }

    # het berekende middelpunt van de provincie Utrecht
    center = {
        "lat": b["Z"][0] + 0.5 * (b["N"][0] - b["Z"][0]),
        "lon": b["W"][1] + 0.5 * (b["O"][1] - b["W"][1]),
    }

    return center


def get_layers(data_directory):
    """Import Utrecht province and township polygons"""

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


def daily_csv_dump(
    api_key, year, month, day, data_directory=".", prefix="api_gegevens", preproc=True
):
    """Save a day of data as CSV."""

    start_datum = f"{year}-{month:02d}-{day:02d}"
    stop_datum = (
        f"{year+1}-01-01"
        if (month == 12 and day == 31)
        else f"{year}-{month:02d}-{day+1:02d}"
    )
    print(f"Getting {start_datum} till {stop_datum}")
    df = call_api(api_key, start_datum, stop_datum)
    df = opschonen.correct_units(df)

    filename = f"{prefix}_{year}-{month:02d}-{day:02d}.csv"
    p = Path(data_directory, filename)
    df.to_csv(p, index=False)

    if preproc:
        df = analyse.MCU_preprocessing(df)

        prefix = "mcu_gegevens"
        filename = f"{prefix}_{year}-{month:02d}-{day:02d}.csv"
        p = Path(data_directory, filename)
        df.to_csv(p, index=False)


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


def create_humidity_plot(main_ax, df, x_metric):
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


def add_id(df):
    # entity_id and rit_id  and _first_ _id of the route defines a unique route
    # As rit_id is generated by us and not saved in the database, we also
    # take _id in our hash
    if not df["recording_timestamp"].is_monotonic_increasing:
        raise Exception("implement")
    if "id" in df.columns:
        raise Exception(
            f"{type(df)} {hex(id(df))} already contains columns 'id', refusing to overwrite"
        )
    if len(df["rit_id"].unique()) != 1:
        raise Exception("rid_id is not unique; cannot generate id")
    if len(df["entity_id"].unique()) != 1:
        raise Exception("entity_id is not unique; cannot generate id")
    if "_id" not in df.columns:
        raise Exception("_id not in columns; cannot generate id")
    my_id = [(df["_id"].iloc[0], df["rit_id"].iloc[0], df["entity_id"].iloc[0])]
    df["my_id"] = my_id * len(df)
    return df


def print_id(df):
    if "id" not in df.columns:
        df = add_id(df)
    if len(df["my_id"].unique()) != 1:
        raise Exception("my_id is not unique; cannot print id")
    my_id = df["my_id"].iloc[0]
    return "first_id={} rit_id={} entity_id={}".format(*my_id)


def create_overview_plot(dfs, y_metric="pm2_5", x_metric="distance"):
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
    ax1.legend()


def add_marker(map, lat: float, lon: float, text: str) -> Map:
    if isinstance(map, folium.folium.Map):
        folium.RegularPolygonMarker(
            [lat, lon],
            popup=text,
            fill_color="#00ff40",
            number_of_sides=3,
            radius=10,
        ).add_to(my_map)
    else:
        map.add_trace(
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
    return map


def add_title(fig, text=None, df=None):
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


def tile(file_path, dir_out, width, height, debug=1):
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


def cut_weather_figure(file_path):
    parts = tile(weather_image_path, "", int(600 - 1 / 4), int((1000) / 6))
    # items per row from left to right from top to bottom
    grid = [
        "fair",
        "A Few Clouds",
        "Partly Cloudy",
        "Mostly Cloudy",
        "Scattered Showers",
        "Showers",
        "Scattered Thunderstorms",
        "Thunderstorms",
        "Overcast",
        "Rain",
        "Wind",
        "Hot",
        "Scattered Fog",
        "Fog",
        "Smoke",
        "Dust",
        "Cold",
        "Snow",
        "Blizzard",
        "Sleet",
        "Freezing Rain",
        "Snow / Freezing Rain",
        "Snow / Rain",
        "Rain / Sleet",
    ]

    icons = {}
    for name, part in zip(grid, parts):
        icons[name] = part
    return icons


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
        variables = ["FH", "T", "SQ", "RH", "P", "DD", "HH.1", "YYYYMMDD.1"]
    df = df[variables]
    angles = df.pop("DD")
    df["Wind speed (m/s)"] = df.pop("FH") / 10
    df["Temperature (oC)"] = df.pop("T") / 10
    df["Sunshine (hours)"] = df.pop("SQ") / 10
    df["Sunshine (fraction of hour)"] = df.pop("Sunshine (hours)") / 10
    df["Precipitation (mm)"] = df.pop("RH") / 10
    df["Pressure (bar)"] = df.pop("P") / 1e4
    df = df.drop(["HH.1", "YYYYMMDD.1"], axis="columns")
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


# weather_image_path = Path("C:/Users/karel/Downloads/kindle_weather_display_icons.png")
# cut_weather_figure(weather_image_path)
# API settings.
api_key = os.environ["CIVITY_CKAN_API_KEY"]

# File system settings.
prefix = "api_gegevens"  # de prefix voor de csv-datafiles; default format <prefix>_<yyyy>_<mm>.csv
data_directory = Path(
    Path("~").expanduser(),
    "Documents",
    "MCUdataclub",
    "Snuffelfiets_data",
    "rapportage",
)  # het pad naar de folder met de data; dit wordt ook de parent folder van de output
Path.mkdir(data_directory, parents=True, exist_ok=True)

# Date range settings.
period_spec = (
    "kwartaal"  # de periode waar het rapport over gaat: 'maand', 'kwartaal' of 'jaar'?
)
year = 2024  # het jaar waar het rapport over gaat
quarter = "Q3"  # het kwartaal waar het rapport over gaat: 'Q1', 'Q2', 'Q3', 'Q4'
month = 9  # de maand waar het rapport over gaat: 1, 2, 3, ..., 10, 11, 12
# day = 6

# Data processing settings.
error_code_selection = (
    []
)  # te verwijderen error codes; [] => behoud alleen error_code=0
rit_splitter_interval = 1800  # het interval tussen ritten (s)
ritfilters = dict(
    min_measurements=2,  # #
    max_duration=360,  # minutes
    max_distance=200,  # kilometers
    min_average_speed=1,  # km/h
    max_average_speed=35,  # km/h
)  # criteria waaraan ritten moeten voldoen
threshold_pm2_5 = 100  # de cutoff value voor geldige PM2.5 waardes

# Hexbin plot settings.
mapbox_center = get_center()  # het middelpunt van de provincie Utrecht
mapbox_extent = 1  # de breedte rondom de mapbox_center [deg lat/lon]; datapunten buiten deze breedte/lengtegraden worden verwijderd
hexagon_size = 0.010  # de grootte van de hexagons in de hexbin plot
hexbin_args = {
    "agg_func": np.nanmean,
    "color_continuous_scale": discrete_colorscale(),
    "range_color": [0, threshold_pm2_5],
    "min_count": 2,
    "animation_frame": None,
    "width": 1920,
    "height": 1080,
    "opacity": 1.0,
    "zoom": 10,
    "center": mapbox_center,
}  # parameters for creating the hexbin plot
mapbox_layers = get_layers(data_directory)
layout_args = {
    "mapbox_style": "open-street-map",
    "coloraxis_showscale": False,
    "mapbox_layers": mapbox_layers,
}  # parameters for the layout of the hexbin plot
scatter_args = {
    "color": "pm2_5",
    "hover_data": [
        "humidity",
        "pm10",
        "pm2_5",
        "pm1_0",
        "pressure",
        "temperature",
        "rit_id",
    ],
    "range_color": [0, 100],
    "color_continuous_scale": discrete_colorscale(),
    "zoom": 10,
}
# Directories.
period_id, months = get_period_info(period_spec, year, quarter, month)
period_id = period_id + "_fire_de_meern"
output_directory = Path(data_directory, period_id)
output_directory.mkdir(parents=True, exist_ok=True)

print(f"Analysing {period_spec} {period_id}; writing output to {output_directory}.")

# We need "similar days"
# We can base this on KMNI data
# First, assume days around the fire are similar to the one of the fire

fire_year = 2024  # The year of the Snbuffelfiets data
# quarter = "Q3"  # het kwartaal waar het rapport over gaat: 'Q1', 'Q2', 'Q3', 'Q4'
fire_month = 9  # The month of the Snbuffelfiets data: 1, 2, 3, ..., 10, 11, 12
fire_day = 6

# Get Snuffelfiets sensor data around the fire date
start_date = datetime(2024, 9, fire_day - 2).strftime("%Y-%m-%d")
end_date = datetime(2024, 9, fire_day + 2).strftime("%Y-%m-%d")

# df = call_api(api_key, start_date, end_date)

# df = pd.concat(dfs)
days = list(range(fire_day - 2, fire_day + 3))
dfs = []
for d in days:
    print(f"Getting day {d}")
    prefix = "mcu_gegevens"
    filename = f"{prefix}_{year}-{fire_month:02d}-{d:02d}.csv"
    p = Path(data_directory, filename)

    try:

        # try to read the data from saved csv's
        df = pd.read_csv(p)

    except FileNotFoundError:

        # download the data if the file does not exist
        # Dump daily
        daily_csv_dump(
            api_key,
            year,
            fire_month,
            d,
            data_directory=data_directory,
            prefix=prefix,
        )

        df = pd.read_csv(p)

    dfs.append(df)
dfd = pd.concat(dfs, ignore_index=True)

assert dfd.duplicated().sum() == 0
# Get KNMI weather data around the fire date

lastday = calendar.monthrange(year, months[-1])[1]
dt_min = f"{year}-{9}-{fire_day-2} 00:00:00"
dt_max = f"{year}-{9}-{fire_day+2} 23:59:59"

# +++WIND = DDVEC:FG:FHX:FHX:FX wind
# TEMP = TG:TN:TX:T10N temperatuur
# SUNR = SQ:SP:Q Zonneschijnduur en globale straling
# PRCP = DR:RH:EV24 neerslag en potentiële verdamping
# PRES = PG:PGX:PGN druk op zeeniveau
# VICL = VVN:VVX:NG zicht en bewolking
# MSTR = UG:UX:UN luchtvochtigheid
knmi_settings = {
    "interval": "hour",
    "stations": [260],
    "variables": ["ALL"],
}
dt_min_knmi = datetime(2024, 9, fire_day - 1)
dt_max_knmi = datetime(2024, 9, fire_day - 1, 23, 59)
dfr_before = import_knmi_data(
    dt_min=dt_min_knmi,
    dt_max=dt_max_knmi,
    **knmi_settings,
)  # Get weather data from Utrecht weather station

dt_min_knmi = datetime(2024, 9, fire_day)
dt_max_knmi = datetime(2024, 9, fire_day, 23, 59)
dfr_day = import_knmi_data(
    dt_min=dt_min_knmi,
    dt_max=dt_max_knmi,
    **knmi_settings,
)  # Get weather data from Utrecht weather station

dt_min_knmi = datetime(2024, 9, fire_day + 1)
dt_max_knmi = datetime(2024, 9, fire_day + 1, 23, 59)
dfr_after = import_knmi_data(
    dt_min=dt_min_knmi,
    dt_max=dt_max_knmi,
    **knmi_settings,
)  # Get weather data from Utrecht weather station

plot_hourly(
    dfr_before,
    savefig=True,
    savefig_args=[output_directory / "knmi_weather_before.png"],
    savefig_kwargs={},
)
plot_hourly(
    dfr_day,
    savefig=True,
    savefig_args=[output_directory / "knmi_weather_day.png"],
    savefig_kwargs={},
)
plot_hourly(
    dfr_after,
    savefig=True,
    savefig_args=[output_directory / "knmi_weather_after.png"],
    savefig_kwargs={},
)
# We determined the location of the fire from vru.nl and found these coordinates on Google Maps: 52°04'39.6"N 5°03'27.9"E
# 52.077522511336845, 5.057254362375853
center_fire = (52.077522511336845, 5.057254362375853)  # (N, E)
b = {
    "N": [52.303634, 5.013507],
    "Z": [51.858631, 5.040462],
    "O": [51.954780, 5.627990],
    "W": [52.226808, 4.794457],
}

# distance2 = calculate_distance_to_point(
#    dfd["latitude"].iloc[0],
#    dfd["longitude"].iloc[0],
#    point={"lat": center_fire[0], "lon": center_fire[1]},
# )
dfd["distance"] = dfd[["latitude", "longitude"]].apply(
    lambda row: calculate_distance_to_point(
        row[0], row[1], point={"lat": center_fire[0], "lon": center_fire[1]}
    )
    / 1000,
    axis="columns",
)  # km

dfd = bewerk_timestamp(dfd)
dfd["distance_rit_mean"] = dfd.groupby("rit_id")["distance"].transform("mean")

# 1 - 80 km from fire
fire_date_filter = (
    dfd["date_time"] < datetime(fire_year, fire_month, fire_day + 1)
) & (dfd["date_time"] > datetime(fire_year, fire_month, fire_day))

day_after_filter = (
    dfd["date_time"] < datetime(fire_year, fire_month, fire_day + 2)
) & (dfd["date_time"] > datetime(fire_year, fire_month, fire_day + 1))

dff = dfd[fire_date_filter]
dfn = dfd[~fire_date_filter]
dfd = dfd[day_after_filter]
# plt.scatter(dfd[fire_date_filter]["distance"], dfd[fire_date_filter]["pm2_5"])
# plt.scatter(dfd[~fire_date_filter]["distance"], dfd[~fire_date_filter]["pm2_5"], c="k")
# fire_closest_route = dff[dff["distance_rit_mean"] == dff["distance_rit_mean"].min()]
fire_closest_route = dff[dff["rit_id"] == 12]
route_interesting = dff[dff["rit_id"] == 46]

# browser, png, html
output_types = ["browser", "png"]
output_types = ["png"]

fig: PlotlyFigure = scatter_mapbox(
    fire_closest_route,
    plot_args=scatter_args,
)
fig = add_title(fig, df=fire_closest_route)
add_marker(fig, center_fire[0], center_fire[1], "Fire")
if "browser" in output_types:
    fig.show()
if "png" in output_types:
    fig.write_image(output_directory / "fire_michiel_route.png")

fig: PlotlyFigure = scatter_mapbox(
    dfd,
    plot_args=scatter_args,
)
fig = add_title(fig, df=dfd)
add_marker(fig, center_fire[0], center_fire[1], "Fire")
if "browser" in output_types:
    fig.show()
if "png" in output_types:
    fig.write_image(output_directory / f"day_after_routes.png")

fig: PlotlyFigure = scatter_mapbox(
    dff,
    plot_args=scatter_args,
)
fig = add_title(fig, df=dff)
add_marker(fig, center_fire[0], center_fire[1], "Fire")
if "browser" in output_types:
    fig.show()
if "png" in output_types:
    fig.write_image(output_directory / f"fire_day_routes.png")

fig: PlotlyFigure = scatter_mapbox(
    dfn,
    plot_args=scatter_args,
)
fig = add_title(fig, df=dfn)
add_marker(fig, center_fire[0], center_fire[1], "Fire")

if "browser" in output_types:
    fig.show()
if "png" in output_types:
    fig.write_image(output_directory / f"around_days_routes.png")
y_metric = "pm2_5"

create_overview_plot([fire_closest_route, route_interesting])


my_map: Map = folium.Map(location=center_fire, zoom_start=13)
my_map = add_marker(my_map, center_fire[0], center_fire[1], "Fire")
if "browser" in output_types:
    my_map.show_in_browser()

if "png" in output_types:
    import os
    import subprocess

    my_map.save("tmp.html")
    url = "file://{}/tmp.html".format(os.getcwd())
    outfn = os.path.join(output_directory, "around_days_routes2.png")
    try:
        binary = "cutycapt"
        returned = subprocess.run(
            [binary, "--url={}".format(url), "--out={}".format(outfn)],
            shell=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, OSError, ValueError) as e:
        embed()
    else:
        assert isinstance(returned, subprocess.CompletedProcess)
        returned.args
        returned.stdout
        returned.stderr
        if returned.returncode != 0:
            assert returned.stdout == b""
            raise Exception(f"{binary} could not be found")
            # raise CompletedProcess(
            # BaseException, returncode=returned.returncode
            # )

    Path("tmp.html").unlink()

print("end")
