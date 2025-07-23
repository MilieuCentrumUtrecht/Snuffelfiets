# Imports
import pandas as pd
import numpy as np
import warnings
from os import listdir
from os.path import isfile, join
from pathlib import Path
from datetime import datetime

from src.snuffelfiets.analyse import verdeel_in_ritten, bewerk_timestamp

latMeter = 0.0000089988659514815  # 1 meter expressed in latitude (works for area province Utrecht)
lonMeter = 0.0000146436902975532  # 1 meter expressed in longitude (works for area province Utrecht)
latMin = 0  # 51.858631                   # smallest latitude province Utrecht
lonMin = 0  # 4.794457                    # smallest longitude province Utrecht
main_directory_default = Path(
    Path("~").expanduser(), "Documents", "MCUdataclub", "RouteFilter"
)
data_directory_default = Path(main_directory_default, "Input_Data")
input_directory_default = Path(main_directory_default, "Input_Data")
routes_directory_default = Path(main_directory_default, "Input_Routes")
output_directory_default = Path(main_directory_default, "Output")


def read_data(
    data_directory=data_directory_default,
    years=None,
    months=None,
    prefix="mcu_gegevens",
):
    if not years:
        years = [2024]

    if not months:
        months = [9]

    if not data_directory.exists():
        Path.mkdir(data_directory, parents=True, exist_ok=True)

    # Import data files for choosen range from data_directory
    df_list = []
    for year in years:
        for month in months:
            filename = f"{prefix}_{year}-{month:02d}.csv"
            p = Path(data_directory, filename)
            try:
                df = pd.read_csv(p)
                df_list.append(df)
            except:
                print(f'[datafile] "{filename}" not found in {data_directory}\n')
    try:
        df = pd.concat(df_list, ignore_index=True)
    except:
        raise RuntimeError(
            "\nThere is no dataframe df. \nNo data has been imported. \nExecution will crash now!"
        )

    if "rid_id" not in df.columns:
        df = verdeel_in_ritten(df)
    if any(col not in df.columns for col in ["year", "month"]):
        df = bewerk_timestamp(df, split=True)
    # add columns yLat and xLon to df
    df["yLat"] = (df["latitude"] - latMin) / latMeter
    df["xLon"] = (df["longitude"] - lonMin) / lonMeter

    # add column unique_rit_id
    df["unique_rit_id"] = df["rit_id"] + df["year"] * 1000000 + df["month"] * 10000

    # TODO: drop unnecessary columns?
    # df = df.drop(columns=['column_nameA', 'column_nameB'])

    print(f"{df.shape[0]} measurements imported...")
    return df


def read_routes(
    routes_directory=routes_directory_default,
    years=None,
    months=None,
    prefix="mcu_gegevens",
    isExtend=True,
):
    """Function to filter Snuffelfiets measurements within a chosen distance of a route.

    Function uses route csv file(s) to filter data from Snuffelfietsdata csv file(s).
    Function outputs filtered data per route.

    Args:
        None

    Kwargs:
        main_directory: Folder which has subfolders "Input_Data" and "Input_Routes"
        years: List of years to include from Snuffelfiets data.
        months: List of months to include from Snuffelfiets data.
        distance: Max distance (m) from imported route of measurements to include from Snuffelfiets data.
        prefix: We use either "mcu_gegevens" (cleaned data) or "api_gegevens" (raw data).
        isExtend: Extend route segment from end point E with set distance to avoid dropping points

    Returns:
        dfO_list: List of dataframes with filtered measurements from Snuffelfiets data per route.
        dfR_list: List of route points per route.

    """
    if not routes_directory.exists():
        Path.mkdir(routes_directory, parents=True, exist_ok=True)

    # Import route(s) filenames
    routes = [f for f in listdir(routes_directory) if isfile(join(routes_directory, f))]
    routesInvalid = []

    # Import routes as list of dataframes
    if len(routes) == 0:
        raise Exception("No routes given! Abort")

    dfR_list = []  # List for dfR (routes)
    print(f"Start reading {routes}")
    for filename in routes:

        p = Path(routes_directory, filename)

        try:
            # TODO only import csv with correct columns and not empty
            dfR = pd.read_csv(p)
            print(f'[{filename}] {dfR["latitude"].shape[0]} route points read')
            dfR.drop_duplicates(subset=["latitude", "longitude"], inplace=True)
            print(f"[{filename}] {dfR.shape[0]} unique route points remaining\n")
            dfR.reset_index(inplace=True)
            dfR_list.append(dfR)
        except:
            print(
                f"{filename} not valid for processing.\nMissing latitude and/or longitude columns (probably).\n"
            )
            routesInvalid.append(filename)
            continue
    routes = [x for x in routes if x not in routesInvalid]
    print(f"Read {len(dfR_list)} valid routes")
    return dfR_list, routes


