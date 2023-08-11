#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het analyseren van Snuffelfiets data.

"""


import numpy as np


def aantal_fietsers(df):
    """Bereken het aantal fietsers."""

    unique_ids = np.unique(df.entity_id)

    return len(unique_ids)

def aantal_ritten(df):
    """Bereken het totaal aantal ritten."""

    pass
