#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het inlezen van Snuffelfiets data.

"""

import requests
import json
import pandas as pd
import time
from sys import argv, exit
from datetime import datetime
from pathlib import Path

from . import opschonen

# https://stackoverflow.com/questions/69845270/use-pandas-style-using-comma-as-decimal-separator


def is_date_matching(date_str):
    """Perform date format check."""

    try:
        if len(date_str) == 10:
            return bool(datetime.strptime(date_str, '%Y-%m-%d'))
        else:
            return False
    except ValueError:
        return False


def call_api(
        api_key,
        start_datum,
        stop_datum,
        columns='*',
        url='https://ckan-dataplatform-nl.dataplatform.nl/api/3/action/datastore_search_sql',
        ):
    """Doe een query op de database."""

    if not is_date_matching(start_datum):
        exit(f'\nStartdatum {start_datum} is niet de juiste datumnotatie (jjjj-mm-dd). Programma wordt afgebroken.\n')

    if not is_date_matching(stop_datum):
        exit(f'\nStopdatum {stop_datum} is niet de juiste datumnotatie (jjjj-mm-dd). Programma wordt afgebroken.\n')

    headers = {'X-CKAN-API-Key': api_key}

    params = {
        'resource_id': '4cfb5177-d3db-4efc-ac6f-351af75f9f92',
        'sql': f'SELECT {columns} from "provincie_utrecht_snuffelfiets_measurement_rydruofi"'\
                + f' WHERE "recording_timestamp" > \'{start_datum}\' AND "recording_timestamp" < \'{stop_datum}\'',
        'offset': 0,
        'limit': 9999999,
    }

    print(f'url= {url}')
    print(f'sql-statement= {params["sql"]}')

    start_time = time.time()
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        exit(f'api-call mislukt: foutcode= {response.status_code}; {response.text}\n')

    jfile = json.loads(response.text)
    df = pd.DataFrame(jfile['result']['records'])

    df = drop_columns(df)
    df = convert_to_int(df)

    print(f'Read {df.shape[0]} measurements in {time.time() - start_time} s.')
    print(f'\n')

    return df


def drop_columns(df, columns=['_full_text']):
    """Drop superfluous columns.
    
    '_full_text' is een column, waar alle gegevens nog
    enn keer instaan als een lange string ('gescheiden)
    """

    df = df.drop(columns, axis=1)

    print(f'Dropped {columns} columns.')

    return df


def convert_to_int(df, columns=['entity_id', 'version_major', 'version_minor', 'error_code']):
    """Convert the object datatype to int64."""
    
    for col in columns:
        df[col]= df[col].astype('int64')

    print(f'Converted {columns} columns to int64.')

    return df


def monthly_csv_dump(api_key, year, month, data_directory='.', prefix='api_gegevens'):
    """Save a month of data as CSV."""

    start_datum = f'{year}-{month:02d}-01'
    stop_datum = f'{year+1}-01-01' if month==12 else f'{year}-{month+1:02d}-01'

    df = call_api(api_key, start_datum, stop_datum)
    df = opschonen.correct_units(df)

    filename = f'{prefix}_{year}-{month:02d}.csv'
    p = Path(data_directory, filename)
    df.to_csv(p, index=False)


if __name__ == '__main__':
    duur = call_api()
    print(f'\nProgramma is afgelopen. Benodigde tijd was: {duur}.\n')
