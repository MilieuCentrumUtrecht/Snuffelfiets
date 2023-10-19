#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het analyseren van Snuffelfiets data.

"""


import numpy as np
import pandas as pd
from geopy.distance import geodesic as gd


def aantal_fietsers(df):
    """Bereken het aantal fietsers."""

    unique_ids = np.unique(df.entity_id)

    return len(unique_ids)


def bewerk_timestamp(df, split=False):
    """Maak kolommen met datetime objects.
    
    evt. uitgesplitst in dag, week, maand, kwartaal, jaar
    """

    columns = ['date_time']
    df['date_time'] = pd.to_datetime(
        df['recording_timestamp'],
        format='%Y-%m-%dT%H:%M:%S',
        )
    df = _sort(df)

    if split:
        columns += ['day', 'week', 'month', 'quarter', 'year']
        df['day'] = df['date_time'].dt.dayofyear
        df['week'] = df['date_time'].dt.isocalendar().week
        df['month'] = df['date_time'].dt.month
        df['quarter'] = df['date_time'].dt.quarter
        df['year'] = df['date_time'].dt.year

    print(f"Added {columns} columns to dataframe.")

    return df


def _sort(df, sortcols={'entity_id': True, 'date_time': True}):
    """Default sorting of the dataframe."""

    df = df.sort_values(
        list(sortcols.keys()),
        ascending=list(sortcols.values()),
        ).reset_index(drop=True)
    
    return df


def verdeel_in_ritten(df, t_seconden=1800, split_timestamp=False):
    """Voeg een kolom toe met rit_id."""

    # Converteer timestamps naar datetime objects.
    df = bewerk_timestamp(df, split=split_timestamp)

    # Bereken de duur tussen punten door row-wise time deltas
    df_dt = df.groupby('entity_id')['date_time']
    df['duur'] = df_dt.diff().fillna(np.timedelta64(0, 's'))
    df = _sort(df)

    # Wijs een rit_id toe op basis van de time deltas.
    td = pd.Timedelta(seconds=t_seconden)
    duur_mask = (df['duur'] >= td).astype(int)
    df['rit_id'] = 1
    df['rit_id'] += duur_mask.groupby(df['entity_id']).cumsum()
    df = _sort(df)

    return df


def aantal_ritten(df):
    return sum(aantal_ritten_per_persoon(df)[:,1])


def aantal_ritten_per_persoon(df):
    """Bereken het totaal aantal ritten per persoon"""
    df_new = verdeel_in_ritten(df)
    
    unique_ids = np.unique(df_new.entity_id)
    
    data = np.ones([len(unique_ids),2])
    for i in range(len(unique_ids)):
        data[i,0] = unique_ids[i]
        mask = df_new.entity_id == unique_ids[i]
        data[i,1] = df_new[mask].rit_id.values[-1]        
        
    return data        


def bereken_afstanden(df):
    """Bereken de afstand tussen opeenvolgende coordinaten."""

    df['afstand_hv'] = haversine(
        df.latitude,
        df.longitude,
        df.latitude.shift(),
        df.longitude.shift(),
        )
    td = np.timedelta64(0, 's')
    df['afstand_hv'] = np.where(df['duur'] == td, 0, df['afstand_hv'])

    df['afstand_gd'] = np.vectorize(
        calculate_distance,
        otypes=[np.float64])(
            df.latitude,
            df.longitude,
            df.latitude.shift(),
            df.longitude.shift(),
            df['duur'],
            )

    df['snelheid'] = df['afstand_gd'] / df['duur'].dt.total_seconds()

    df['afstand_dom'] = np.vectorize(
        calculate_distance_to_point,
        otypes=[np.float64])(
            df.latitude,
            df.longitude,
            )

    return df


def haversine(lat1, lon1, lat2, lon2):
    """Return distance in meters.

    between one set of longitude/latitude coordinates and another
    """
    # degene die deze functie geschreven heeft,
    # heeft ervoor gezorgd (vermoed ik) dat
    # de functie werkt met Series
    # (lat1, lon1, .. en km zijn series).

    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])

    newlon = lon2 - lon1
    newlat = lat2 - lat1
 
    haver_formula = np.sin(newlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(newlon/2.0)**2
 
    dist = 2 * np.arcsin(np.sqrt(haver_formula))
    m = 1000 * 6367 * dist   # 6367 for distance in KM, for miles use 3958
 
    return m


def calculate_distance(latitude, longitude, shifted_lat, shifted_lon, duur):
    """Bereken de geodesic distance in meters."""

    td = np.timedelta64(0, 's')
    if duur > td:
        return gd(
            (latitude, longitude),
            (shifted_lat, shifted_lon),
            ).m
    else:
        return 0


def calculate_distance_to_point(latitude, longitude, point=dict(lat=52.090695, lon=5.121314)):
    """Bereken de geodesic distance in meters."""

    return gd(
        (latitude, longitude),
        (point['lat'], point['lon']),
        ).m


def split_in_ritten(df, t_seconden=1800):
    """For each entity_id, split in separate bike rides.
     
       add columns with duration, distance and speed.
    """

    df['duur'] = np.timedelta64(0, 's')
    df['rit_id'] = 0
    df['afstand'] = 0.
    df['snelheid'] = 0.

    for id, df_id in df.groupby('entity_id'):

        # Calculate the time difference between measurements.
        df_id['duur'] = df_id['date_time'].diff().fillna(np.timedelta64(0, 's'))
        # Threshold the time interval to identify new rides.
        rit_mask = df_id['duur'] >= pd.Timedelta(seconds=t_seconden)
        df_id['duur'][rit_mask] = np.timedelta64(0, 's')

        # Fill the rit_id column.
        df_id['rit_id'] = df['rit_id'].max() + 1
        df_id['rit_id'] += rit_mask.astype(int).cumsum()

        # Calculate the distance between measurements.
        df_id['afstand'] = haversine(
            df_id.latitude,
            df_id.longitude,
            df_id.latitude.shift(),
            df_id.longitude.shift(),
            )
        df_id['afstand'][rit_mask] = 0.

        # Calculate the speed for each measurement.
        df_id['snelheid'] = df_id['afstand'] / df_id['duur'].dt.total_seconds()

        # Copy data from entity_id to the collated dataframe.
        columns = ['duur', 'afstand', 'snelheid', 'rit_id']
        for col in columns:
            df.loc[df_id.index, col] = df_id[col]

    print(f"Added {columns} columns to dataframe.")

    return df


def filter_ritten(df, min_measurements=2, max_duration=360, max_distance=200, min_average_speed=1, max_average_speed=35):
    """Filter the rides."""

    # Aggregate over rit_id
    options = {
        'rit_id': ['count'],
        'duur':['sum'],
        'afstand': ['sum'],
        'snelheid': ['mean'],
        }
    df_ritten = df.groupby(['entity_id', 'rit_id']).agg(options)
    df_ritten = df_ritten.reset_index(level=['entity_id', 'rit_id'])

    # Rename the columns.
    cols = ['entity_id', 'rit_id', 'aantal_waarn', 'duur', 'afstand', 'snelheid_mean']
    df_ritten = df_ritten.set_axis(cols, axis=1)

    def apply_mask(df_ritten, mask, reasons=''):

        regels_voor = len(df_ritten)
        df_ritten = df_ritten[mask].reset_index(drop=True)
        Ndel = regels_voor - len(df_ritten)
        print(f'{Ndel:10} rides were removed because {reasons}')

        return df_ritten

    # Apply the filters
    mask = df_ritten['aantal_waarn'] >= min_measurements
    reason = f'number of measurements was < {min_measurements}'
    df_ritten = apply_mask(df_ritten, mask, reason)

    mask = df_ritten['duur'] < np.timedelta64(max_duration * 60, 's')
    reason = f'duration was >= {max_duration} minutes'
    df_ritten = apply_mask(df_ritten, mask, reason)

    mask = df_ritten['afstand'] < max_distance * 1000
    reason = f'distance was >= {max_distance} kilometers'
    df_ritten = apply_mask(df_ritten, mask, reason)

    mask = df_ritten['snelheid_mean'] < max_average_speed * 1000 / 3600
    reason = f'average speed was >= {max_average_speed} km/h'
    df_ritten = apply_mask(df_ritten, mask, reason)

    mask = df_ritten['snelheid_mean'] >= min_average_speed * 1000 / 3600
    reason = f'average speed was < {min_average_speed} km/h'
    df_ritten = apply_mask(df_ritten, mask, reason)

    # Only retain rit_ids that are still in df_ritten
    df = df[df['rit_id'].isin(np.unique(df_ritten['rit_id']))]

    return df


def summary_stats(df):

    # aantal fietsers
    N_fietsers = len(np.unique(df.entity_id))

    # aantal ritten
    N_ritten = len(np.unique(df.rit_id))
    G_ritten = N_ritten / N_fietsers
    dft = df.loc[:, ['entity_id', 'rit_id']].groupby(['entity_id']).nunique()
    M_ritten = int(max(dft['rit_id']))

    # aantal uren
    dft = df.loc[:, ['duur']].sum() / np.timedelta64(1, 'h')
    N_uren = dft.iloc[0]
    G_uren = N_uren / N_fietsers
    dft = df.loc[:, ['entity_id', 'duur']].groupby(['entity_id']).sum()
    M_uren = int(max(dft['duur'] / np.timedelta64(1, 'h')))

    # # aantal kilometers
    dft = df.loc[:, ['afstand']].sum() / 1000
    N_km = dft.iloc[0]
    G_km = N_km / N_fietsers
    dft = df.loc[:, ['entity_id', 'afstand']].groupby(['entity_id']).sum()
    M_km = max(dft['afstand']) / 1000

    return {
        'fietsers': {'N': N_fietsers, 'G': None, 'M': None},
        'ritten': {'N': N_ritten, 'G': G_ritten, 'M': M_ritten},
        'uren': {'N': N_uren, 'G': G_uren, 'M': M_uren},
        'afstand': {'N': N_km, 'G': G_km, 'M': M_km},
    }

