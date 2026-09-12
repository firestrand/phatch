"""Service layer helpers for Phatch GUI and console applications."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .action_list import (
        ActionListError,
        ActionListLoadResult,
        ActionListService,
        IncompatibleActionListError,
        MissingRequiredActionError,
        UnsafeActionListError,
    )

__all__ = [
    "ActionListError",
    "ActionListLoadResult",
    "ActionListService",
    "IncompatibleActionListError",
    "MissingRequiredActionError",
    "UnsafeActionListError",
]


def __getattr__(
    name: str,
) -> type[
    ActionListError
    | ActionListLoadResult
    | ActionListService
    | IncompatibleActionListError
    | MissingRequiredActionError
    | UnsafeActionListError
]:
    from .action_list import (
        ActionListError,
        ActionListLoadResult,
        ActionListService,
        IncompatibleActionListError,
        MissingRequiredActionError,
        UnsafeActionListError,
    )

    exports = {
        "ActionListLoadResult": ActionListLoadResult,
        "ActionListService": ActionListService,
        "ActionListError": ActionListError,
        "IncompatibleActionListError": IncompatibleActionListError,
        "MissingRequiredActionError": MissingRequiredActionError,
        "UnsafeActionListError": UnsafeActionListError,
    }
    try:
        return exports[name]
    except KeyError as error:
        raise AttributeError(name) from error
