# -*- coding: utf-8 -*-
"""
Functions to work with satellite imagery
"""
from bs4 import BeautifulSoup
import cartopy.crs as ccrs
from datetime import datetime
import json
from pathlib import Path
import rasterio
import re
import requests

import mypaths

URL_BASE = 'http://www.sat.dundee.ac.uk/customers/{project_name}/data/{dt:%Y%m%d}'

INST_WISE_FMT = '{platform}_{instrument}_{channel}_{dt:%Y%m%d_%H%M%S}_mapping6_500.{ext}'
INST_WISE_RE = r'{platform}_{instrument}_{channel}_([0-9]{{8}}_[0-9]{{6}})_'
NEW_FMT_DATE = datetime(2018, 3, 6)
DATE_WISE_FMT = 'mapping6_500_{dt:%Y%m%d_%H%M%S}_{channel}_{instrument}_{platform}.{ext}'
DATE_WISE_RE = r'_([0-9]{{8}}_[0-9]{{6}})_{channel}_{instrument}_{platform}'

project_name = 'renfrew_afis'


def get_avail_sat_img_opt():
    with (mypaths.sample_dir / 'satellite' / 'sat_img_opt.json').open('r') as f:
        sat_img_opt = json.load(f)
    return sat_img_opt


def sort_by_timedelta(x, other):
    _x = datetime.strptime(re.findall(r'_([0-9]{8}_[0-9]{6})_', str(x))[0],
                           '%Y%m%d_%H%M%S')
    return abs(_x - other).total_seconds()


def get_nearest_url(dt, instrument, channel, platform,
                    project_name=project_name, ext='tif'):
    sat_img_opt = get_avail_sat_img_opt()
    
    opt = sat_img_opt[instrument]
    _d = dict(channel=channel, platform=platform)
    assert _d in opt, ('Combination\n'
                       f'    instrument = {instrument}\n'
                       f'    platform   = {platform}\n'
                       f'    channel    = {channel}\n'
                       f'is not correct;\n\nAvailable:\n{sat_img_opt}')
    sat_opt = dict(instrument=instrument, **_d)
    
    if dt >= NEW_FMT_DATE:
        filename_mask = DATE_WISE_FMT
        regex = re.compile(DATE_WISE_RE.format(**sat_opt))
    else:
        filename_mask = INST_WISE_FMT
        regex = re.compile(INST_WISE_RE.format(**sat_opt))
    
    url_dir = URL_BASE.format(project_name=project_name, dt=dt)
    fnames = url_listdir(url_dir, ext='tif')
    filename = sorted(filter(regex.match,
                             map(str, fnames)),
                      key=lambda x: sort_by_timedelta(x, dt))[0]

    return f'{url_dir}/{filename}'


def url_listdir(url, ext, parser='html.parser'):
    html = requests.get(url).text
    soup = BeautifulSoup(html, parser)
    return [Path(node.get('href'))
            for node in soup.find_all('a') if node.get('href', '').endswith(ext)]


def _get_sat_name_options(dundee_folder_url, ext='.png'):
    """
    Note: works with old, instrument-wise format
    
    TODO: use regex for fname parsing
    """
    fnames = url_listdir(dundee_folder_url, ext)
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