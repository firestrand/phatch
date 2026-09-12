import io
import os

import builtins
from types import SimpleNamespace

import pytest

from phatch.console import console


if not hasattr(builtins, '_'):
    setattr(builtins, '_', lambda x: x)


class CliHarness(console.CliMixin):
    verbose: bool
    output: io.StringIO
    console: SimpleNamespace


def test_ask_uses_typer_prompt(monkeypatch):
    responses = iter(['maybe', 'yes'])

    def fake_prompt(message):
        return next(responses)

    monkeypatch.setattr(console.typer, 'prompt', fake_prompt)

    result = console.ask('Question', ['yes', 'no'])

    assert result == 'yes'


def test_progress_uses_rich_progress(monkeypatch):
    events = []

    class DummyProgress:
        def __init__(self, *args, **kwargs):
            events.append(('init', args, kwargs))
        def start(self):
            events.append('start')
        def add_task(self, description, total):
            events.append(('add_task', description, total))
            return 1
        def update(self, task_id, completed=None, description=None):
            events.append(('update', completed, description))
        def stop(self):
            events.append('stop')

    monkeypatch.setattr(console, 'RichProgress', lambda *a, **k: DummyProgress(*a, **k))

    progress = console.Progress('Title', parent_max=2, child_max=1, verbose=True, output=io.StringIO())
    progress.update({}, 1, newmsg='Step')
    progress.update({}, 2)
    progress.close()

    assert ('add_task', 'Title', 2) in events
    assert ('update', 1, 'Step') in events
    assert 'stop' in events


def test_main_initializes_api_before_creating_frame(monkeypatch):
    from phatch.core import api

    events = []
    registry = object()
    monkeypatch.setattr(api, 'init', lambda: registry)
    monkeypatch.setattr(
        console,
        'Frame',
        lambda actionlist, paths, settings, registry: events.append(
            ('frame', actionlist, paths, settings, registry)),
    )

    console.main('actions.phatch', ['image.jpg'], {'verbose': False})

    assert events == [
        ('frame', 'actions.phatch', ['image.jpg'], {'verbose': False}, registry),
    ]


def test_cli_mixin_writes_to_plain_output_and_honors_verbose():
    frame = CliHarness()
    frame.verbose = True
    frame.output = io.StringIO()

    frame.show_message('one', 'two')
    frame.write('three', end='!')

    assert frame.output.getvalue() == 'one\ntwo\nthree!'
    frame.verbose = False
    frame.show_message('hidden')
    frame.write('hidden')
    assert frame.output.getvalue() == 'one\ntwo\nthree!'


def test_cli_mixin_uses_rich_console():
    calls = []
    frame = CliHarness()
    frame.verbose = True
    frame.console = SimpleNamespace(print=lambda *args, **kwargs: calls.append(
        (args, kwargs)))

    frame.show_message('message')
    frame.write('text', end='!')

    assert calls == [
        (('message',), {}),
        (('text',), {'end': '!'}),
    ]


def test_cli_mixin_show_error_can_continue_or_exit(monkeypatch):
    events = []
    frame = console.CliMixin()
    monkeypatch.setattr(frame, 'show_message', events.append)
    monkeypatch.setattr(frame, 'exit', lambda: events.append('exit'))

    frame.show_error('problem', exit=False)
    frame.show_error('fatal')

    assert events[-1] == 'exit'


def test_cli_mixin_notification_delegates_to_message(monkeypatch):
    frame = CliHarness()
    events = []
    monkeypatch.setattr(frame, 'show_message', events.append)

    frame.show_notification('notice')

    assert events == ['notice']


def test_cli_mixin_exit_raises_system_exit():
    with pytest.raises(SystemExit):
        console.CliMixin().exit()


def test_ask_yes_no_maps_localized_answer(monkeypatch):
    monkeypatch.setattr(console, 'ask', lambda message, answers: answers[0])

    assert console.ask_yes_no('Continue?') is True


def test_progress_silent_mode_updates_result_without_renderer():
    result = {}
    progress = console.Progress(
        'Title', parent_max=1, child_max=1, verbose=False,
        output=io.StringIO())

    progress.update(result, 1)
    progress.close()

    assert result == {'keepgoing': True}


def make_frame(settings=None):
    frame = object.__new__(console.Frame)
    frame.settings = settings or {'interactive': False, 'paths': []}
    frame.verbose = True
    frame.output = io.StringIO()
    frame.show_message = lambda *messages: None
    frame.show_error = lambda message, exit=True: None
    return frame


def test_frame_initialization_opens_and_applies_actionlist(monkeypatch):
    from phatch.core import api

    events = []
    monkeypatch.setattr(console.Frame, '_pubsub', lambda self: events.append('pubsub'))
    monkeypatch.setattr(
        api,
        'open_actionlist',
        lambda path: ({'actions': ['action']}, ''),
    )
    monkeypatch.setattr(
        api,
        'apply_actions_to_photos',
        lambda actions, settings, paths: events.append(
            (actions, settings, paths)),
    )
    monkeypatch.setattr(console.formField, 'get_safe', lambda: False)

    console.Frame(
        'actions.phatch', ['image.jpg'],
        {'verbose': False, 'interactive': False})

    assert events == [
        'pubsub',
        (['action'], {'verbose': False, 'interactive': False}, ['image.jpg']),
    ]


def test_frame_initialization_rejects_unsafe_actionlist(monkeypatch):
    from phatch.core import api

    monkeypatch.setattr(console.Frame, '_pubsub', lambda self: None)
    monkeypatch.setattr(
        api,
        'open_actionlist',
        lambda path: ({'actions': []}, 'unsafe'),
    )
    monkeypatch.setattr(console.formField, 'get_safe', lambda: True)

    with pytest.raises(console.safe.UnsafeError):
        console.Frame(
            'actions.phatch', [],
            {'verbose': False, 'interactive': False})


