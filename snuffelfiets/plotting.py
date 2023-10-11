#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het plotten van Snuffelfiets data.

"""

import numpy as np
import plotly.figure_factory as ff
import plotly.express as px
from plotly.colors import hex_to_rgb


def hexbin_mapbox(df, hexagon_size=None, hexbin_args={}, layout_args={}):
    """Maak een hexbin plot."""

    if hexagon_size is not None:
        hexbin_args['nx_hexagon'] = np.ceil(
            (df['longitude'].max() - df['longitude'].min()) / hexagon_size,
            ).astype('int')

    if hexbin_args['nx_hexagon'] > 500:
        print('Too many hexagons; please increase hexagon_size')
        return

    default_hexbin_args = dict(
        data_frame=df,
        lat='latitude',
        lon='longitude',
        agg_func=np.average,
        color='pm2_5',
        animation_frame=None,
        color_continuous_scale=['green', 'red'],
        range_color=[0, 50],
        show_original_data=False,
        nx_hexagon=200,
        min_count=6,
        opacity=0.3,
        labels={'color': 'PM2.5'},
        center=dict(lat=52.090695, lon=5.121314),
        zoom=10,
    )
    default_layout_args = dict(
        mapbox_style='carto-positron',
        margin=dict(b=0, t=0, l=0, r=0),
    )

    hexbin_args = {**default_hexbin_args, **hexbin_args}
    layout_args = {**default_layout_args, **layout_args}

    fig = ff.create_hexbin_mapbox(**hexbin_args)
    fig.update_layout(**layout_args)

    return fig


def line_mapbox(df, plot_args={}, layout_args={}):
    """Maak een line plot."""

    plot_args_defaults = dict(
        data_frame=df,
        lat='latitude',
        lon='longitude',
        color='rit_id',
        center=dict(lat=52.090695, lon=5.121314),
        zoom=10,
        animation_frame=None,
    )

    layout_args_defaults = dict(
        mapbox_style='carto-positron',
        margin=dict(b=0, t=0, l=0, r=0),
    )

    plot_args = {**plot_args_defaults, **plot_args}
    layout_args = {**layout_args_defaults, **layout_args}

    fig = px.line_mapbox(**plot_args)
    fig.update_layout(**layout_args)

    return fig


def save_fig(fig, outputstem, fig_formats=['html', 'pdf']):
    """Save de figuur."""

    for fig_format in fig_formats:
        if fig_format == 'html':
            fig.write_html(f"{outputstem}.{fig_format}")
        else:
            fig.write_image(f"{outputstem}.{fig_format}")



def discrete_colorscale(bvals=[], colors=[]):
    """Functie to create discrete colorscale.

    bvals -  list of values bounding intervals/ranges of interest
    colors - list of rgb or hex color codes for values in [bvals[k], bvals[k+1]], 0 <= k < len(bvals)-1
    returns  a nonuniform   discrete colorscale
    """

    if not bvals:
        bvals = [
            0, 3, 6, 9,
            12, 18, 24, 30,
            38, 46, 60, 100, 100,
            ]
    if not colors:
        colors_hex =[
            '#0020c5', '#006df8', '#2dcdfb', '#c4ecfd',
            '#fffed0', '#fffc4d', '#f4e645', '#ffb255',
            '#ff9845', '#fe7626', '#ff0a17', '#dc0625',
            ]
        colors =[f"rgb{hex_to_rgb(c)}" for c in colors_hex]

    if len(bvals) != len(colors) + 1:
        raise ValueError(f"len boundaries {len(bvals)} should be equal to len colours + 1 = {len(colors)+1}")

    bvals = sorted(bvals)
    nvals = [(v-bvals[0]) / (bvals[-1] - bvals[0]) for v in bvals]  # normalized values

    dcolorscale = []
    for k in range(len(colors)):
        dcolorscale.extend([[nvals[k], colors[k]], [nvals[k+1], colors[k]]])

    return dcolorscale 


