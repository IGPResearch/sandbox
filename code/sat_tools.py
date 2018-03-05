# -*- coding: utf-8 -*-
"""
Functions to work with satellite imagery
"""
import cartopy.crs as ccrs
import rasterio


def read_raster_stereographic(filename):
    """
    Read the image and essential metadata from a GeoTIFF file

    Used for reading satellite imagery in polar stereographic projection
    from NERC Satellite Receiving Station, Dundee University, Scotland
    (http://www.sat.dundee.ac.uk/)

    Parameters
    ----------
    filename: str or path-like
        path to the GeoTIFF file

    Returns
    -------
    im: numpy array
        image data
    extent: list
        image extent in units of the original projection
    crs: cartopy.crs.Projection
        Stereographic projection of the image
    """
    with rasterio.open(filename, 'r') as src:
        proj = src.crs.to_dict()
        crs = ccrs.Stereographic(central_latitude=proj['lat_0'],
                                 central_longitude=proj['lon_0'],
                                 false_easting=proj['x_0'],
                                 false_northing=proj['y_0'],
                                 true_scale_latitude=proj['lat_ts'],
                                 globe=ccrs.Globe(datum=proj['datum']))

        # read image into ndarray
        im = src.read().squeeze()

        # calculate extent of raster
        xmin = src.transform[0]
        xmax = src.transform[0] + src.transform[1]*src.width
        ymin = src.transform[3] + src.transform[5]*src.height
        ymax = src.transform[3]
        extent = [xmin, xmax, ymin, ymax]

    return im, extent, crs
