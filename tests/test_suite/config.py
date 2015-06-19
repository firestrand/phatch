#!/usr/bin/python

# Phatch - Photo Batch Processor
# Copyright (C) 2009 Nadia Alramli, www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.

# Follows PEP8

import os
import sys
import utils

######################################################
# WARNING: Paths are relative to the parent directory#
######################################################

# Actions to be disabled from the full test
DISABLE_ACTIONS = set(['rename', 'geek', 'geotag'])

# Default image input directory
DEFAULT_INPUT = utils.system_path('input')
# Default image output directory
DEFAULT_OUTPUT = utils.system_path('output/images')
# Default log path
DEFAULT_LOG = utils.system_path('output/logs.txt')
# Default report path
DEFAULT_REPORT = utils.system_path('output/report.txt')

# Out actionlists path
OUT_ACTIONLISTS_PATH = utils.system_path('output/actionlists')
# diff path
OUT_DIFF = utils.system_path('output/diff')
# Phatch package path
PHATCH_PATH = utils.system_path('../phatch/')
# Phatch application path
PHATCH_APP_PATH = utils.system_path(os.path.join(PHATCH_PATH, 'phatch.py'))
# Phatch actions path
PHATCH_ACTIONS_PATH = utils.system_path(os.path.join(PHATCH_PATH, 'actions'))

# Inserting phatch path to system path
sys.path.insert(0, PHATCH_PATH)

import phatch

# Phatch configurations
CONFIG_PATHS = phatch.init_config_paths()
# Phatch log path
USER_LOG_PATH = CONFIG_PATHS['USER_LOG_PATH']
# Phatch library actionlists path
PHATCH_ACTIONLISTS_PATH = CONFIG_PATHS['PHATCH_ACTIONLISTS_PATH']

# Report template
REPORT_TEMPLATE = """
Errors: %(errors)s
Missing: %(missing)s
Corrupted: %(corrupted)s
Mismatch: %(mismatch)s
New: %(new)s
"""

# File names shortening map
SHORTNAME_MAP = sorted([
    ('Automatice', 'Auto'),
    ('Background', 'Bg'),
    ('Corner', ''),
    ('Custom', 'Cust'),
    ('Direction', 'Dir'),
    ('False', '0'),
    ('Floor', 'Fl'),
    ('Gradient', 'Gr'),
    ('Horizontal', 'Hor'),
    ('Justification', 'Just'),
    ('Opacity', 'Op'),
    ('Options', 'Ops'),
    ('Orientation', 'Ori'),
    ('Position', 'Pos'),
    ('Reflection', 'Rfl'),
    ('Rotate', 'Rot'),
    ('Rotation', 'Rot'),
    ('SameMethodforAllCorners', 'Same'),
    ('Thumbnail', 'Thumb'),
    ('Transformation', 'Trafo'),
    ('Transparent', 'Trapa'),
    ('True', '1'),
    ('Utility', 'Util'),
    ('Vertical', 'Ver'),
    ('degrees', '')], key=lambda a: len(a[0]), reverse=True)
