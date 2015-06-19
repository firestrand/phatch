# Phatch - Photo Batch Processor
# Copyright (C) 2007-2008 www.stani.be
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

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '../..')
    from phatch.phatch import init_config_paths
    init_config_paths()

import os
import Image
import api
from config import USER_PREVIEW_PATH
from lib import openImage
from lib.system import ensure_path


def generate(source, size=(48, 48), path=USER_PREVIEW_PATH, force=True):
    source_image = openImage.open(source)
    source_image.thumbnail(
        (min(source_image.size[0], size[0] * 1),
        min(source_image.size[0], size[0] * 1)),
        Image.ANTIALIAS)
    ensure_path(path)
    for Action in api.ACTIONS.values():
        action = Action()
        filename = os.path.join(path, action.label + '.png')
        if os.path.exists(filename) and not force:
            continue
        action.init()
        result = action.apply_pil(source_image.copy())
        result.thumbnail(size, Image.ANTIALIAS)
        result.save(filename)


if __name__ == '__main__':
    api.init()
    generate('/home/stani/sync/python/phatch/icons/lenna/lenna_new.png')
