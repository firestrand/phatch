from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from phatch.core.execution_ports import Recovery
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionRequest,
    ExecutionResult,
    IssueResponse,
)
from phatch.lib.odict import ReadOnlyDict
from phatch.services.action_validation import (
    AcceptedActionList,
    ActionListRejectionReason,
    ActionListValidationResult,
    RejectedActionList,
)
from phatch.services.execution import (
    ExecutionService,
    ExecutionServices,
)
from phatch.services.execution_runner import ExecutionRunner, RunnerServices
from phatch.services.legacy_actions import (
    LegacyActionAdapter,
    LegacyActionDependencies,
)
from phatch.services.legacy_interaction import (
    LegacyInteraction,
    LegacyIssueRecorder,
    LegacyProgress,
)
from phatch.services.legacy_interaction import (
    _progress_decision as _progress_decision,
)
from phatch.services.legacy_interaction import (
    _setting_int as _setting_int,
)
from phatch.services.legacy_photos import LegacyPhotoAccess, LegacyPhotoState
from phatch.services.legacy_recovery_decision import LegacyRecoveryDecision
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyPaths,
    LegacySettings,
    UpdateCallback,
)


@dataclass(slots=True)
class LegacyExecutionContext:
    actions: tuple[LegacyActionAdapter, ...]
    originals: tuple[LegacyActionObject, ...]
    settings: LegacySettings
    paths: LegacyPaths | None
    drop: bool
    photo_state: LegacyPhotoState = field(default_factory=LegacyPhotoState)
    responses: dict[ExecutionIssue, IssueResponse] = field(default_factory=dict)
    error_state: dict[str, object] = field(init=False)
    validation_presented: bool = False

    def __post_init__(self) -> None:
        self.error_state = {
            "stop_for_errors": _setting_bool(self.settings, "stop_for_errors"),
            "last_answer": None,
        }

    def options(self) -> ExecutionOptions:
        return ExecutionOptions(
            _setting_strings(self.settings, "extensions"),
            recursive=_setting_bool(self.settings, "recursive"),
            prompt_on_issue=_setting_bool(self.settings, "stop_for_errors"),
            overwrite_existing=_setting_bool(
                self.settings, "overwrite_existing_images"
            ),
            require_save_action=not _setting_bool(self.settings, "no_save"),
            verify_images=_setting_bool(self.settings, "check_images_first"),
            always_show_status=_setting_bool(
                self.settings, "always_show_status_dialog"
            ),
            safe_mode=True,
            repeat=_setting_int(self.settings, "repeat"),
        )


@dataclass(slots=True)
class LegacyValidator:
    context: LegacyExecutionContext

    def validate(
        self,
        request: ExecutionRequest,
        action_run,
    ) -> ActionListValidationResult:
        from phatch.core import api

        checked = api.check_actionlist(
            list(self.context.originals), self.context.settings
        )
        if checked is None:
            self.context.validation_presented = True
            return RejectedActionList(ActionListRejectionReason.EMPTY)
        enabled_ids = {id(action) for action in checked}
        enabled = tuple(
            action
            for action in request.actions
            if isinstance(action, LegacyActionAdapter)
            and id(action.action) in enabled_ids
        )
        return AcceptedActionList(
            enabled,
            _setting_bool(self.context.settings, "overwrite_existing_images_forced"),
        )


@dataclass(slots=True)
class LegacyDiscovery:
    context: LegacyExecutionContext

    def discover(
        self,
        paths: tuple[Path, ...],
        extensions: tuple[str, ...],
        *,
        recursive: bool,
    ) -> tuple[DiscoveredFile, ...] | ExecutionIssue:
        from phatch.core import api

        variables = set(api.pil.BASE_VARS).union(api.get_vars(self.context.originals))
        if _setting_bool(self.context.settings, "check_images_first"):
            variables = api.TREE_VARS.union(variables)
        variables_file, variables_other = api.metadata.InfoFile.split_vars(
            list(variables)
        )
        info_file = api.metadata.InfoFile(vars=list(variables_file))
        infos = api.get_image_infos(
            [str(path) for path in paths], info_file, extensions, recursive
        )
        static = api.pil.split_vars_static_dynamic(variables_other)[0]
        self.context.photo_state.info_not_file = api.metadata.InfoExtract(vars=static)
        sources: list[DiscoveredFile] = []
        for info in infos:
            source = DiscoveredFile(
                Path(str(info["path"])),
                Path(str(info["root"])) if info.get("root") else None,
                int(info.get("folderindex", 0)),
            )
            self.context.photo_state.add(source, info)
            sources.append(source)
        return tuple(sources)


class MonotonicClock:
    __slots__ = ()

    def monotonic(self) -> float:
        return time.monotonic()


def apply_actions_to_photos(
    actions: Sequence[LegacyActionObject],
    settings: LegacySettings,
    paths: LegacyPaths | None = None,
    drop: bool = False,
    update: UpdateCallback | None = None,
) -> ExecutionResult:
    return _execute_actions_to_photos(actions, settings, paths, drop, update, None)


def _execute_actions_to_photos(
    actions: Sequence[LegacyActionObject],
    settings: LegacySettings,
    paths: LegacyPaths | None,
    drop: bool,
    update: UpdateCallback | None,
    recovery: Recovery | None,
) -> ExecutionResult:
    adapters = tuple(LegacyActionAdapter(action) for action in actions)
    context = LegacyExecutionContext(adapters, tuple(actions), settings, paths, drop)
    interaction = LegacyInteraction(context)
    recorder = LegacyIssueRecorder()
    photo_access = LegacyPhotoAccess(context.photo_state, interaction)
    progress = LegacyProgress()
    runner = ExecutionRunner(
        RunnerServices(
            interaction,
            progress,
            photo_access,
            recorder,
            LegacyRecoveryDecision(interaction),
        )
    )
    service = ExecutionService(
        ExecutionServices(
            LegacyDiscovery(context),
            LegacyActionDependencies(
                ReadOnlyDict(settings),
                interaction,
                tuple(actions),
            ),
            interaction,
            progress,
            photo_access,
            recorder,
            MonotonicClock(),
            runner,
            LegacyValidator(context),
            recovery,
        )
    )
    return service.execute(
        ExecutionRequest(adapters, context.options(), None, drop, update)
    )


def _setting_bool(settings: LegacySettings, key: str) -> bool:
    value = settings[key]
    if not isinstance(value, bool):
        raise TypeError(f"{key} must be boolean")
    return value


def _setting_strings(settings: LegacySettings, key: str) -> tuple[str, ...]:
    value = settings[key]
    if not isinstance(value, Sequence) or isinstance(value, str):
        raise TypeError(f"{key} must be a sequence")
    strings = tuple(item for item in value if isinstance(item, str))
    if len(strings) != len(value):
        raise TypeError(f"{key} must contain strings")
    return strings
