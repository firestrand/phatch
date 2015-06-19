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
#
# Follows PEP8


#---import modules

#standard library
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, '../..')
    from phatch.phatch import init_config_paths
    init_config_paths()

#gui-independent
from core import api, ct
from core.message import FrameReceiver, ProgressReceiver
from lib import formField
from lib import safe
from lib.unicoding import ENCODING

#api.init()

#---functions


def u(txt):
    return txt.encode(ENCODING, 'replace')


def ask(message, answers):
    answer = None
    while not(answer in answers):
        answer = raw_input(u(message)).strip().lower()
    return answer


def ask_yes_no(message):
    return ask(message, [_('yes'), _('no')]) == _('yes')

#---classes


class CliMixin:
    def show_error(self, message, exit=True):
        self.show_message(u'\n%s: %s' % (_('Error'), message))
        if exit:
            self.exit()

    def show_message(self, *messages):
        self.write(u'\n'.join(messages) + '\n')

    def show_notification(self, message, *args, **keyw):
        self.show_message(message)

    def write(self, message):
        if self.verbose:
            self.output.write(u(message))
            self.output.flush()

    def exit(self):
        sys.exit()

    show_info = show_message


class Progress(CliMixin, ProgressReceiver):
    def __init__(self, title, parent_max, child_max, verbose, output, \
                                    message=''):
        ProgressReceiver.__init__(self, parent_max, child_max)
        self.verbose = verbose
        self.output = output
        self.previous = 0
        self.write(u'\n%s ...\n' % title)

    def close(self):
        self.erase()
        self.unsubscribe_all()
        #self.show_message('done!')
        #self.previous = 0
        del self

    def erase(self):
        self.write('\b' * self.previous + ' ' * self.previous + \
                                            '\b' * self.previous)

    def update(self, result, value, newmsg=''):
        if self.verbose:
            #erase previous
            self.erase()
            if newmsg:
                self.write(newmsg)
            percent = int(100.0 * value / self.max)
            hpercent = percent / 2
            message = '%3d%% [%s%s]' % \
                (percent, '=' * hpercent, ' ' * (50 - hpercent))
            self.write(message)
            self.previous = len(message)
        result['keepgoing'] = True


class Frame(CliMixin, FrameReceiver):
    Progress = Progress

    def __init__(self, actionlist, paths, settings, output=sys.stdout):
        self.verbose = settings['verbose'] or settings['interactive']
        self.settings = settings
        self.output = output
        self._pubsub()
        data, warning = api.open_actionlist(
            self.verify_actionlist(actionlist))
        if formField.get_safe():
            if warning:
                raise safe.UnsafeError(warning)
        else:
            self.show_message(warning)
        report = api.apply_actions_to_photos(data['actions'], settings, \
                                                            paths=paths)

    def append_save_action(self, actions):
        self.show_error(ct.SAVE_ACTION_NEEDED, exit=True)

    def verify_actionlist(self, actionlist):
        if actionlist:
            return actionlist
        if self.settings['interactive']:
            while not(os.path.splitext(actionlist)[1].lower() == ct.EXTENSION
                    and os.path.isfile(actionlist)):
                actionlist = raw_input(_('Action list') + '(*%s) : '\
                    % ct.EXTENSION).strip().lstrip('file://')
            return actionlist
        else:
            self.show_error(_('No action list provided.'), exit=True)

    def show_execute_dialog(self, result, settings, files=None):
        """To be overwritten."""
        if not settings['paths'] and settings['interactive']:
            settings['paths'] = raw_input(_('Image paths') + ': ').strip()
        if not settings['paths']:
            self.show_error('No image paths given.', exit=True)
        result['cancel'] = False

    def show_files_message(self, result, message, title, files):
        if self.verbose:
            self.show_error(message + '\n' + '\n'.join(files), exit=False)
        if self.settings['interactive']:
            if ask_yes_no(_('Do you want to continue?') + \
                ' (%s/%s) ' % (_('yes'), _('no'))):
                self.exit()
        result['cancel'] = False

    def show_progress(self, title, parent_max, child_max=1, message=''):
        self.progress = self.Progress(title, parent_max, child_max,
            self.verbose, self.output, message)

    def show_progress_error(self, result, message, ignore=True):
        self.show_error(message, exit=not self.settings['interactive'])
        result['stop_for_errors'] = True
        result['answer'] = ask(_('What do you want to do now?'),
            [_('abort'), _('skip'), _('ignore')])

    def show_scrolled_message(self, message, title, **keyw):
        self.show_message(title + '\n' + message)

    def show_image_tree(self, result, *args, **keyw):
        #ignore this, not useful for server
        result['answer'] = True

    def show_status(self, message, *args, **keyw):
        #already done by notification
        #self.show_message(message)
        pass


def example():
    Frame('/home/stani/sync/python/phatch/action lists/test_all.phatch',
        interactive=True, \
    path=['/home/stani/sync/python/phatch/test images/building/IMGA3166.JPG'])


def main(actionlist, paths, settings):
    Frame(actionlist, paths, settings)

if __name__ == '__main__':
    example()
