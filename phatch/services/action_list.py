"""Service objects that encapsulate action list lifecycle operations."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from phatch.core import api
from phatch.core.execution_ports import ActionRegistry
from phatch.core.execution_types import RecoveryConfiguration
from phatch.core.plugin_context import PluginContext
from phatch.lib import formField
from phatch.services.preflight import PreflightRequest, PreflightResult, PreflightService


class ActionListError(Exception):
    """Base class for all action list related service errors."""


class MissingRequiredActionError(ActionListError):
    """Raised when an action list references a plugin that is not installed."""

    def __init__(self, original_exception: Exception):
        super().__init__(str(original_exception))
        self.original_exception = original_exception


class IncompatibleActionListError(ActionListError):
    """Raised when an action list file cannot be read because it is incompatible."""

    def __init__(self, filename: str, original_exception: Exception | None = None):
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
        open_actionlist: Callable[..., tuple[Mapping[str, Any], str] | None] = (
            api.open_actionlist
        ),
        save_actionlist: Callable[[str, Mapping[str, Any]], None] = api.save_actionlist,
        apply_actions_to_photos: Callable[..., None] = api.apply_actions_to_photos,
        safe_mode_checker: Callable[[], bool] = formField.get_safe,
        *,
        registry: ActionRegistry | None = None,
        plugin_context: PluginContext | None = None,
        preflight: Callable[[PreflightRequest], PreflightResult] | None = None,
    ) -> None:
        self._open_actionlist = open_actionlist
        self._save_actionlist = save_actionlist
        self._apply_actions_to_photos = apply_actions_to_photos
        self._safe_mode_checker = safe_mode_checker
        self._registry = registry
        self._plugin_context = plugin_context
        self._preflight = preflight

    @property
    def registry(self) -> ActionRegistry | None:
        return self._registry

    def load(self, filename: str) -> ActionListLoadResult:
        """Load an action list and return its data plus metadata.

        Raises:
            MissingRequiredActionError: when referenced actions are missing.
            IncompatibleActionListError: when the file cannot be parsed.
            UnsafeActionListError: when warnings are present and safe mode is on.
        """

        try:
            if self._registry is None and self._plugin_context is None:
                result = self._open_actionlist(filename)
            elif self._registry is None:
                result = self._open_actionlist(
                    filename, plugin_context=self._plugin_context
                )
            else:
                result = self._open_actionlist(
                    filename,
                    registry=self._registry,
                    plugin_context=self._plugin_context,
                )
            if result is None:
                raise ValueError("open_actionlist returned None (incompatible version)")
            data, warning = result
        except MissingRequiredActionError:
            raise
        except KeyError as exc:
            raise MissingRequiredActionError(exc) from exc
        except Exception as exc:
            raise IncompatibleActionListError(filename, exc) from exc

        invalid_labels = tuple(data.get("invalid labels", ()))
        warning = warning or ""

        if warning and self._safe_mode_checker():
            raise UnsafeActionListError(warning)

        return ActionListLoadResult(
            data=data, warning=warning, invalid_labels=invalid_labels
        )

    def save(
        self, filename: str, description: str, actions: Sequence[Any]
    ) -> dict[str, Any]:
        """Persist an action list to disk and return the payload that was written."""

        payload: dict[str, Any] = {
            "description": description,
            "actions": actions,
        }
        self._save_actionlist(filename, payload)
        return payload

    def preflight(self, request: PreflightRequest) -> PreflightResult:
        if self._preflight is None:
            return PreflightService().build(request)
        return self._preflight(request)

    def execute(
        self,
        actions: Iterable[Any],
        settings: Mapping[str, Any],
        update_callback: Callable[[], None] | None = None,
        recovery: RecoveryConfiguration | None = None,
        **kwargs: Any,
    ) -> None:
        """Apply the action list to the provided inputs."""

        call_kwargs = dict(kwargs)
        if update_callback is not None and "update" not in call_kwargs:
            call_kwargs["update"] = update_callback
        if recovery is None:
            self._apply_actions_to_photos(actions, settings, **call_kwargs)
        else:
            api.apply_actions_to_photos_with_recovery(
                actions, settings, recovery, **call_kwargs
            )
