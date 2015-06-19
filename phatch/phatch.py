#!/usr/bin/env python

# Phatch - Photo Batch Processor
# Copyright (C) 2007-2008  www.stani.be
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

# Follows PEP8

"""Local launch script for all platforms"""

import sys

if sys.version_info[0] != 2:
    sys.exit('Sorry, Phatch is only compatible with Python 2.x!\n')

from os.path import abspath, dirname, join
from core import config


def create_paths(relative=''):
    root = dirname(abspath(__file__))

    def expand(path):
        return abspath(join(root, relative, path))

    phatch_data_path = 'data'
    paths = {
        'PHATCH_DOCS_PATH': 'docs',
        'PHATCH_FONTS_CACHE_PATH': 'cache/fonts',
        'PHATCH_IMAGE_PATH': 'images',
        'PHATCH_LOCALE_PATH': 'locale',
        #data
        'PHATCH_DATA_PATH': phatch_data_path,
        'PHATCH_ACTIONLISTS_PATH': join(phatch_data_path, 'actionlists'),
        'PHATCH_BLENDER_PATH': join(phatch_data_path, 'blender'),
        'PHATCH_FONTS_PATH': join(phatch_data_path, 'fonts'),
        'PHATCH_HIGHLIGHTS_PATH': join(phatch_data_path, 'highlights'),
        'PHATCH_MASKS_PATH': join(phatch_data_path, 'masks'),
        'PHATCH_PERSPECTIVE_PATH': join(phatch_data_path, 'perspective'),
    }
    for key, path in paths.items():
        paths[key] = expand(path)
    paths['PHATCH_PYTHON_PATH'] = root
    return paths


def init_config_paths():
    if hasattr(sys, "frozen"):
        __file__ = sys.argv[0]
        relative = ''
    else:
        relative = '..'
    return config.init_config_paths(config_paths=create_paths(relative))


def main():
    #override paths with local paths
    #start application
    import app
    app.main(init_config_paths(), app_file=__file__)

if __name__ == '__main__':
    main()
