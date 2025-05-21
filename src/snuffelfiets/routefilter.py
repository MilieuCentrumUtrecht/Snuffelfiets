# Imports
import pandas as pd
import numpy as np
import warnings
from os import listdir
from os.path import isfile, join
from pathlib import Path
from datetime import datetime

def filter_routes(main_directory=None, years=None, months=None, distance=10, prefix="mcu_gegevens", isExtend=True):
    """ Short description

    Long description
    Multiple lines can be used

    Args:
        None

    Kwargs:
        main_directory: Folder
        years: Description
        months: Description
        distance: Description
        prefix: Description
        isExtend: Description

    Returns:
        dfO_list: Description of output
        dfR: Description of output

    """
    # Directories for data, route and output files
    if not main_directory:
        main_directory = Path(Path('~').expanduser(), 'Documents', 'MCUdataclub', 'RouteFilter')

    if not years:
        years = [2024]

    if not months:
        months = [9]
    data_directory = Path(main_directory, 'Input_Data')
    routes_directory = Path(main_directory, 'Input_Routes')
    output_directory = Path(main_directory, 'Output')

    for path in [data_directory, routes_directory, output_directory]:
        Path.mkdir(path, parents=True, exist_ok=True)
    print(f'writing output to {output_directory}\n')

    # Import route(s) filenames
    routes = [f for f in listdir(routes_directory) if isfile(join(routes_directory, f))]

    # Parameters
    latMeter = 0.0000089988659514815        # 1 meter expressed in latitude (works for area province Utrecht)
    lonMeter = 0.0000146436902975532        # 1 meter expressed in longitude (works for area province Utrecht)
    latMin = 0 #51.858631                   # smallest latitude province Utrecht
    lonMin = 0 #4.794457                    # smallest longitude province Utrecht
    timestamp = str(int(datetime.timestamp(datetime.now())))

    # Lists for dataframes
    df_list = []                            # List for csv imports
    dfR_list = []                           # List for dfR (routes)
    dfS_list = []                           # List for dfS (measurements per segment)
    dfO_list = []                           # List for dfO (output dataframes per route)

    # Ignore expected error
    warnings.filterwarnings("ignore", message='invalid value encountered in arc')

    # Import routes as list of dataframes
    if len(routes) == 0:
        raise Exception("No routes given! Abort")
    for filename in routes:

        p = Path(routes_directory, filename)

        try:
            #TODO only import csv with correct columns and not empty
            dfR = pd.read_csv(p)
            print(f'[{filename}] {dfR["latitude"].shape[0]} route points read')
            dfR.drop_duplicates(subset=['latitude', 'longitude'], inplace=True)
            print(f'[{filename}] {dfR.shape[0]} unique route points remaining\n')
            dfR.reset_index(inplace=True)
            dfR_list.append(dfR)

        except:
            print(f'{filename} not valid for processing.\nMissing latitude and/or longitude columns (probably).\n')
            routes.remove(filename)
            continue

    # Import data files for choosen range from data_directory
    for year in years:
        for month in months:
            filename = f'{prefix}_{year}-{month:02d}.csv'
            p = Path(data_directory, filename)
            try:
                df = pd.read_csv(p)
                df_list.append(df)
            except:
                print(f'[datafile] "{filename}" not found in {data_directory}\n')
    try:
        df = pd.concat(df_list, ignore_index=True)
    except:
        print('\nThere is no dataframe df. \nNo data has been imported. \nExecution will crash now!')

    # add columns yLat and xLon to df
    df['yLat'] = (df['latitude'] - latMin) / latMeter
    df['xLon'] = (df['longitude'] - lonMin) / lonMeter

    # add column unique_rit_id
    df['unique_rit_id'] = df['rit_id'] + df['year'] * 1000000 + df['month'] * 10000

    # TODO: drop unnecessary columns?
    # df = df.drop(columns=['column_nameA', 'column_nameB'])

    print(f'{df.shape[0]} measurements imported...')

    # use route points to filter df to max/min lat/lon
    maxLat = 0
    minLat = 999
    maxLon = 0
    minLon = 999

    for dfR in dfR_list:
        maxLatRoute = max(dfR['latitude'])
        minLatRoute = min(dfR['latitude'])
        maxLonRoute = max(dfR['longitude'])
        minLonRoute = min(dfR['longitude'])
        maxLat = max(maxLatRoute, maxLat) + (distance * latMeter)
        minLat = min(minLatRoute, minLat) - (distance * latMeter)
        maxLon = max(maxLonRoute, maxLon) + (distance * lonMeter)
        minLon = min(minLonRoute, minLon) - (distance * lonMeter)

    df = df[df['latitude'].between(minLat, maxLat )]
    df = df[df['longitude'].between(minLon, maxLon)]

    print(f'{df.shape[0]} filtered measurements remaining\n')

    # LOOP THROUGH ROUTES
    for idx, dfR in enumerate(dfR_list):

        # Reset dfS_list and routeSegment for this route
        dfS_list = []
        df['routeSegment'] = 0

        # Add columns to dfR and transform dfR into segments per row
        dfR['longitude2'] = dfR['longitude'].shift(-1)
        dfR['latitude2'] = dfR['latitude'].shift(-1)
        dfR.drop(dfR.tail(1).index, inplace=True)
        dfR['xB'] = (dfR['longitude'] - lonMin) / lonMeter
        dfR['yB'] = (dfR['latitude'] - latMin) / latMeter
        dfR['xE'] = (dfR['longitude2'] - lonMin) / lonMeter
        dfR['yE'] = (dfR['latitude2'] - latMin) / latMeter
        print(f'created {dfR.shape[0]} segments from {routes[idx]}...')

        # Calculate segment length
        dfR['BE'] = np.sqrt( 
            np.square(dfR['xE'] - dfR['xB']) 
            + np.square(dfR['yE'] - dfR['yB']) )
        dfR['distBegin'] = dfR['BE'].cumsum().shift(1).fillna(0)

        # Extend segment from end point E with set distance
        # TODO: don't extend last segment somehow
        if isExtend: 
            dfR['xE'] = (dfR['xE'] - dfR['xB']) * (distance / dfR['BE']) + dfR['xE'] 
            dfR['yE'] = (dfR['yE'] - dfR['yB']) * (distance / dfR['BE']) + dfR['yE'] 
            dfR['BE'] = np.sqrt( 
                np.square(dfR['xE'] - dfR['xB']) 
                + np.square(dfR['yE'] - dfR['yB']) )

        # LOOP THROUGH SEGMENTS OF ROUTE
        for index, segment in dfR.iterrows():

            # Calculate sides MB, ME using Pythagorean theorem
            df['MB'] = np.sqrt( 
                np.square(df['xLon'] - segment['xB']) 
                + np.square(df['yLat'] - segment['yB']) ) 
            df['ME'] = np.sqrt( 
                np.square(df['xLon'] - segment['xE']) 
                + np.square(df['yLat'] - segment['yE']) ) 

            # Calculate angles aBE, aMB, aME using Law of cosines (aBE is currently redundant)
            df['aMB'] = np.acos( 
                ( np.square(df['ME']) + np.square(segment['BE']) - np.square(df['MB']) ) 
                / (2 * segment['BE'] * df['ME']) ) 
            df['aME'] = np.acos( 
                ( np.square(df['MB']) + np.square(segment['BE']) - np.square(df['ME']) ) 
                / (2 * segment['BE'] * df['MB']) ) 
            #df['aBE'] = np.acos( 
                #( np.square(df['MB']) + np.square(df['ME']) - np.square(segment['BE']) ) 
                #/ (2 * df['MB'] * df['ME']) ) 

            # Calculate distances
            df['M-BE'] = np.sin(df['aME']) * df['MB']                       # distance from measurement perpendicular to route segment line BE
            df['distSegment'] = np.cos(df['aME']) * df['MB']                # distance measurement along segment
            df['distRoute'] = df['distSegment'] + segment['distBegin']      # distance measurement along total route

            # Filter and add routeSegment number
            df.loc[
                (df['M-BE'].between(0, distance)) 
                & (df['aMB'].between(0, np.pi/2)) 
                & (df['aME'].between(0, np.pi/2)) 
                & (df['routeSegment'] == 0)
                , ['routeSegment']] = index + 1

            # Save filtered measurements
            dfS = df[df['routeSegment'] == index + 1]
            #dfS['test2'] = 0 #why does this give a copywarning?
            dfS_list.append(dfS)                                        # Append dfS to dfS_List

        # Concat all dfS of route into dfO in dfO_list
        dfO_list.append(pd.concat(dfS_list, ignore_index=True))

        # export dfO
        filename2 = timestamp + '-dfOutput-' + routes[idx]
        p = Path(output_directory, filename2)
        dfO_list[idx].to_csv(p, index=False)
        print(f'...exported {dfO_list[idx].shape[0]} filtered measurements to {filename2}\n')

        # export dfR for testing
        filename2 = timestamp + '-dfRoute-' + routes[idx]
        p = Path(output_directory, filename2)
        dfR.to_csv(p, index=False)

        # export df for testing
        #filename2 = timestamp  + '-df-' + routes[idx]
        #p = Path(output_directory, filename2)
        #df.to_csv(p, index=False)

        return dfO_list, dfR

    warnings.resetwarnings()

if __name__ == "__main__":
    dfO_list, dfR = filter_routes()
