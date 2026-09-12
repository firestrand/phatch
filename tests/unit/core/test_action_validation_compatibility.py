from __future__ import annotations

from phatch.core import api


class ActionFake:
    tags: tuple[str, ...] = ()
    valid_last: bool = False

    def __init__(self, *, enabled: bool = True, forced: bool = False) -> None:
        self._enabled = enabled
        self._forced = forced

    def is_enabled(self) -> bool:
        return self._enabled

    def is_overwrite_existing_images_forced(self) -> bool:
        return self._forced


def test_empty_rejection_preserves_exact_error_call(monkeypatch) -> None:
    # Given
    errors: list[str] = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: True)
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    # When
    result = api.check_actionlist([], {"no_save": False})

    # Then
    assert result is None
    assert errors == ["Nothing to do. The action list is empty."]


def test_unsafe_rejection_preserves_diagnostic_and_exact_error_call(
    monkeypatch,
) -> None:
    # Given
    action = ActionFake(enabled=False)
    errors: list[str] = []
    safety_calls: list[tuple[ActionFake, ...]] = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: True)
    monkeypatch.setattr(
        api,
        "assert_safe",
        lambda actions: safety_calls.append(actions) or "unsafe payload",
    )
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    # When
    result = api.check_actionlist([action], {"no_save": False})

    # Then
    assert result is None
    assert safety_calls == [(action,)]
    assert errors == [
        "This action list is unsafe:\n\nunsafe payload\n"
        "Disable Safe Mode in the Tools menu if you trust this action list."
    ]


def test_all_disabled_rejection_preserves_exact_error_call(monkeypatch) -> None:
    # Given
    errors: list[str] = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    # When
    result = api.check_actionlist(
        [ActionFake(enabled=False)],
        {"no_save": False},
    )

    # Then
    assert result is None
    assert errors == ["Nothing to do. There is no action enabled."]


def test_save_required_preserves_exact_frame_call(monkeypatch) -> None:
    # Given
    enabled = ActionFake()
    disabled = ActionFake(enabled=False)
    requests: list[list[ActionFake]] = []
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_append_save_action", requests.append)

    # When
    result = api.check_actionlist(
        [enabled, disabled],
        {"no_save": False},
    )

    # Then
    assert result is None
    assert requests == [[enabled]]


def test_accepted_result_preserves_list_and_settings_mutation(monkeypatch) -> None:
    # Given
    final = ActionFake(forced=True)
    final.valid_last = True
    settings = {"no_save": False}
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)

    # When
    result = api.check_actionlist([final], settings)

    # Then
    assert result == [final]
    assert isinstance(result, list)
    assert settings == {
        "no_save": False,
        "overwrite_existing_images_forced": True,
    }


def test_file_only_legacy_surface_preserves_boolean_result() -> None:
    # Given
    file_action = ActionFake()
    file_action.tags = ("file",)

    # When / Then
    assert api.check_actionlist_file_only([file_action]) is True
    assert api.check_actionlist_file_only([ActionFake()]) is False
