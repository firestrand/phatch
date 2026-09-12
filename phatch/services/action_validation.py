from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeAlias

from phatch.core.execution_ports import Action
from phatch.core.execution_types import ExecutionOptions


class ActionSafetyChecker(Protocol):
    def __call__(self, actions: tuple[Action, ...]) -> str: ...


class ActionListRejectionReason(StrEnum):
    EMPTY = "empty"
    UNSAFE = "unsafe"
    ALL_DISABLED = "all_disabled"


@dataclass(frozen=True, slots=True)
class AcceptedActionList:
    enabled_actions: tuple[Action, ...]
    overwrite_existing_forced: bool


@dataclass(frozen=True, slots=True)
class RejectedActionList:
    reason: ActionListRejectionReason
    diagnostic: str = ""


@dataclass(frozen=True, slots=True)
class SaveActionRequired:
    enabled_actions: tuple[Action, ...]


ActionListValidationResult: TypeAlias = (
    AcceptedActionList | RejectedActionList | SaveActionRequired
)


def validate_actionlist(
    actions: tuple[Action, ...],
    options: ExecutionOptions,
    safety_checker: ActionSafetyChecker,
) -> ActionListValidationResult:
    if not actions:
        return RejectedActionList(ActionListRejectionReason.EMPTY)

    if options.safe_mode:
        diagnostic = safety_checker(actions)
        if diagnostic:
            return RejectedActionList(
                ActionListRejectionReason.UNSAFE,
                diagnostic=diagnostic,
            )

    enabled_actions = tuple(action for action in actions if action.is_enabled())
    if not enabled_actions:
        return RejectedActionList(ActionListRejectionReason.ALL_DISABLED)

    final_action = enabled_actions[-1]
    is_file_only = all("file" in action.tags for action in enabled_actions)
    if options.require_save_action and not (final_action.valid_last or is_file_only):
        return SaveActionRequired(enabled_actions)

    overwrite_existing_forced = (
        options.require_save_action
        and final_action.is_overwrite_existing_images_forced()
    )
    return AcceptedActionList(enabled_actions, overwrite_existing_forced)
