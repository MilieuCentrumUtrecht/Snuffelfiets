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

from . import opschonen, analyse


def is_date_matching(date_str):
    """Perform date format check."""

    try:
        if len(date_str) == 10:
            return bool(datetime.strptime(date_str, "%Y-%m-%d"))
        else:
            return False
    except ValueError:
        return False


def _get_chunk(url, headers, params):
    """Get a single chunk of (limit=32000) observations."""

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        msg = f"api-call mislukt:"
        msg += f" foutcode: {response.status_code};"
        msg += f" {response.text}\n"
        exit()
    jfile = json.loads(response.text)
    records = jfile["result"]["records"]

    return records


def get_records(url, headers, params, limit=32000, offset=0):
    """Get all records for a query."""

    sql_base = f'{params["sql"]}'
    records = []
    truncated = True
    i = 1

    while truncated:
        params["sql"] = f"{sql_base} OFFSET {offset}"
        chunk = _get_chunk(url, headers, params)
        truncated = len(chunk) == limit
        records += chunk
        offset += limit
        msg = f"Read chunk {i:02d}"
        msg += f' up to timestamp {chunk[-1]["recording_timestamp"]}'
        print(msg)
        i += 1

    return records


def build_sql_statement(
    columns="*",
    datastore="provincie_utrecht_snuffelfiets_measurement_rydruofi",
    conditions=[],
    parameters={},
):

    sql = ""
    sql += f'SELECT {columns} FROM "{datastore}"'

    sql += f" WHERE"
    for condition in conditions:
        sql += f' "{condition["col"]}" {condition["op"]} \'{condition["val"]}\''
        sql += f" AND"
    sql = sql[:-4]

    for k, v in parameters.items():
        sql += f" {k.upper()} {v}"

    return sql


def call_api(
    api_key,
    start_datum,
    stop_datum,
    columns="*",
    url="https://ckan-dataplatform-nl.dataplatform.nl/api/3/action/datastore_search_sql",
    datastore="provincie_utrecht_snuffelfiets_measurement_rydruofi",
    resource_id="4cfb5177-d3db-4efc-ac6f-351af75f9f92",
    sql_conditions=[],
    sql_parameters={"limit": 32000},  # CKAN limit is 32000 records  , 'offset': 0
):
    """Doe een query op de database."""

    for k, datum in {"Start": start_datum, "Stop": stop_datum}.items():
        if not is_date_matching(datum):
            msg = f"\n{k}datum {datum} is niet de juiste datumnotatie."
            msg += f" (jjjj-mm-dd). Programma wordt afgebroken.\n"
            exit(msg)

    sql_conditions_dates = [
        {"col": "recording_timestamp", "op": ">", "val": start_datum},
        {"col": "recording_timestamp", "op": "<", "val": stop_datum},
    ]
    sql_conditions_all = sql_conditions + sql_conditions_dates

    sql_args = {
        "columns": columns,
        "datastore": datastore,
        "conditions": sql_conditions_all,
        "parameters": sql_parameters,
    }
    headers = {"X-CKAN-API-Key": api_key}
    params = {"resource_id": resource_id, "sql": build_sql_statement(**sql_args)}
    print(f'sql statement: {params["sql"]}')

    start_time = time.time()

    records = get_records(url, headers, params, sql_parameters["limit"])

    df = pd.DataFrame(records)
    df = drop_columns(df)
    df = convert_to_int(df)

    print(f"Read {df.shape[0]} measurements in {time.time() - start_time} s.")
    print(f"\n")

    return df


def drop_columns(df, columns=["_full_text"]):
    """Drop superfluous columns.

    '_full_text' is een column, waar alle gegevens nog
    enn keer instaan als een lange string ('gescheiden)
    """

    df = df.drop(columns, axis=1)

    print(f"Dropped {columns} columns.")

    return df


def convert_to_int(
    df, columns=["entity_id", "version_major", "version_minor", "error_code"]
):
    """Convert the object datatype to int64."""

    for col in columns:
        df[col] = df[col].astype("int64")

    print(f"Converted {columns} columns to int64.")

    return df


def monthly_csv_dump(
    api_key, year, month, data_directory=".", prefix="api_gegevens", preproc=True
):
    """Save a month of data as CSV."""

    start_datum = f"{year}-{month:02d}-01"
    stop_datum = f"{year+1}-01-01" if month == 12 else f"{year}-{month+1:02d}-01"

    df = call_api(api_key, start_datum, stop_datum)
    df = opschonen.correct_units(df)

    filename = f"{prefix}_{year}-{month:02d}.csv"
    p = Path(data_directory, filename)
    df.to_csv(p, index=False)

    if preproc:
        df = analyse.MCU_preprocessing(df)

        prefix = "mcu_gegevens"
        filename = f"{prefix}_{year}-{month:02d}.csv"
        p = Path(data_directory, filename)
        df.to_csv(p, index=False)


if __name__ == "__main__":
    duur = call_api()
    print(f"\nProgramma is afgelopen. Benodigde tijd was: {duur}.\n")
