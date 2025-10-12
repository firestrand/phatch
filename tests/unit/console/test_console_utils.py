import io

import builtins

from phatch.console import console


if not hasattr(builtins, '_'):
    builtins._ = lambda x: x


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
    progress.close()

    assert ('add_task', 'Title', 2) in events
    assert ('update', 1, 'Step') in events
    assert 'stop' in events
