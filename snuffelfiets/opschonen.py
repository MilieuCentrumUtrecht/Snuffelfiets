#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het opschonen van Snuffelfiets data.

"""

import numpy as np


# sommige data moet worden aangepast:
# https://ckan-dataplatform-nl.dataplatform.nl/dataset/near-real-time-onbewerkte-snuffelfiets-gegevens-provincie-utrecht

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


# https://ckan.dataplatform.nl/dataset/snuffelfiets-extra-informatie-snifferbike-additional-info

ERROR_DESCRIPTIONS = {
    0: ['No Error', 'No Error'],
    1: ['ACCELEROMETER ERROR 1: Sensor Not Found', 'Critical Error'],
    2: ['Reserved', ''],
    4: ['BME ERROR 1: Sensor Not Found', 'Critical Error'],
    8: ['BME ERROR 2: Failed to begin reading', 'Critical Error'],
    16: ['GPS ERROR 1: Sensor Not Found', 'Critical Error'],
    32: ['GPS ERROR 2: No GPS Fix', 'Allowed Error, device maybe indoors'],
    64: ['Reserved', ''],
    128: ['NO2 ERROR 1: Sensor Not Found', 'Should never be seen, NO2 removed in software.'],
    256: ['Reserved', ''],
    512: ['PM ERROR 1: Sensor Not Found', 'Critical Error'],
    1024: ['PM ERROR 2a: Measurement Start Failure', 'Critical Error'],
    2048: ['PM ERROR 2b: Measurement Read Failure', 'Allowed Error, PM sensors nt ready. Wait 5 more measurements.'],
    4096: ['PM ERROR 2c: Measurement Accuracy Uncertain', 'Critical Error'],
    8192: ['Reserved', ''],
    16384: ['Reserved', ''],
    32768: ['Reserved', ''],
}


def correct_units(df, correcties=CORRECTIE_DEFAULTS):
    """Converteer de ruwe data naar correcte units."""

    for col, correctie in correcties.items():

        # doe niets als item niet gespecificeerd
        default = {'factor': 1.0, 'offset': 0, 'conditie': None}
        corr = {**default, **correctie}

        print(f'Correcting column {col:12} using {correctie}')

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


def analyse_errors(df):
    """Print a short error breakdown."""

    error_codes = np.unique(df['error_code'])

    for error_code in error_codes:

        N = len(df[df['error_code']==error_code])

        print(f'code {error_code:10}: count {N:15}')

        compound = split_error_code(error_code)

        for ec in compound:
            descr = ERROR_DESCRIPTIONS[ec]
            d = ' '
            print(f'{ec:15}: {d:22} type       : {descr[1]}')
            print(f'{ec:15}: {d:22} description: {descr[0]}')


def split_error_code(error_code):
    """Split compound bitwise error codes."""

    nbits = len(bin(error_code)[2:])

    bits = [(error_code >> bit) & 1 for bit in range(nbits - 1, -1, -1)]

    error_codes = []
    for pos, bit in enumerate(bits[::-1]):
        if bit:
            error_codes += [2**pos]

    return error_codes


def verwijder_errors(df, error_codes=[], print_breakdown=False):
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

    if print_breakdown:
        analyse_errors(df)

    if error_codes == []:
        error_codes = set(np.unique(df.error_code)) - set([0])

    mask = np.zeros_like(df.error_code, dtype='bool')
    for error_code in error_codes:
        emask = df['error_code'] == error_code
        print(f'Removing {np.sum(emask):15} measurements with error_code {error_code:15}')
        mask |= emask

    df = df[~mask]

    print(f'')
    print(f'Error codes remaining: {np.unique(df.error_code)}')
    print(f'Measurements remaining: {df.shape[0]}.')

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


def filter_lat_lon(df, latlon={}):

    coord_query = ''
    for col, q in latlon.items():
        coord_query += f"{col} >= {q['center'] - q['extent']}"
        coord_query += ' & '
        coord_query += f"{col} < {q['center'] + q['extent']}"
        coord_query += ' & '
    coord_query = coord_query.strip(' & ')

    df = filter_rows(df, filters=coord_query)

    return df
