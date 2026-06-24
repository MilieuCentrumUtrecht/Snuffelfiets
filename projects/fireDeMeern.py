# This project generated report-grade plots for the fire at
# de Meern from 2024-09-06. See https://www.rtvutrecht.nl/nieuws/3783761/grote-brand-op-industrieterrein-in-de-meern-brandweer-aan-het-nablussen
# and https://vru.nl/incidenten/industriebrand-strijkviertel-de-meern/
# The first reports of the fire were at 6:00. The fire was under control at
# 11:07, but the fire department was still extinguishing until
# "late in the evening"

import calendar
from datetime import datetime
from itertools import product
import io
from pathlib import Path
from PIL import Image, ImageDraw
import os

import folium
from folium.folium import Map
from knmi.metadata import variables as knmi_variables
from knmi.knmi import winddir_mapping
import matplotlib.pyplot as plt
from matplotlib.pyplot import Figure
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

from snuffelfiets.plotting import (
    scatter_mapbox,
    discrete_colorscale,
    download_borders_utrecht,
    get_borders_utrecht,
    scatter_mapbox,
    hexbin_mapbox,
    line_mapbox,
    save_fig,
    discrete_colorscale,
    download_borders_utrecht,
    get_borders_utrecht,
    load_polygons_geojson,
    select_polygons,
    get_mapbox_layers,
    secondairy_spines,
    create_humidity_plot,
    create_overview_plot,
    add_marker,
    add_title,
    tile,
    plot_hourly,
)
from snuffelfiets.inlezen import call_api, daily_csv_dump
from snuffelfiets.opschonen import correct_units
from snuffelfiets.analyse import (
    add_id,
    print_id,
    get_utrecht_center,
    get_period_info,
    haversine,
    calculate_distance_to_point,
    bewerk_timestamp,
    import_knmi_data,
    MCU_preprocessing,
)

def cut_weather_figure(file_path):
    """Try to make nice symbols for current weather"""
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


if __name__ == "__main__":
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
    period_spec = "kwartaal"  # de periode waar het rapport over gaat: 'maand', 'kwartaal' of 'jaar'?
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
    mapbox_center = get_utrecht_center()  # het middelpunt van de provincie Utrecht
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
    mapbox_layers = get_mapbox_layers(data_directory)
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
        # This will hang without the right browser and X settings!! Ctrl+C to stop
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
        # This will hang without the right browser and X settings!! Ctrl+C to stop
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
        # This will hang without the right browser and X settings!! Ctrl+C to stop
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

    fig: Figure = create_overview_plot([fire_closest_route, route_interesting])
    if "png" in output_types:
        fig.savefig(output_directory / f"overview.png")

    # See https://leaflet-extras.github.io/leaflet-providers/preview/ for tiles
    my_map: Map = folium.Map(
        location=center_fire,
        zoom_start=14,
        max_zoom=18,
        tiles="TopPlusOpen.Color",
        attribution='Map data: &copy; <a href="http://www.govdata.de/dl-de/by-2-0">dl-de/by-2-0</a>',
    )
    my_map = add_marker(my_map, center_fire[0], center_fire[1], "Fire")
    if "browser" in output_types:
        my_map.show_in_browser()

    if "png" in output_types:
        outfn = os.path.join(output_directory, "around_days_routes_alt.png")
        img_data = my_map._to_png(delay=1)
        img = Image.open(io.BytesIO(img_data))
        img.save(outfn)

    print("end")
