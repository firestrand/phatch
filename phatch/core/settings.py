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
# Phatch recommends SPE (http://pythonide.stani.be) for editing python.

# Follows PEP8

#from lib.formField import IMAGE_EXTENSIONS
import ct
from pil import IMAGE_READ_EXTENSIONS


def create_settings(config_paths=None, options=None):

    settings = {
        #execute
        'extensions': IMAGE_READ_EXTENSIONS,
        'recursive': False,
        'stop_for_errors': True,
        'overwrite_existing_images': True,
        'no_save': False,
        'check_images_first': True,
        'always_show_status_dialog': True,
        "desktop": False,
        "safe": True,
        "repeat": 1,
        #console
        'console': False,
        'init_fonts': False,
        'interactive': False,
        'verbose': True,
        #gui
        'browse_source': 0,
        'tag_actions': _('All'),
        'description': True,
        'collapse_automatic': False,
        'droplet': False,
        'droplet_path': ct.USER_PATH,
        'file_history': [],
        'image_inspector': False,
        'paths': [ct.USER_PATH],
        #internal
        'overwrite_existing_images_forced': False,
    }
    if options:
        for attr in settings:
            if hasattr(options, attr):
                settings[attr] = getattr(options, attr)
    if config_paths == None:
        #FIXME: when is this happening
        from config import init_config_paths
        config_paths = init_config_paths()
    settings.update(config_paths)
    return settings
