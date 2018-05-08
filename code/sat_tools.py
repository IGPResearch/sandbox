# -*- coding: utf-8 -*-
"""
Functions to work with satellite imagery
"""
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess as sb

from bs4 import BeautifulSoup
import cartopy.crs as ccrs
import h5py
import rasterio
import requests

import mypaths

DUNDEE_URL = 'http://www.sat.dundee.ac.uk/customers/{project}/data/{dt:%Y%m%d}'
PROJECT = 'renfrew_afis'

AMSR2_URL_BASE = 'https://seaice.uni-bremen.de/data/amsr2/asi_daygrid_swath/'
COORD_URL_BASE = 'https://seaice.uni-bremen.de/data/grid_coordinates/'


def get_amsr2(dt, save_dir=None, res='n6250'):
    """
    Get AMSR2 data and matching coordinates from an HDF file originally
    downloaded from the University of Bremen sea ice data archive

    Basically a wrapper of get_amsr2_coords_file and get_amsr2_data_file funcs
    """
    # TODO: different directories for coords and data
    coords_file = get_amsr2_coords_file(save_dir=save_dir, res=res)
    with h5py.File(coords_file) as f:
        lons = f['Longitude'].value
        lats = f['Latitude'].value
    data_file = get_amsr2_data_file(dt=dt, save_dir=save_dir, res=res)
    with h5py.File(data_file) as f:
        data = f['ASI Ice Concentration'].value
    return lons, lats, data


def get_amsr2_coords_file(save_dir=None, res='n6250', h5=True):
    """
    Download (if the file is already not in the target directory) the file with
    longitude and latitude coordinates
    from the University of Bremen's http server

    Arguments
    ---------
    save_dir: pathlib.Path, optional
        Save destination
    res: str, optional
        Resolution ([n|s][2500|3125|6250|12500])
    h5: bool, optional
        Convert from HDF4 to HDF5 using h4toh5 command (should be installed!)

    Returns
    -------
    Full Path to the file
    """
    url = (Path(COORD_URL_BASE) / res
           / f'LongitudeLatitudeGrid-{res}-Arctic.hdf')
    save_to = download_file(url, save_dir=save_dir)
    if h5:
        completed = sb.run(['h4toh5', save_to])
        assert completed.returncode == 0, f'{completed.args} failed'
    return save_to


def get_amsr2_data_file(dt, save_dir=None, res='n6250', h5=True):
    """
    Download (if the file is already not in the target directory) AMSR2 sea ice
    data from the University of Bremen's http server

    Arguments
    ---------
    dt: datetime.datetime
        Date of the required sea ice data
    save_dir: pathlib.Path, optional
        Save destination
    res: str, optional
        Resolution ([n|s][2500|3125|6250|12500])
    h5: bool, optional
        Convert from HDF4 to HDF5 using h4toh5 command (should be installed!)

    Returns
    -------
    Full Path to the file
    """
    url = (Path(AMSR2_URL_BASE) / res / f'{dt:%Y}' / f'{dt:%m}'.lower()
           / 'Arctic' / f'asi-AMSR2-{res}-{dt:%Y%m%d}-v5.hdf')
    save_to = download_file(url, save_dir=save_dir)
    if h5:
        completed = sb.run(['h4toh5', save_to])
        assert completed.returncode == 0, f'{completed.args} failed'
    return save_to


def get_avail_sat_img_opt():
    with (mypaths.sample_dir/'satellite'/'sat_img_opt.json').open('r') as f:
        sat_img_opt = json.load(f)
    return sat_img_opt


def sort_by_timedelta(x, other):
    _x = datetime.strptime(re.findall(r'_([0-9]{8}_[0-9]{6})_', str(x))[0],
                           '%Y%m%d_%H%M%S')
    return abs(_x - other).total_seconds()


def get_nearest_zfile(zip_obj, dt, instrument, channel, platform,
                      ext='tif'):
    sat_img_opt = get_avail_sat_img_opt()

    opt = sat_img_opt[instrument]
    _d = dict(channel=channel, platform=platform)
    assert _d in opt, ('Combination\n'
                       f'    instrument = {instrument}\n'
                       f'    platform   = {platform}\n'
                       f'    channel    = {channel}\n'
                       f'is not correct;\n\nAvailable:\n{sat_img_opt}')
    sat_opt = dict(instrument=instrument, **_d)

    regex = re.compile(r'^(?=.*_[0-9]{8}_[0-9]{6}_)'
                       + ''.join([f'(?=.*{v})' for v in sat_opt.values()])
                       + '.+')
    fnames = [Path(i).name
              for i in zip_obj.namelist() if i.endswith(ext)]
    filename = sorted(filter(regex.match, fnames),
                      key=lambda x: sort_by_timedelta(x, dt))[0]

    timestamp = datetime.strptime(re.findall(r'(_[0-9]{8}_[0-9]{6}_)',
                                             str(filename))[0],
                                  '_%Y%m%d_%H%M%S_')
    return f'{dt:%Y%m%d}/{filename}', timestamp


def get_nearest_url(dt, instrument, channel, platform,
                    project=PROJECT, ext='tif'):
    sat_img_opt = get_avail_sat_img_opt()

    opt = sat_img_opt[instrument]
    _d = dict(channel=channel, platform=platform)
    assert _d in opt, ('Combination\n'
                       f'    instrument = {instrument}\n'
                       f'    platform   = {platform}\n'
                       f'    channel    = {channel}\n'
                       f'is not correct;\n\nAvailable:\n{sat_img_opt}')
    sat_opt = dict(instrument=instrument, **_d)

    regex = re.compile(r'^(?=.*_[0-9]{8}_[0-9]{6}_)'
                       + ''.join([f'(?=.*{v})' for v in sat_opt.values()])
                       + '.+')

    url_dir = DUNDEE_URL.format(project=project, dt=dt)
    fnames = url_listdir(url_dir, ext='tif')
    filename = sorted(filter(regex.match,
                             map(str, fnames)),
                      key=lambda x: sort_by_timedelta(x, dt))[0]

    timestamp = datetime.strptime(re.findall(r'(_[0-9]{8}_[0-9]{6}_)',
                                             str(filename))[0],
                                  '_%Y%m%d_%H%M%S_')

    return f'{url_dir}/{filename}', timestamp


def url_listdir(url, ext, parser='html.parser'):
    html = requests.get(url).text
    soup = BeautifulSoup(html, parser)
    return [Path(node.get('href'))
            for node in soup.find_all('a')
            if node.get('href', '').endswith(ext)]


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
    else:
        print('Failed with {} ({})'.format(img_req.status_code,
                                           img_req.reason))
    return save_to


def read_raster_stereo(filename):
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
