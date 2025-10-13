import builtins

if '_' not in builtins.__dict__:
    builtins.__dict__['_'] = lambda value: value

from phatch.pyWx.droplet_manager import DropletManager


class FakeFrame:
    def __init__(self):
        self.calls = []

    def show(self, visible):
        self.calls.append(visible)


def test_toggle_creates_frame_when_actionlist_valid():
    frame = FakeFrame()
    created = []

    manager = DropletManager(
        export_actions=lambda: [1],
        settings_provider=lambda: {"safe": True},
        check_actionlist=lambda actions, settings: True,
        create_frame=lambda: created.append(True) or frame,
        schedule_hide=lambda: None,
        state_callback=lambda _: None,
    )

    manager.toggle(True)

    assert created == [True]
    assert frame.calls == [True]


def test_toggle_schedules_hide_when_invalid():
    schedule = []
    manager = DropletManager(
        export_actions=lambda: [],
        settings_provider=lambda: {},
        check_actionlist=lambda actions, settings: False,
        create_frame=lambda: FakeFrame(),
        schedule_hide=lambda: schedule.append("hide"),
        state_callback=lambda _: None,
    )

    manager.toggle(True)

    assert schedule == ["hide"]


def test_toggle_off_hides_existing_frame():
    frame = FakeFrame()
    manager = DropletManager(
        export_actions=lambda: [1],
        settings_provider=lambda: {},
        check_actionlist=lambda actions, settings: True,
        create_frame=lambda: frame,
        schedule_hide=lambda: None,
        state_callback=lambda _: None,
    )

    manager.toggle(True)
    manager.toggle(False)

    assert frame.calls == [True, False]


def test_handle_show_event_clears_frame_when_hidden():
    frame = FakeFrame()
    events = []
    manager = DropletManager(
        export_actions=lambda: [1],
        settings_provider=lambda: {},
        check_actionlist=lambda actions, settings: True,
        create_frame=lambda: frame,
        schedule_hide=lambda: None,
        state_callback=lambda flag: events.append(flag),
    )

    manager.toggle(True)
    manager.handle_show_event(False)

    manager.toggle(True)

    assert events == [True, False, True]
    assert frame.calls == [True, True]
