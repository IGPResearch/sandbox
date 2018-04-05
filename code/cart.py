# -*- coding: utf-8 -*-
"""
Collection of functions for cartographic plotting.

Borrows some functions from arke library
"""
from arke.cart import (get_xy_ticks, add_coastline,
                       _lambert_xticks, _lambert_yticks)
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER 


def ukmo_igp_map(fig, subplot_grd=111,
                 clon=-21, clat=68.5, extent=[-34, -7.8, 61, 75.2],
                 ticks=[5, 1], coast=None, **gridline_kw):
    """
    Create axes the Stereographic projection in a given figure
    
    Defaults to plots like UK Met Office supplied for the IGP campaign
    Parameters
    ----------
    fig: matplotlib.figure.Figure
         matplotlib figure
    subplot_grd: int, optional
        3-digit integer describing the position of the subplot
        default: 111
    clon: float, optional
        central longitude of the projection
    clat: float, optional
        central latitude of the projection
    coast: str or dict, optional
        parameters to draw a coastline, see `add_coastline()` for details
    extent: sequence, optional
        extent (x0, x1, y0, y1) of the map in the given coordinate projection
    ticks: sequence, optional
        see `get_xy_ticks()` for details
    gridline_kw: dict, optional
        Gridline style dictionary
    Returns
    -------
    cartopy.mpl.geoaxes.GeoAxesSubplot
        axes with the LCC projection
    """
    # Create a projection
    proj = ccrs.Stereographic(central_latitude=68.5, central_longitude=-21)

    # Draw a set of axes with coastlines
    ax = fig.add_subplot(subplot_grd, projection=proj)
    if isinstance(extent, list):
        ax.set_extent(extent, crs=ccrs.PlateCarree())

    add_coastline(ax, coast)

    if ticks:
        xticks, yticks = get_xy_ticks(ticks)
        # *must* call draw in order to get the axis boundary used to add ticks
        fig.canvas.draw()
        # Draw the lines using cartopy's built-in gridliner
        ax.gridlines(xlocs=xticks, ylocs=yticks, **gridline_kw)
        # Label the end-points of the gridlines using the custom tick makers:
        ax.xaxis.set_major_formatter(LONGITUDE_FORMATTER)
        ax.yaxis.set_major_formatter(LATITUDE_FORMATTER)
        _lambert_xticks(ax, xticks)
        _lambert_yticks(ax, yticks)

    return ax