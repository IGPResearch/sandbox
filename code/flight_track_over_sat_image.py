# coding: utf-8
"""
Satellite image for each flight day at approximate time of the flight
with flight track (shaded with altitude) overlaid
"""
from datetime import datetime, timedelta
import cartopy.crs as ccrs
import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.offsetbox import AnchoredText
from pathlib import Path
import xarray as xr
# local modules
import mypaths
from common_defs import FLIGHTS, MASIN_FILE_MASK
import sat_tools
from cart import ukmo_igp_map


flight_date = datetime(2018, 3, 1)
sat_opts = [
    # dict(instrument="avhrr", platform="metopb", channel="band2_vis"),
    # dict(instrument="avhrr", platform="noaa19", channel="band2_vis"),
    # dict(instrument="avhrr", platform="avhrr", channel="band4_bt"),
    # dict(instrument="avhrr", platform="noaa19", channel="band4_bt"),
    # dict(instrument="viirs", platform="j01", channel="m15"),
    # dict(instrument="viirs", platform="j01", channel="m05"),
    dict(instrument="viirs", platform="npp", channel="m15"),
    dict(instrument="viirs", platform="npp", channel="m05"),
    dict(instrument="modis", platform="aqua", channel="bt31"),
    # dict(instrument="modis", platform="terra", channel="vis02"),
    dict(instrument="modis", platform="aqua", channel="vis02"),
    # dict(instrument="modis", platform="terra", channel="bt31"),
]

flight_id = [k for k, v in FLIGHTS.items() if v == f'{flight_date:%Y%m%d}'][0]

# Paths
PLOTDIR = mypaths.plotdir / 'flight_track_satellite'
PLOTDIR.mkdir(parents=True, exist_ok=True)
SAVE_SAT_DIR = mypaths.sat_dir / f'{flight_date:%Y%m%d}'
masin_data_path = (mypaths.masin_dir / f'flight{flight_id}'
                   / MASIN_FILE_MASK.format(flight_date=flight_date,
                                            flight_id=flight_id))

# Plotting parameters
mapkw = dict(transform=ccrs.PlateCarree())
gridline_kw = dict(linestyle=(0, (10, 10)), linewidth=0.5, color='C9')
sat_stride = 1
flt_stride = 10
COAST = dict(scale='50m', facecolor='none', edgecolor='C8', alpha=0.75)

cmap = plt.cm.plasma_r
cmap.set_over('#36013f')
bounds = [0, 200, 300, 500, 1000, 1500, 2000]
norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=256)

ds = xr.open_dataset(masin_data_path, decode_times=False)
ref_date = flight_date.replace(hour=0, minute=0, second=0, microsecond=0)
# TODO: decode from ds.Time.units
ds.coords['data_point'] = np.array([np.datetime64(ref_date)
                                    + np.timedelta64(timedelta(seconds=int(i)))
                                    for i in ds.Time.values])
ds = ds.drop('Time')
ds = ds.rename({'data_point': 'Time'})
masin_x = ds.LON_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]
masin_y = ds.LAT_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]
masin_z = ds.ALT_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]

flight_hours = sorted(set(ds.Time.dt.hour.values))

for sat_opt in sat_opts:
    print(sat_opt)
    prev_tstamp = ref_date
    for hour in flight_hours:
        dt = ref_date + timedelta(hours=int(hour))
        print(dt)
        # Get satellite image with given options closest to the flight time
        url, tstamp = sat_tools.get_nearest_url(dt, **sat_opt)

        if tstamp == prev_tstamp:
            print('skip')
            continue
        sat_image_name = SAVE_SAT_DIR/Path(url).name
        if not sat_image_name.is_file():
            stat = sat_tools.download_file(url=url, save_dir=SAVE_SAT_DIR)
            assert stat == 0, 'something went wrong with downloading the image'

        # Open the satellite image and get data, image extent, and CRS
        im, extent, crs = sat_tools.read_raster_stereographic(str(sat_image_name))

        fig = plt.figure(figsize=(15, 7))
        ax = ukmo_igp_map(fig, coast=COAST, **gridline_kw)

        h = ax.imshow(im[::sat_stride, ::sat_stride],
                      origin='upper', extent=extent,
                      transform=crs, cmap='gray', interpolation='nearest')

        ax.plot(masin_x, masin_y, linewidth=5, color='k', alpha=0.25, **mapkw)
        points = np.array([masin_x, masin_y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=cmap, linewidth=3, zorder=10,
                            norm=norm, **mapkw)
        lc.set_array(masin_z)
        h = ax.add_collection(lc)

        cb = fig.colorbar(h, ax=ax, extend='max', pad=0.01)
        cb.ax.tick_params(labelsize='x-large')
        cb.ax.set_ylabel(f'Altitude ({masin_z.units.strip()})',
                         fontsize='x-large', rotation=270, labelpad=15)
        at = AnchoredText(f'Flight {flight_id}\n{tstamp:%H:%M:%S %d %B}',
                          prop=dict(size='x-large'), loc=1)
        ax.add_artist(at)

        sat_opt_str = '_'.join(sat_opt.values())
        fig.savefig(PLOTDIR /
                    f'flight_{flight_id}_{tstamp:%Y%m%d%H%M}_{sat_opt_str}.png',
                    dpi=300, bbox_inches='tight')
        prev_tstamp = tstamp
        plt.close()
