# coding: utf-8
"""
Satellite image for each flight day at approximate time of the flight
with flight track (shaded with altitude) overlaid
"""
import concurrent.futures
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import mkdtemp
from zipfile import ZipFile

import cartopy.crs as ccrs
import numpy as np
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.offsetbox import AnchoredText
import matplotlib.patheffects as mpe
import xarray as xr
# local modules
import mypaths
from common_defs import SCI_FLIGHTS, MASIN_FILE_MASK
import sat_tools
from cart import ukmo_igp_map

use_concurrent = True

use_tmp_dir = False

add_sea_ice = 'amsr2'

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

# Paths
ARCH_DIR = mypaths.dundee_dir
if use_tmp_dir:
    EXTRACTDIR = Path(mkdtemp())
else:
    EXTRACTDIR = mypaths.dundee_dir  # mkdtemp()
PLOTDIR = mypaths.plotdir / 'flight_track_satellite'
PLOTDIR.mkdir(parents=True, exist_ok=True)
SICDIR = None  # Directory with sea ice data files (also used as flag)
if add_sea_ice.lower() == 'amsr2':
    SICDIR = mypaths.amsr2_dir
elif add_sea_ice.lower() == 'ostia':
    raise NotImplementedError
else:
    pass

# Plotting parameters
mapkw = dict(transform=ccrs.PlateCarree())
gridline_kw = dict(linestyle=(0, (10, 10)), linewidth=0.5, color='C9')
igp_map_kw = dict(extent=[-26, -11, 63, 72], ticks=[3, 1])
zoom_str = ''  # '_zoom'
sat_stride = 1
flt_stride = 10
COAST = dict(scale='50m', facecolor='none', edgecolor='C8', alpha=0.75)
sic_kw = dict(levels=[15, 80], cmap='cool_r', linewidths=0.5)
sic_clab_kw = dict(fmt="%2.0f%%", fontsize='x-small', use_clabeltext=True)
path_effects = [mpe.withStroke(linewidth=0.5, foreground='w')]
svfigkw = dict(dpi=300, bbox_inches='tight')

cmap = plt.cm.plasma_r
cmap.set_over('#36013f')
bounds = [0, 200, 300, 500, 1000, 1500, 2000]
norm = mcolors.BoundaryNorm(boundaries=bounds, ncolors=256)


def plotter(flight_id):
    flight_datestr = SCI_FLIGHTS[flight_id]
    flight_date = datetime.strptime(flight_datestr, '%Y%m%d')
    save_sat_dir = EXTRACTDIR  # / f'{flight_date:%Y%m%d}'
    masin_data_path = (mypaths.masin_dir / f'flight{flight_id}'
                       / MASIN_FILE_MASK.format(flight_date=flight_date,
                                                flight_id=flight_id))
    ds = xr.open_dataset(masin_data_path, decode_times=False)
    ref_date = flight_date.replace(hour=0, minute=0, second=0, microsecond=0)
    # TODO: decode from ds.Time.units
    ds.coords['data_point'] = np.array([np.datetime64(ref_date)
                                        + np.timedelta64(timedelta(seconds=int(i)))  # NOQA
                                        for i in ds.Time.values])
    ds = ds.drop('Time')
    ds = ds.rename({'data_point': 'Time'})
    masin_x = ds.LON_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]
    masin_y = ds.LAT_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]
    masin_z = ds.ALT_OXTS[~ds.ALT_OXTS.isnull()][::flt_stride]
    masin_t = ds.Time[~ds.ALT_OXTS.isnull()]

    flight_hours = sorted(set(masin_t.dt.hour.values))

    seaice_str = ''
    if add_sea_ice.lower() == 'amsr2':
        (sic_lons, sic_lats,
         sic_data) = sat_tools.get_amsr2(dt=flight_date, save_dir=SICDIR)
        seaice_str = '_amsr2'

    print(flight_date)
    for sat_opt in sat_opts:
        print(sat_opt)
        prev_tstamp = ref_date
        for hour in flight_hours:
            dt = ref_date + timedelta(hours=int(hour))
            # Get satellite image with given options closest to the flight time
            arch_file = ARCH_DIR / f'{dt:%Y%m%d}.zip'
            with ZipFile(arch_file) as z:
                zfile, tstamp = sat_tools.get_nearest_zfile(z, dt, **sat_opt)

            if tstamp == prev_tstamp:
                continue

            sat_image_name = save_sat_dir/zfile
            if not sat_image_name.is_file():
                # er = sat_tools.download_file(url=url, save_dir=save_sat_dir)
                # assert err == 0, 'Downloading the image failed'
                with ZipFile(arch_file) as z:
                    z.extract(zfile, save_sat_dir)

            # Open the satellite image and get data, image extent, and CRS
            im, extent, crs = sat_tools.read_raster_stereo(str(sat_image_name))

            fig = plt.figure(figsize=(12, 8))
            ax = ukmo_igp_map(fig, coast=COAST, **igp_map_kw, **gridline_kw)

            ax.imshow(im[::sat_stride, ::sat_stride],
                      origin='upper', extent=extent,
                      transform=crs, cmap='gray', interpolation='nearest')
            if SICDIR:
                # Add contours of sea-ice concentration
                cntr = ax.contour(sic_lons, sic_lats, sic_data,
                                  **sic_kw, **mapkw)
                clbls = ax.clabel(cntr, **sic_clab_kw)
                plt.setp(cntr.collections + clbls, path_effects=path_effects)

            ax.plot(masin_x, masin_y, linewidth=5, color='k',
                    alpha=0.25, **mapkw)
            points = np.array([masin_x, masin_y]).T.reshape(-1, 1, 2)
            segments = np.concatenate([points[:-1], points[1:]], axis=1)
            lc = LineCollection(segments, cmap=cmap, linewidth=3, zorder=10,
                                norm=norm, **mapkw)
            lc.set_array(masin_z)
            h = ax.add_collection(lc)

            cb = fig.colorbar(h, ax=ax, extend='max', pad=0.01)
            cb.ax.tick_params(labelsize='large')
            cb.ax.set_ylabel(f'Altitude ({masin_z.units.strip()})',
                             fontsize='large', rotation=270, labelpad=15)

            txt = f'Flight {flight_id} | {tstamp:%d %b}'
            txt += (f'\nFlight time: {str(masin_t.min().values)[11:16]}'
                    f'-{str(masin_t.max().values)[11:16]}')
            txt += f'\n{" | ".join(sat_opt.values())}'
            txt += f'\nSat image time: {tstamp:%H:%M}'
            if SICDIR:
                txt += f'\n{add_sea_ice.upper()} sea ice'
            # ax.set_title(txt, loc='left', fontsize='large')
            ax.add_artist(AnchoredText(txt, prop=dict(size='large'), loc=4))

            sat_opt_str = '_'.join(sat_opt.values())
            outdir = PLOTDIR / f'flight{flight_id}'
            outdir.mkdir(exist_ok=True)
            fig.savefig(outdir /
                        (f'flight_{flight_id}_{tstamp:%Y%m%d%H%M}'
                         f'_{sat_opt_str}{seaice_str}{zoom_str}.png'),
                        **svfigkw)
            prev_tstamp = tstamp
            plt.close(fig)


def main():
    if use_concurrent:
        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.map(plotter, SCI_FLIGHTS.keys())
    else:
        for flight_id in SCI_FLIGHTS.keys():
            plotter(flight_id)


if __name__ == '__main__':
    main()
