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
import sys

try:
    import typer  # type: ignore
except ImportError:  # pragma: no cover - fallback when typer is absent
    class _TyperFallback:
        @staticmethod
        def prompt(message: str) -> str:
            return input(message)

    typer = _TyperFallback()  # type: ignore

from rich.console import Console as RichConsole
from rich.progress import (
    BarColumn,
    Progress as RichProgress,
    TextColumn,
)

if __name__ == '__main__':
    sys.path.insert(0, '../..')
    from phatch.phatch import init_config_paths
    init_config_paths()

#gui-independent
from phatch.core import api, ct
from phatch.core.message import FrameReceiver, ProgressReceiver
from phatch.lib import formField
from phatch.lib import safe

#---functions


def u(txt):
    # Python 3: strings are already Unicode, no encoding needed for stdout
    return txt


def ask(message, answers):
    normalized = [answer.lower() for answer in answers]
    while True:
        response = typer.prompt(u(message)).strip().lower()
        if response in normalized:
            index = normalized.index(response)
            return answers[index]


def ask_yes_no(message):
    return ask(message, [_('yes'), _('no')]) == _('yes')

#---classes


class CliMixin:
    def show_error(self, message, exit=True):
        self.show_message('\n%s: %s' % (_('Error'), message))
        if exit:
            self.exit()

    def show_message(self, *messages):
        if not self.verbose:
            return
        text = '\n'.join(messages)
        if hasattr(self, 'console'):
            self.console.print(text)
        else:
            self.output.write(u(text) + '\n')
            self.output.flush()

    def show_notification(self, message, *args, **keyw):
        self.show_message(message)

    def write(self, message, end=''):
        if not self.verbose:
            return
        if hasattr(self, 'console'):
            self.console.print(u(message), end=end)
        else:
            self.output.write(u(message) + end)
            self.output.flush()

    def exit(self):
        sys.exit()

    show_info = show_message


class Progress(CliMixin, ProgressReceiver):
    def __init__(self, title, parent_max, child_max, verbose, output, message=''):
        ProgressReceiver.__init__(self, parent_max, child_max)
        self.verbose = verbose
        self.output = output
        self.console = RichConsole(file=output, highlight=False)
        self._progress = None
        self._task_id = None
        if self.verbose:
            total = parent_max * child_max
            self.console.print(f"\n{title} ...")
            self._progress = RichProgress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.percentage:>3.0f}%"),
                console=self.console,
                transient=True,
            )
            self._progress.start()
            self._task_id = self._progress.add_task(title, total=total)

    def close(self):
        if self._progress is not None:
            self._progress.stop()
            self._progress = None
        self.unsubscribe_all()

    def update(self, result, value, newmsg=''):
        if self.verbose and self._progress is not None and self._task_id is not None:
            update_kwargs = {'completed': value}
            if newmsg:
                update_kwargs['description'] = newmsg
            self._progress.update(self._task_id, **update_kwargs)
        result['keepgoing'] = True


class Frame(CliMixin, FrameReceiver):
    Progress = Progress

    def __init__(self, actionlist, paths, settings, output=sys.stdout):
        self.verbose = settings['verbose'] or settings['interactive']
        self.settings = settings
        self.output = output
        self.console = RichConsole(file=output, highlight=False)
        self._pubsub()
        data, warning = api.open_actionlist(
            self.verify_actionlist(actionlist))
        if formField.get_safe():
            if warning:
                raise safe.UnsafeError(warning)
        else:
            self.show_message(warning)
        settings['recipe_path'] = str(actionlist)
        self.result = api.apply_actions_to_photos(
            data['actions'], settings, paths=paths)

    def append_save_action(self, actions):
        self.show_error(ct.SAVE_ACTION_NEEDED, exit=False)

    def verify_actionlist(self, actionlist):
        if actionlist:
            return actionlist
        if self.settings['interactive']:
            while not(os.path.splitext(actionlist)[1].lower() == ct.EXTENSION
                    and os.path.isfile(actionlist)):
                actionlist = input(_('Action list') + '(*%s) : '\
                    % ct.EXTENSION).strip().lstrip('file://')
            return actionlist
        else:
            raise ValueError('No action list provided')

    def show_execute_dialog(self, result, settings, files=None):
        """To be overwritten."""
        if not settings['paths'] and settings['interactive']:
            settings['paths'] = input(_('Image paths') + ': ').strip()
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
        self.show_error(message, exit=False)
        if not self.settings['interactive']:
            result['answer'] = _('stop')
            return
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
    import json
    from phatch.core.batch import BatchPlan
    from phatch.lib.atomic import AtomicOutput
    try:
        frame = Frame(actionlist, paths, settings)
        result = frame.result
    except (OSError, ValueError, KeyError, safe.UnsafeError) as exc:
        # Recipe/input setup failures have a stable status; no traceback payload.
        sys.stderr.write('Invalid batch setup: %s\n' % type(exc).__name__)
        from phatch.core.batch import BatchResult, Issue
        result = BatchResult(status='invalid_setup',
                             issues=[Issue('invalid_recipe',
                                           'Recipe could not be loaded')])
    if isinstance(result, BatchPlan):
        payload = result.to_dict(include_paths=settings.get('report_paths', False))
        status = 0 if result.valid else 2
        if not settings.get('report_path'):
            sys.stdout.write(json.dumps(payload, indent=2) + '\n')
    else:
        payload = result.to_dict(include_paths=settings.get('report_paths', False))
        status = result.exit_code
    if settings.get('report_path'):
        from pathlib import Path
        report_path = Path(settings['report_path']).expanduser().resolve()
        protected = {Path(actionlist).resolve()} if actionlist else set()
        if settings.get('manifest_path'):
            protected.add(Path(settings['manifest_path']).expanduser().resolve())
        if hasattr(result, 'reserved_paths'):
            protected.update(path.resolve() for path in result.reserved_paths)
        if isinstance(result, BatchPlan):
            protected.update(path.resolve() for path in result.resource_paths)
        for item in result.files:
            protected.add(item.source.resolve())
            if isinstance(result, BatchPlan):
                protected.update(dest.path.resolve() for dest in item.destinations)
            else:
                protected.update(output.resolve() for output in item.outputs)
                protected.update(output.resolve() for output in item.artifacts)
        for value in paths:
            candidate = Path(value).expanduser().resolve()
            protected.add(candidate)
            if (candidate.is_dir() and report_path.is_relative_to(candidate)
                and report_path.suffix.lstrip('.').lower() in settings['extensions']):
                protected.add(report_path)
        if report_path in protected:
            sys.stderr.write('Report path overlaps a recipe, input or output; report not written.\n')
            return 2
        with AtomicOutput(report_path) as temporary:
            temporary.write_text(json.dumps(payload, indent=2) + '\n',
                                 encoding='utf-8')
    return status

if __name__ == '__main__':
    example()
