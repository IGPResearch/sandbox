# -*- coding: utf-8 -*-
"""
Paths to data
"""
import os
from pathlib import Path

# Root of the current repository
curdir = Path('.').absolute().parent
sample_dir = curdir/'data'

# External data directories
igp_data_dir = Path('/media')/os.getenv('USER')/'Elements'/'IGP'/'data'
alliance_dir = igp_data_dir/'total_backup_Alliance_20180308'
masin_dir = igp_data_dir/'masin'

# Output directories
plotdir = curdir/'figures'