def filter_routes(
    dfR_list,
    routes,
    df,
    output_directory=output_directory_default,
    distance=10,
    isExtend=True,
):
    if not output_directory.exists():
        Path.mkdir(output_directory, parents=True, exist_ok=True)

    # Parameters
    timestamp = str(int(datetime.timestamp(datetime.now())))

    # Lists for dataframes
    df_list = []  # List for csv imports
    dfS_list = []  # List for dfS (measurements per segment)
    dfO_list = []  # List for dfO (output dataframes per route)

    # Ignore expected error
    warnings.filterwarnings("ignore", message="invalid value encountered in arc")

    # use route points to filter df to max/min lat/lon
    maxLat = 0
    minLat = 999
    maxLon = 0
    minLon = 999

    for dfR in dfR_list:
        maxLatRoute = max(dfR["latitude"])
        minLatRoute = min(dfR["latitude"])
        maxLonRoute = max(dfR["longitude"])
        minLonRoute = min(dfR["longitude"])
        maxLat = max(maxLatRoute, maxLat) + (distance * latMeter)
        minLat = min(minLatRoute, minLat) - (distance * latMeter)
        maxLon = max(maxLonRoute, maxLon) + (distance * lonMeter)
        minLon = min(minLonRoute, minLon) - (distance * lonMeter)

    df = df[df["latitude"].between(minLat, maxLat)]
    df = df[df["longitude"].between(minLon, maxLon)]

    print(f"{df.shape[0]} filtered measurements remaining\n")
    print(f"writing output to {output_directory}\n")

    # LOOP THROUGH ROUTES
    for idx, dfR in enumerate(dfR_list):

        # Reset dfS_list and routeSegment for this route
        dfS_list = []
        df["routeSegment"] = 0

        # Add columns to dfR and transform dfR into segments per row
        dfR["longitude2"] = dfR["longitude"].shift(-1)
        dfR["latitude2"] = dfR["latitude"].shift(-1)
        dfR.drop(dfR.tail(1).index, inplace=True)
        dfR["xB"] = (dfR["longitude"] - lonMin) / lonMeter
        dfR["yB"] = (dfR["latitude"] - latMin) / latMeter
        dfR["xE"] = (dfR["longitude2"] - lonMin) / lonMeter
        dfR["yE"] = (dfR["latitude2"] - latMin) / latMeter
        print(f"created {dfR.shape[0]} segments from {routes[idx]}...")

        # Calculate segment length
        dfR["BE"] = np.sqrt(
            np.square(dfR["xE"] - dfR["xB"]) + np.square(dfR["yE"] - dfR["yB"])
        )
        dfR["distBegin"] = dfR["BE"].cumsum().shift(1).fillna(0)

        # Extend segment from end point E with set distance
        # TODO: don't extend last segment somehow
        if isExtend:
            dfR["xE"] = (dfR["xE"] - dfR["xB"]) * (distance / dfR["BE"]) + dfR["xE"]
            dfR["yE"] = (dfR["yE"] - dfR["yB"]) * (distance / dfR["BE"]) + dfR["yE"]
            dfR["BE"] = np.sqrt(
                np.square(dfR["xE"] - dfR["xB"]) + np.square(dfR["yE"] - dfR["yB"])
            )

        # LOOP THROUGH SEGMENTS OF ROUTE
        for index, segment in dfR.iterrows():

            # Calculate sides MB, ME using Pythagorean theorem
            df["MB"] = np.sqrt(
                np.square(df["xLon"] - segment["xB"])
                + np.square(df["yLat"] - segment["yB"])
            )
            df["ME"] = np.sqrt(
                np.square(df["xLon"] - segment["xE"])
                + np.square(df["yLat"] - segment["yE"])
            )

            # Calculate angles aBE, aMB, aME using Law of cosines (aBE is currently redundant)
            df["aMB"] = np.acos(
                (np.square(df["ME"]) + np.square(segment["BE"]) - np.square(df["MB"]))
                / (2 * segment["BE"] * df["ME"])
            )
            df["aME"] = np.acos(
                (np.square(df["MB"]) + np.square(segment["BE"]) - np.square(df["ME"]))
                / (2 * segment["BE"] * df["MB"])
            )
            # df['aBE'] = np.acos(
            # ( np.square(df['MB']) + np.square(df['ME']) - np.square(segment['BE']) )
            # / (2 * df['MB'] * df['ME']) )

            # Calculate distances
            df["M-BE"] = (
                np.sin(df["aME"]) * df["MB"]
            )  # distance from measurement perpendicular to route segment line BE
            df["distSegment"] = (
                np.cos(df["aME"]) * df["MB"]
            )  # distance measurement along segment
            df["distRoute"] = (
                df["distSegment"] + segment["distBegin"]
            )  # distance measurement along total route

            # Filter and add routeSegment number
            df.loc[
                (df["M-BE"].between(0, distance))
                & (df["aMB"].between(0, np.pi / 2))
                & (df["aME"].between(0, np.pi / 2))
                & (df["routeSegment"] == 0),
                ["routeSegment"],
            ] = (
                index + 1
            )

            # Save filtered measurements
            dfS = df[df["routeSegment"] == index + 1]
            # dfS['test2'] = 0 #why does this give a copywarning?
            dfS_list.append(dfS)  # Append dfS to dfS_List

        # Concat all dfS of route into dfO in dfO_list
        dfO_list.append(pd.concat(dfS_list, ignore_index=True))

        output_filtered(
            idx, dfO_list, dfR, timestamp, routes, output_directory=output_directory
        )


def output_filtered(idx, dfO_list, dfR, timestamp, routes, output_directory=None):
    # export dfO
    filename2 = timestamp + "-dfOutput-" + routes[idx]
    p = Path(output_directory, filename2)
    dfO_list[idx].to_csv(p, index=False)
    print(
        f"...exported {dfO_list[idx].shape[0]} filtered measurements to {filename2}\n"
    )

    # export dfR for testing
    filename2 = timestamp + "-dfRoute-" + routes[idx]
    p = Path(output_directory, filename2)
    dfR.to_csv(p, index=False)

    # export df for testing
    # filename2 = timestamp  + '-df-' + routes[idx]
    # p = Path(output_directory, filename2)
    # df.to_csv(p, index=False)