def test_frame_initialization_processes_safe_actionlist_without_warning(
        monkeypatch):
    from phatch.core import api

    processed = []
    monkeypatch.setattr(console.Frame, '_pubsub', lambda self: None)
    monkeypatch.setattr(
        api,
        'open_actionlist',
        lambda path: ({'actions': ['resize']}, ''),
    )
    monkeypatch.setattr(
        api,
        'apply_actions_to_photos',
        lambda actions, settings, paths: processed.append((actions, paths)),
    )
    monkeypatch.setattr(console.formField, 'get_safe', lambda: True)

    console.Frame(
        'actions.phatch', ['image.jpg'],
        {'verbose': False, 'interactive': False})

    assert processed == [(['resize'], ['image.jpg'])]


def test_frame_initialization_displays_warning_when_safe_mode_is_off(
        monkeypatch):
    from phatch.core import api

    output = io.StringIO()
    monkeypatch.setattr(console.Frame, '_pubsub', lambda self: None)
    monkeypatch.setattr(
        api,
        'open_actionlist',
        lambda path: ({'actions': []}, 'warning'),
    )
    monkeypatch.setattr(api, 'apply_actions_to_photos', lambda *args, **kwargs: None)
    monkeypatch.setattr(console.formField, 'get_safe', lambda: False)

    console.Frame(
        'actions.phatch', [],
        {'verbose': True, 'interactive': False}, output=output)

    assert 'warning' in output.getvalue()


def test_frame_verify_actionlist_handles_value_and_missing(monkeypatch):
    frame = make_frame()

    assert frame.verify_actionlist('actions.phatch') == 'actions.phatch'
    exits = []
    frame.show_error = lambda message, exit=True: exits.append(exit)
    assert frame.verify_actionlist('') is None
    assert exits == [True]


def test_frame_verify_actionlist_prompts_until_path_is_valid(monkeypatch):
    frame = make_frame({'interactive': True, 'paths': []})
    answers = iter(['wrong.txt', 'actions.phatch'])
    monkeypatch.setattr(builtins, 'input', lambda message: next(answers))
    monkeypatch.setattr(
        os.path,
        'isfile',
        lambda path: path == 'actions.phatch',
    )

    assert frame.verify_actionlist('') == 'actions.phatch'


def test_frame_dialog_methods_update_results(monkeypatch):
    frame = make_frame({'interactive': False, 'paths': ['image.jpg']})
    result = {}

    frame.show_execute_dialog(result, frame.settings)
    frame.show_files_message(result, 'message', 'title', ['image.jpg'])
    frame.show_image_tree(result)
    frame.show_status('status')

    assert result == {'cancel': False, 'answer': True}


def test_frame_execute_dialog_prompts_for_missing_paths(monkeypatch):
    frame = make_frame({'interactive': True, 'paths': []})
    monkeypatch.setattr(builtins, 'input', lambda message: 'image.jpg')
    result = {}

    frame.show_execute_dialog(result, frame.settings)

    assert frame.settings['paths'] == 'image.jpg'
    assert result == {'cancel': False}


def test_frame_execute_dialog_reports_absent_noninteractive_paths():
    errors = []
    frame = make_frame({'interactive': False, 'paths': []})
    frame.show_error = lambda message, exit=True: errors.append((message, exit))
    result = {}

    frame.show_execute_dialog(result, frame.settings)

    assert errors == [('No image paths given.', True)]


def test_frame_files_message_interactive_yes_exits(monkeypatch):
    events = []
    frame = make_frame({'interactive': True, 'paths': ['image.jpg']})
    monkeypatch.setattr(frame, 'exit', lambda: events.append('exit'))
    monkeypatch.setattr(console, 'ask_yes_no', lambda message: True)
    result = {}

    frame.show_files_message(result, 'message', 'title', ['image.jpg'])

    assert events == ['exit']
    assert result == {'cancel': False}


def test_frame_files_message_quiet_decline_continues_without_output(
        monkeypatch):
    frame = make_frame({'interactive': True, 'paths': ['image.jpg']})
    output = io.StringIO()
    frame.output = output
    frame.verbose = False
    frame.show_error = console.CliMixin.show_error.__get__(frame)
    monkeypatch.setattr(console, 'ask_yes_no', lambda message: False)
    result = {}

    frame.show_files_message(result, 'problem', 'title', ['image.jpg'])

    assert result == {'cancel': False}
    assert output.getvalue() == ''


def test_frame_append_save_action_reports_required_save():
    errors = []
    frame = make_frame()
    frame.show_error = lambda message, exit=True: errors.append((message, exit))

    frame.append_save_action([])

    assert errors == [(console.ct.SAVE_ACTION_NEEDED, True)]


def test_frame_progress_and_error_methods(monkeypatch):
    events = []
    frame = make_frame({'interactive': True, 'paths': ['image.jpg']})
    monkeypatch.setattr(
        console.Frame,
        'Progress',
        lambda *args: events.append(args) or 'progress',
    )
    monkeypatch.setattr(console, 'ask', lambda message, answers: answers[1])
    result = {}

    frame.show_progress('Title', 2, child_max=3, message='Step')
    frame.show_progress_error(result, 'problem')
    frame.show_scrolled_message('message', 'title')

    assert frame.progress == 'progress'
    assert result == {'stop_for_errors': True, 'answer': 'skip'}
