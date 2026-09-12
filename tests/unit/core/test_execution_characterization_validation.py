from phatch.core import api
from phatch.services.legacy_actions import LegacyActionAdapter, LegacyActionRun


class ActionFake:
    tags: tuple[str, ...] = ()
    metadata: tuple[str, ...] = ()
    valid_last: bool = False

    def __init__(self, label="Action", events=None, init_error=None):
        self.label = label
        self._enabled = True
        self._forced = False
        self._events = events
        self._init_error = init_error

    def is_enabled(self):
        if self._events is not None:
            self._events.append(f"enabled:{self.label}")
        return self._enabled

    def is_overwrite_existing_images_forced(self):
        return self._forced

    def init(self):
        if self._events is not None:
            self._events.append(f"init:{self.label}")
        if self._init_error is not None:
            raise self._init_error

    def _get_fields(self):
        return {}

    def is_done(self, photo):
        return False

    def apply(self, photo, settings, cache):
        return photo

    def dump(self):
        return {}


class InteractionFake:
    def record_execution_error(self, photo, issue, action, *, can_continue) -> None:
        return None


def settings(*, no_save=False):
    return {"no_save": no_save}


def test_safe_mode_validation_precedes_disabled_action_removal(monkeypatch):
    events = []
    action = ActionFake(events=events)
    action._enabled = False
    errors = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: True)
    monkeypatch.setattr(
        api, "assert_safe", lambda actions: events.append("safe") or "unsafe"
    )
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    result = api.check_actionlist([action], settings())

    assert result is None
    assert events == ["safe"]
    assert len(errors) == 1


def test_empty_and_all_disabled_action_lists_fail(monkeypatch):
    errors = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    empty = api.check_actionlist([], settings())
    action = ActionFake()
    action._enabled = False
    disabled = api.check_actionlist([action], settings())

    assert empty is None
    assert disabled is None
    assert len(errors) == 2


def test_missing_final_save_requests_insertion(monkeypatch):
    action = ActionFake()
    requests = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_append_save_action", requests.append)

    result = api.check_actionlist([action], settings())

    assert result is None
    assert requests == [[action]]


def test_file_only_and_no_save_lists_bypass_final_save_requirement(monkeypatch):
    file_action = ActionFake()
    file_action.tags = ("file",)
    image_action = ActionFake()
    requests = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_append_save_action", requests.append)

    file_result = api.check_actionlist([file_action], settings())
    no_save_result = api.check_actionlist([image_action], settings(no_save=True))

    assert file_result == [file_action]
    assert no_save_result == [image_action]
    assert requests == []


def test_forced_overwrite_is_derived_from_final_action_and_no_save(monkeypatch):
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    forced_action = ActionFake()
    forced_action.valid_last = True
    forced_action._forced = True
    save_settings = settings()
    no_save_settings = settings(no_save=True)

    api.check_actionlist([forced_action], save_settings)
    api.check_actionlist([forced_action], no_save_settings)

    assert save_settings["overwrite_existing_images_forced"] is True
    assert no_save_settings["overwrite_existing_images_forced"] is False


def test_action_initialization_stops_at_first_failure():
    events = []
    actions = [
        ActionFake("first", events=events),
        ActionFake("broken", events=events, init_error=RuntimeError("boom")),
        ActionFake("never", events=events),
    ]
    run = LegacyActionRun({}, InteractionFake(), tuple(actions))
    issue = None
    for action in actions:
        issue = run.initialize(LegacyActionAdapter(action))
        if issue is not None:
            break

    assert issue is not None
    assert issue.action_label == "broken"
    assert events == ["init:first", "init:broken"]
