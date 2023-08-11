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

    print(f'\nurl= {url}')
    print(f'\nsql-statement= {params["sql"]}')

    # begin kernprogramma
    start_time = time.time()
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        exit(f'\napi-call mislukt: foutcode= {response.status_code}; {response.text}\n')

    jfile = json.loads(response.text)
    df = pd.DataFrame(jfile['result']['records'])

    # '_full_text' is een column, waar alle gegevens nog 'n keer instaan als een lange string ('gescheiden)
    df = df.drop('_full_text', axis=1)  

    print(f'Data gelezen in: {time.time() - start_time} s.')

    return df


if __name__ == '__main__':
    duur = call_api()
    print(f'\nProgramma is afgelopen. Benodigde tijd was: {duur}.\n')
