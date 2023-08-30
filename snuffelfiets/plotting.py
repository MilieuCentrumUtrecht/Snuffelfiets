#!/usr/bin/env python

# -*- coding: utf-8 -*-

"""Python module voor het plotten van Snuffelfiets data.

"""

import numpy as np
import plotly.figure_factory as ff


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


def save_fig(fig, outputstem, fig_formats=['html', 'pdf']):
    """Save de figuur."""

    for fig_format in fig_formats:
        if fig_format == 'html':
            fig.write_html(f"{outputstem}.{fig_format}")
        else:
            fig.write_image(f"{outputstem}.{fig_format}")
