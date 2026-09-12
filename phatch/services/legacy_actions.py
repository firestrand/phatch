from __future__ import annotations

import os
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from operator import mod
from pathlib import Path
from typing import Protocol

from phatch.core.execution_ports import Action, ActionRun, Photo
from phatch.core.execution_types import (
    ActionApplication,
    ExecutionIssue,
    ExecutionOptions,
    IssueSeverity,
    IssueStage,
)
from phatch.core.plugin_context import PluginContext
from phatch.lib.unicoding import ensure_unicode, exception_to_unicode
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyPhotoObject,
)
from phatch.services.legacy_types import (
    translate as _,
)


@dataclass(frozen=True, slots=True)
class LegacyActionAdapter:
    action: LegacyActionObject

    @property
    def label(self) -> str:
        return self.action.label

    @property
    def tags(self) -> tuple[str, ...]:
        return tuple(self.action.tags)

    @property
    def metadata(self) -> tuple[str, ...]:
        return tuple(self.action.metadata)

    @property
    def valid_last(self) -> bool:
        return self.action.valid_last

    def is_enabled(self) -> bool:
        return self.action.is_enabled()

    def is_overwrite_existing_images_forced(self) -> bool:
        return self.action.is_overwrite_existing_images_forced()


class LegacyErrorInteraction(Protocol):
    def record_execution_error(
        self,
        photo: LegacyPhotoObject | None,
        issue: ExecutionIssue,
        action: LegacyActionObject | None,
        *,
        can_continue: bool,
    ) -> None: ...


@dataclass(slots=True)
class LegacyActionRun:
    settings: object
    interaction: LegacyErrorInteraction
    originals: tuple[LegacyActionObject, ...]
    plugin_context: PluginContext | None = None
    cache: MutableMapping[str, object] = field(default_factory=dict)

    def required_variables(self, actions: tuple[Action, ...]) -> tuple[str, ...]:
        from phatch.core import api

        return tuple(api.get_vars([_legacy_action(action) for action in actions]))

    def safety_issue(self, actions: tuple[Action, ...]) -> ExecutionIssue | None:
        from phatch.core import api

        warning = api.assert_safe([_legacy_action(action) for action in actions])
        if not warning:
            return None
        return ExecutionIssue(
            IssueStage.ACTION_VALIDATION,
            IssueSeverity.ERROR,
            warning,
        )

    def initialize(self, action: Action) -> ExecutionIssue | None:
        legacy_action = _legacy_action(action)
        try:
            bind_context = getattr(legacy_action, "bind_plugin_context", None)
            if bind_context is not None and self.plugin_context is not None:
                bind_context(self.plugin_context)
            legacy_action.init()
        except Exception as error:
            return ExecutionIssue(
                IssueStage.ACTION_INITIALIZATION,
                IssueSeverity.ERROR,
                exception_to_unicode(error),
                action_label=legacy_action.label,
            )
        return None

    def is_done(self, action: Action, photo: Photo) -> bool:
        return _legacy_action(action).is_done(_legacy_photo(photo))

    def apply(self, action: Action, photo: Photo) -> ActionApplication:
        from phatch.core import api

        legacy_action = _legacy_action(action)
        legacy_photo = _legacy_photo(photo)
        try:
            updated = legacy_action.apply(legacy_photo, self.settings, self.cache)
            api.flush_log(updated, str(photo.source.path), legacy_action)
            return ActionApplication(photo, True)
        except Exception as error:
            api.flush_log(legacy_photo, str(photo.source.path), legacy_action)
            folder, image = os.path.split(ensure_unicode(str(photo.source.path)))
            translated = mod(
                _("Can not apply action %(a)s on image '%(i)s' in folder:"),
                {"a": _(legacy_action.label), "i": image},
            )
            message = f"{translated}\n{folder}\n\n{exception_to_unicode(error)}"
            issue = ExecutionIssue(
                IssueStage.ACTION_EXECUTION,
                IssueSeverity.ERROR,
                message,
                Path(photo.source.path),
                legacy_action.label,
            )
            self.interaction.record_execution_error(
                legacy_photo,
                issue,
                legacy_action,
                can_continue=True,
            )
            return ActionApplication(photo, False, (issue,))


@dataclass(frozen=True, slots=True)
class LegacyActionDependencies:
    settings: object
    interaction: LegacyErrorInteraction
    originals: tuple[LegacyActionObject, ...]
    plugin_context: PluginContext | None = None

    def begin_run(self, options: ExecutionOptions) -> ActionRun:
        return LegacyActionRun(
            self.settings, self.interaction, self.originals, self.plugin_context
        )


def _legacy_action(action: Action) -> LegacyActionObject:
    if not isinstance(action, LegacyActionAdapter):
        raise TypeError("legacy execution requires LegacyActionAdapter")
    return action.action


def _legacy_photo(photo: Photo) -> LegacyPhotoObject:
    from phatch.services.legacy_photos import LegacyPhotoAdapter

    if not isinstance(photo, LegacyPhotoAdapter):
        raise TypeError("legacy execution requires LegacyPhotoAdapter")
    return photo.photo
