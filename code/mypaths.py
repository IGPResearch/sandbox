# -*- coding: utf-8 -*-
"""
Paths to data
Depends on path.py package
"""
import os
from pathlib import Path

# Root of the present repository
topdir = Path('.').absolute().parent

# Data directories
igp_data_dir = Path('/media')/os.getenv('USER')/'Elements'/'IGP'/'data'/'total_backup_Alliance_20180308'

# Output directories
plotdir = topdir/'figures'