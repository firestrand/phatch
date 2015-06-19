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

#---import modules

#gui-independent
import os
from lib.events import send, Receiver  # send is used when message is imported
from lib.unicoding import ensure_unicode

#---classes


class FrameReceiver(Receiver):
    #---pubsub
    def _pubsub(self):
        Receiver.__init__(self, 'frame')
        #Pubsub events
        self.subscribe('append_save_action')
        self.subscribe('show_execute_dialog')
        self.subscribe('show_error')
        self.subscribe('show_files_message')
        self.subscribe('show_info')
        self.subscribe('show_message')
        self.subscribe('show_notification')
        self.subscribe('show_progress')
        self.subscribe('show_progress_error')
        self.subscribe('show_scrolled_message')
        self.subscribe('show_image_tree')
        self.subscribe('show_status')

    def append_save_action(self, actions):
        """To be overwritten."""
        pass

    def show_execute_dialog(self, result, settings, files=None):
        """To be overwritten."""
        pass

    def show_error(self, message):
        """To be overwritten."""
        pass

    def show_files_message(self, result, message, title, files):
        """To be overwritten."""
        pass

    def show_progress(self, title, parent_max, child_max, message=''):
        """To be overwritten.
        parent_max -> parent loop, eg images
        child_max  -> child loop, eg actions & open"""
        pass

    def show_progress_error(self, result, message, ignore=True):
        """To be overwritten."""
        pass

    def show_scrolled_message(self, message, title, **keyw):
        """To be overwritten."""
        pass


class ProgressReceiver(Receiver):
    def __init__(self, parent_max, child_max):
        self.set_max(parent_max, child_max)
        self._pubsub()

    def set_max(self, parent_max, child_max):
        self.parent_max = parent_max
        self.child_max = child_max
        self.max = parent_max * child_max

    def _pubsub(self):
        Receiver.__init__(self, 'progress')
        self.subscribe('close')
        self.subscribe('update')
        self.subscribe('update_filename')
        self.subscribe('update_index')

    def update_filename(self, result, parent_index, filename):
        dirname, basename = os.path.split(filename)
        dirname = ensure_unicode(dirname)
        basename = ensure_unicode(basename)
        message = u"%s: %s\n%s: %s\n" \
            % (_('In'), dirname, _('File'), basename)
        self.update(result, parent_index * self.child_max, newmsg=message)
        self.sleep()

    def update_index(self, result, parent_index, child_index):
        self.update(result, parent_index * self.child_max + child_index + 1)

    #---overwrite
    def close(self):
        pass

    def update(self, result, value, newmsg=''):
        pass

    def sleep(self):
        pass
