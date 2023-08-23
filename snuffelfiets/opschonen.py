#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het opschonen van Snuffelfiets data.

"""

import numpy as np


# sommige data moet worden aangepast:
# https://ckan-dataplatform-nl.dataplatform.nl/dataset/
#       near-real-time-onbewerkte-snuffelfiets-gegevens-provincie-utrecht

CORRECTIE_DEFAULTS = {
    'temperature': {
        'factor': 0.10,
        },
    'pressure': {
        'factor': 100.,
        },
    'voltage': {
        'factor': 0.10,
        'offset': 3,
        },
    'pm1_0': {
        'factor': 0.01,
        'conditie': {
            'col': 'version_major',
            'fun': np.greater_equal,
            'val': 2,
            },
        },
    'pm2_5': {
        'factor': 0.01,
        'conditie': {
            'col': 'version_major',
            'fun': np.greater_equal,
            'val': 2,
            },
        },
    'pm10' : {
        'factor': 0.01,
        'conditie': {
            'col': 'version_major',
            'fun': np.greater_equal,
            'val': 2,
            },
        },
}


def correct_units(df, correcties=CORRECTIE_DEFAULTS):
    """Converteer de ruwe data naar correcte units."""

    for col, correctie in correcties.items():

        # doe niets als item niet gespecificeerd
        default = {'factor': 1.0, 'offset': 0, 'conditie': None}
        corr = {**default, **correctie}

        mask = _get_mask(df, col, corr)

        df[col] = np.where(mask, corr['offset'] + df[col] * corr['factor'], df[col])

    return df


def _get_mask(df, col, corr):
    """Maak een conditie masker.
     
    om te kiezen tussen geconverteerde en originele data.
    """

    mask = np.zeros_like(df[col], dtype='bool')

    if corr['conditie'] is not None:

        fun_conditie = corr['conditie']['fun']
        col_conditie = corr['conditie']['col']
        val_conditie = corr['conditie']['val']

        mask = fun_conditie(df[col_conditie], val_conditie)

    return mask


def verwijder_errors(df, error_codes=[]):
    """Verwijder metingen met specifieke error codes.

    https://ckan.dataplatform.nl/dataset/snuffelfiets-extra-informatie-snifferbike-additional-info
    ------------------------------------------------------------------
    Name                                        number  Note
    ------------------------------------------------------------------
    ACCELEROMETER ERROR 1: Sensor Not Found     1       Critical Error
    Reserved                                    2
    BME ERROR 1: Sensor Not Found               4       Critical Error
    BME ERROR 2: Failed to begin reading        8       Critical Error
    GPS ERROR 1: Sensor Not Found               16      Critical Error
    GPS ERROR 2: No GPS Fix                     32      "Allowed Error, device maybe indoors"
    Reserved                                    64      
    NO2 ERROR 1: Sensor Not Found               128     "Should never be seen, NO2 removed in software."
    Reserved                                    256     
    PM ERROR 1: Sensor Not Found                512     Critical Error
    PM ERROR 2a: Measurement Start Failure      1024    Critical Error
    PM ERROR 2b: Measurement Read Failure       2048    "Allowed Error, PM sensors not ready. Wait 5 more measurements."
    PM ERROR 2c: Measurement Accuracy Uncertain 4096    Critical Error
    Reserved                                    8192    
    Reserved                                    16384   
    Reserved                                    32768   
    """

    if error_codes == []:
        error_codes = set(np.unique(df.error_code)) - set([0])

    for error_code in error_codes:
        df = df.drop(df[df['error_code'] == error_code].index)

    print(f'Error codes remaining: {np.unique(df.error_code)}')

    return df


def filter_columns(df, cols):
    """Filter kolommen met een list van kolomnamen."""

    return df[cols]


def filter_rows(df, filters):
    """Verwijder metingen buiten de gespecificeerde ranges.

    filters = 'latitude >= 50 & latitude < 54 & longitude >= 3.1 & longitude < 7.1'

    filters = {
        'column_name1': [0, 10],
        'column_name2': [20, 30],
        }
    """

    if isinstance(filters, str):

        df = filter_by_query(df, filters)

    elif isinstance(filters, dict):

        df = filter_by_range(df, filters)

    return df


def filter_by_query(df, filter):
    """Filter een dataframe met een query string."""

    return df.query(filter)


def filter_by_range(df, filters):
    """Filter een dataframe met value ranges."""

    for col_name, col_range in filters.items():

        if col_range[0] is None:
            col_range[0] = df[col_name].min()

        if col_range[1] is None:
            col_range[1] = df[col_name].max()

        df = df[(df[col_name] >= col_range[0]) & (df[col_name] < col_range[1])]

    return df
