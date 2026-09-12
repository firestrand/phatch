from __future__ import annotations

from phatch.core.execution_ports import Action
from phatch.core.execution_types import ExecutionOptions
from phatch.services.action_validation import (
    AcceptedActionList,
    ActionListRejectionReason,
    RejectedActionList,
    SaveActionRequired,
    validate_actionlist,
)


class ActionFake:
    __slots__ = ("_enabled", "_forced", "_label", "_tags", "_valid_last", "events")

    def __init__(
        self,
        label: str,
        *,
        enabled: bool = True,
        forced: bool = False,
        tags: tuple[str, ...] = (),
        valid_last: bool = False,
        events: list[str] | None = None,
    ) -> None:
        self._label = label
        self._enabled = enabled
        self._forced = forced
        self._tags = tags
        self._valid_last = valid_last
        self.events = events

    @property
    def label(self) -> str:
        return self._label

    @property
    def tags(self) -> tuple[str, ...]:
        return self._tags

    @property
    def metadata(self) -> tuple[str, ...]:
        return ()

    @property
    def valid_last(self) -> bool:
        return self._valid_last

    def is_enabled(self) -> bool:
        if self.events is not None:
            self.events.append(f"enabled:{self.label}")
        return self._enabled

    def is_overwrite_existing_images_forced(self) -> bool:
        return self._forced


class SafetyCheckerFake:
    __slots__ = ("diagnostic", "received")

    def __init__(self, diagnostic: str = "") -> None:
        self.diagnostic = diagnostic
        self.received: list[tuple[Action, ...]] = []

    def __call__(self, actions: tuple[Action, ...]) -> str:
        self.received.append(actions)
        return self.diagnostic


def options(
    *, require_save_action: bool = True, safe_mode: bool = True
) -> ExecutionOptions:
    return ExecutionOptions(
        extensions=(),
        require_save_action=require_save_action,
        safe_mode=safe_mode,
    )


def test_empty_action_list_is_rejected_without_safety_check() -> None:
    # Given
    safety = SafetyCheckerFake()

    # When
    result = validate_actionlist((), options(), safety)

    # Then
    assert result == RejectedActionList(ActionListRejectionReason.EMPTY)
    assert safety.received == []


def test_unsafe_disabled_action_is_checked_before_enabled_filtering() -> None:
    # Given
    events: list[str] = []
    action = ActionFake("disabled", enabled=False, events=events)
    safety = SafetyCheckerFake("unsafe details")

    # When
    result = validate_actionlist((action,), options(), safety)

    # Then
    assert result == RejectedActionList(
        ActionListRejectionReason.UNSAFE,
        diagnostic="unsafe details",
    )
    assert safety.received == [(action,)]
    assert events == []


def test_all_disabled_actions_are_rejected() -> None:
    # Given
    action = ActionFake("disabled", enabled=False)

    # When
    result = validate_actionlist((action,), options(), SafetyCheckerFake())

    # Then
    assert result == RejectedActionList(ActionListRejectionReason.ALL_DISABLED)


def test_enabled_actions_preserve_order_and_duplicates() -> None:
    # Given
    first = ActionFake("first", valid_last=True)
    disabled = ActionFake("disabled", enabled=False)
    actions = (first, disabled, first)

    # When
    result = validate_actionlist(actions, options(), SafetyCheckerFake())

    # Then
    assert result == AcceptedActionList((first, first), False)


def test_valid_last_action_satisfies_save_requirement() -> None:
    # Given
    action = ActionFake("terminal", valid_last=True)

    # When
    result = validate_actionlist((action,), options(), SafetyCheckerFake())

    # Then
    assert result == AcceptedActionList((action,), False)


def test_file_only_actions_satisfy_save_requirement() -> None:
    # Given
    actions = (
        ActionFake("copy", tags=("file",)),
        ActionFake("rename", tags=("file",)),
    )

    # When
    result = validate_actionlist(actions, options(), SafetyCheckerFake())

    # Then
    assert result == AcceptedActionList(actions, False)


def test_no_save_bypasses_save_requirement_and_forced_overwrite() -> None:
    # Given
    action = ActionFake("image", forced=True)

    # When
    result = validate_actionlist(
        (action,),
        options(require_save_action=False),
        SafetyCheckerFake(),
    )

    # Then
    assert result == AcceptedActionList((action,), False)


def test_missing_final_save_requests_save_with_enabled_actions() -> None:
    # Given
    enabled = ActionFake("enabled")
    disabled = ActionFake("disabled", enabled=False)

    # When
    result = validate_actionlist((enabled, disabled), options(), SafetyCheckerFake())

    # Then
    assert result == SaveActionRequired((enabled,))


def test_forced_overwrite_comes_only_from_final_enabled_action() -> None:
    # Given
    first = ActionFake("first", forced=True)
    final = ActionFake("final", forced=True, valid_last=True)
    last = ActionFake("last", valid_last=True)

    # When
    forced = validate_actionlist((first, final), options(), SafetyCheckerFake())
    not_forced = validate_actionlist(
        (final, last),
        options(),
        SafetyCheckerFake(),
    )

    # Then
    assert forced == AcceptedActionList((first, final), True)
    assert not_forced == AcceptedActionList((final, last), False)


def test_disabled_safety_mode_does_not_call_checker() -> None:
    # Given
    action = ActionFake("terminal", valid_last=True)
    safety = SafetyCheckerFake("would reject")

    # When
    result = validate_actionlist(
        (action,),
        options(safe_mode=False),
        safety,
    )

    # Then
    assert result == AcceptedActionList((action,), False)
    assert safety.received == []
