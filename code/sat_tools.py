# -*- coding: utf-8 -*-
"""
Functions to work with satellite imagery
"""
import cartopy.crs as ccrs
import rasterio
from pathlib import Path
from bs4 import BeautifulSoup
import requests


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


def _get_sat_name_options(dundee_folder_url, ext='.png'):
    """
    Note: works with old, instrument-wise format
    
    TODO: use regex for fname parsing
    """
    req_txt = requests.get(dundee_folder_url).text
    soup = BeautifulSoup(req_txt, 'html.parser')
    fnames = [Path(node.get('href')) for node in soup.find_all('a') if node.get('href', '').endswith(ext)]
    combinations = list(set(['_'.join(str(fname.with_suffix('')).split('_')[4:]) for fname in fnames]))
    sat_img_opt = dict()
    for comb in combinations:
        params = comb.split('_')
        if len(params) == 3:
            try:
                sat_img_opt[params[1]].append(dict(platform=params[2], channel=params[0]))
            except KeyError:
                sat_img_opt[params[1]] = [dict(platform=params[2], channel=params[0])]
        elif len(params) == 4:
            try:
                sat_img_opt[params[2]].append(dict(platform=params[2], channel='_'.join(params[0:2])))
            except KeyError:
                sat_img_opt[params[2]] = [dict(platform=params[2], channel='_'.join(params[0:2]))]
    return sat_img_opt


def download_file(url, save_dir=None, mkdir=True, **req_kw):
    """
    Download file using requests
    """
    # get request
    img_req = requests.get(url, **req_kw)

    if img_req.status_code == 200:
        # save destination
        if save_dir is None:
            save_dir = Path('.')
        else:
            assert isinstance(save_dir, Path)
            save_dir.mkdir(parents=True, exist_ok=True)
        file_name = Path(url).name
        save_to = save_dir / file_name
        # open in binary mode
        with save_to.open('wb') as file:
            # write to file
            file.write(img_req.content)
        return 0
    else:
        print('Failed with {} ({})'.format(img_req.status_code,
                                           img_req.reason))
        return img_req.status_code