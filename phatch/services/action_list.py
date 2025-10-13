"""Service objects that encapsulate action list lifecycle operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

from phatch.core import api
from phatch.lib import formField


class ActionListError(Exception):
    """Base class for all action list related service errors."""


class MissingRequiredActionError(ActionListError):
    """Raised when an action list references a plugin that is not installed."""

    def __init__(self, original_exception: Exception):
        super().__init__(str(original_exception))
        self.original_exception = original_exception


class IncompatibleActionListError(ActionListError):
    """Raised when an action list file cannot be read because it is incompatible."""

    def __init__(self, filename: str, original_exception: Optional[Exception] = None):
        message = filename
        if original_exception:
            message = f"{filename}: {original_exception}"
        super().__init__(message)
        self.filename = filename
        self.original_exception = original_exception


class UnsafeActionListError(ActionListError):
    """Raised when unsafe actions are encountered while safe mode is active."""

    def __init__(self, warning: str):
        super().__init__(warning)
        self.warning = warning


@dataclass(frozen=True)
class ActionListLoadResult:
    """Container returned when an action list is loaded successfully."""

    data: Mapping[str, Any]
    warning: str
    invalid_labels: Sequence[str]

    @property
    def description(self) -> str:
        return self.data.get("description", "")

    @property
    def actions(self) -> Sequence[Any]:
        return self.data.get("actions", ())


class ActionListService:
    """Encapsulates load/save/execute behaviour for action lists."""

    def __init__(
        self,
        open_actionlist: Callable[[str], tuple[Mapping[str, Any], str]] = api.open_actionlist,
        save_actionlist: Callable[[str, Mapping[str, Any]], None] = api.save_actionlist,
        apply_actions_to_photos: Callable[..., None] = api.apply_actions_to_photos,
        safe_mode_checker: Callable[[], bool] = formField.get_safe,
    ) -> None:
        self._open_actionlist = open_actionlist
        self._save_actionlist = save_actionlist
        self._apply_actions_to_photos = apply_actions_to_photos
        self._safe_mode_checker = safe_mode_checker

    def load(self, filename: str) -> ActionListLoadResult:
        """Load an action list and return its data plus metadata.

        Raises:
            MissingRequiredActionError: when referenced actions are missing.
            IncompatibleActionListError: when the file cannot be parsed.
            UnsafeActionListError: when warnings are present and safe mode is on.
        """

        try:
            result = self._open_actionlist(filename)
            if result is None:
                raise ValueError("open_actionlist returned None (incompatible version)")
            data, warning = result
        except MissingRequiredActionError:
            raise
        except KeyError as exc:
            raise MissingRequiredActionError(exc) from exc
        except Exception as exc:  # noqa: BLE001 - we convert to a typed error
            raise IncompatibleActionListError(filename, exc) from exc

        invalid_labels = tuple(data.get("invalid labels", ()))
        warning = warning or ""

        if warning and self._safe_mode_checker():
            raise UnsafeActionListError(warning)

        return ActionListLoadResult(data=data, warning=warning, invalid_labels=invalid_labels)

    def save(self, filename: str, description: str, actions: Sequence[Any]) -> dict[str, Any]:
        """Persist an action list to disk and return the payload that was written."""

        payload: dict[str, Any] = {
            "description": description,
            "actions": actions,
        }
        self._save_actionlist(filename, payload)
        return payload

    def execute(
        self,
        actions: Iterable[Any],
        settings: Mapping[str, Any],
        update_callback: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> None:
        """Apply the action list to the provided inputs."""

        call_kwargs = dict(kwargs)
        if update_callback is not None and "update" not in call_kwargs:
            call_kwargs["update"] = update_callback
        self._apply_actions_to_photos(actions, settings, **call_kwargs)
