# -*- coding: utf-8 -*-
"""
Various plotting functions and objects
"""
from pathlib import Path

from matplotlib.pyplot import imread
from matplotlib.offsetbox import AnchoredOffsetbox, OffsetImage


def add_igp_logo(ax, loc, image_bg="transparent", zoom=1, **kwargs):
    """
    Add the IGP logo to a figure.

    (a clone of MetPy package's _add_logo() function)

    Logo credit: Andrew Elvidge

    Arguments
    ----------
    ax : matplotlib axes
       The `axes` instance used for plotting
    loc : int or str
       Location of logo within the axes
    image_bg : str
       Logo background (white|transparent)
    zoom : float
       Size of logo to be used.
    kwargs : keyword arguments
        kwargs passed to `matplotlib.offsetbox.AnchoredOffsetbox`,
        except for `frameon` and `loc`
    """
    logodir = Path("_static")
    # fname_suffix = {'S': '75x75',
    #                 'M': '150x150',
    #                 'L': '300x300'}
    fname_prefix = {"transparent": "t", "white": "w"}
    try:
        fname = "igp_logo_{}_300x300.png".format(fname_prefix[image_bg])
        fpath = logodir / fname
    except KeyError:
        raise ValueError("Unknown logo size or background")

    logo = imread(str(fpath))
    imagebox = OffsetImage(logo, zoom=zoom)
    ao = AnchoredOffsetbox(loc=loc, child=imagebox, frameon=False, **kwargs)
    ax.add_artist(ao)
