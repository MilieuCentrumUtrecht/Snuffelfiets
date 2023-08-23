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


def aantal_ritten(df):
    """Bereken het totaal aantal ritten."""

    pass


def bewerk_timestamp(df, split=False):
    """Maak kolommen met datetime objects.
    
    evt. uitgesplitst in dag, week, maand, jaar
    """

    df['date_time'] = pd.to_datetime(
        df['recording_timestamp'],
        format='%Y-%m-%dT%H:%M:%S',
        )
    df = _sort(df)

    if split:
        df['day'] = df['date_time'].dt.dayofyear
        df['week'] = df['date_time'].dt.isocalendar().week
        df['month'] = df['date_time'].dt.month
        df['year'] = df['date_time'].dt.year

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
