from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from operator import mod
from pathlib import Path
from typing import Protocol

from phatch.core.execution_ports import Action
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionRequest,
    ExecutionSelection,
    IssueResponse,
    IssueStage,
    ProgressDecision,
)
from phatch.services.legacy_actions import LegacyActionAdapter
from phatch.services.legacy_photos import LegacyPhotoState
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyPaths,
    LegacyPhotoObject,
    LegacySettings,
)
from phatch.services.legacy_types import (
    translate as _,
)


class LegacyInteractionContext(Protocol):
    settings: LegacySettings
    paths: LegacyPaths | None
    drop: bool
    photo_state: LegacyPhotoState
    responses: dict[ExecutionIssue, IssueResponse]
    error_state: dict[str, object]
    validation_presented: bool

    def options(self) -> ExecutionOptions: ...


@dataclass(slots=True)
class LegacyInteraction:
    context: LegacyInteractionContext

    def select_execution(self, request: ExecutionRequest) -> ExecutionSelection | None:
        from phatch.core import api

        paths = api.get_paths_and_settings(
            None if self.context.paths is None else list(self.context.paths),
            self.context.settings,
            drop=self.context.drop,
        )
        if not paths:
            return None
        if not isinstance(paths, (list, tuple)):
            raise TypeError("legacy execution paths must be a sequence")
        options = self.context.options()
        if options.verify_images:
            api.send.frame_show_progress(
                title=_("Checking images"),
                parent_max=len(paths),
                message=api.PROGRESS_MESSAGE,
            )
        return ExecutionSelection(tuple(Path(str(path)) for path in paths), options)

    def present_issue(self, issue: ExecutionIssue) -> None:
        from phatch.core import api

        if self.context.validation_presented:
            return
        if issue.stage is IssueStage.ACTION_INITIALIZATION:
            translated = mod(
                _("Can not apply action %(a)s:"),
                {"a": _(issue.action_label or "")},
            )
            api.send.frame_show_error(f"{translated}\n\n{issue.message}")
        elif issue.stage is IssueStage.ACTION_VALIDATION:
            self._present_validation_issue(issue)

    def _present_validation_issue(self, issue: ExecutionIssue) -> None:
        from phatch.core import api

        if issue.message == "The action list is empty.":
            message = f"{_('Nothing to do.')} {_('The action list is empty.')}"
        elif issue.message == "There is no enabled action.":
            message = f"{_('Nothing to do.')} {_('There is no action enabled.')}"
        else:
            message = (
                f"{api.ERROR_UNSAFE_ACTIONLIST_INTRO}\n\n{issue.message}\n"
                f"{api.ERROR_UNSAFE_ACTIONLIST_DISABLE_SAFE}"
            )
        api.send.frame_show_error(message)

    def request_save_action(self, actions: tuple[Action, ...]) -> None:
        from phatch.core import api

        api.send.frame_append_save_action(
            [
                action.action
                for action in actions
                if isinstance(action, LegacyActionAdapter)
            ]
        )

    def confirm_invalid_files(self, files: tuple[DiscoveredFile, ...]) -> bool:
        from phatch.core import api

        if self.context.photo_state.verification_cancelled:
            return False
        api.send.progress_close()
        if not self.context.photo_state.invalid_infos:
            return True
        result: dict[str, object] = {}
        api.send.frame_show_files_message(
            result,
            message=_("Phatch can not handle %d image(s):")
            % len(self.context.photo_state.invalid_infos),
            title=api.ct.FRAME_TITLE % ("", _("Invalid images")),
            files=self.context.photo_state.invalid_infos,
        )
        return not bool(result["cancel"])

    def confirm_valid_files(self, files: tuple[DiscoveredFile, ...]) -> bool:
        from phatch.core import api

        for index, info in enumerate(self.context.photo_state.valid_infos):
            info["index"] = index * _setting_int(self.context.settings, "repeat")
        result: dict[str, object] = {}
        api.send.frame_show_image_tree(
            result,
            self.context.photo_state.valid_infos,
            widths=(200, 40, 200, 200, 200, 200, 60),
            headers=api.TREE_HEADERS,
            ok_label=_("C&ontinue"),
            buttons=True,
        )
        return bool(result["answer"])

    def decide_issue(self, issue: ExecutionIssue, can_continue: bool) -> IssueResponse:
        return self.context.responses[issue]

    def record_execution_error(
        self,
        photo: LegacyPhotoObject | None,
        issue: ExecutionIssue,
        action: LegacyActionObject | None,
        *,
        can_continue: bool,
    ) -> None:
        from phatch.core import api

        _, state = api.process_error(
            photo,
            issue.message,
            str(issue.source or ""),
            action,
            self.context.error_state,
            can_continue,
        )
        if bool(state["abort"]):
            decision = ExecutionDecision.ABORT
        elif bool(state["skip"]):
            decision = ExecutionDecision.SKIP
        else:
            decision = ExecutionDecision.CONTINUE
        self.context.responses[issue] = IssueResponse(
            decision,
            bool(state["stop_for_errors"]),
        )


class LegacyProgress:
    __slots__ = ()

    def start(self, item_count: int, step_count: int) -> None:
        from phatch.core import api

        api.send.frame_show_progress(
            title=_("Executing action list"),
            parent_max=item_count,
            child_max=step_count,
            message=api.PROGRESS_MESSAGE,
        )

    def file_started(self, source: DiscoveredFile, position) -> ProgressDecision:
        from phatch.core import api

        result: dict[str, object] = {}
        api.send.progress_update_filename(result, position.item_index, str(source.path))
        return _progress_decision(result)

    def action_started(self, position, action_index: int) -> ProgressDecision:
        from phatch.core import api

        result: dict[str, object] = {}
        api.send.progress_update_index(result, position.item_index, action_index)
        return _progress_decision(result)

    def close(self) -> None:
        from phatch.core import api

        api.send.progress_close()


class LegacyIssueRecorder:
    __slots__ = ()

    def begin(self) -> None:
        from phatch.core import api

        api.init_error_log_file()

    def record(self, issue: ExecutionIssue, sequence: int) -> None:
        pass

    def close(self) -> None:
        pass


def _setting_int(settings: LegacySettings, key: str) -> int:
    value = settings[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be integer")
    return value


def _progress_decision(result: Mapping[str, object]) -> ProgressDecision:
    if result and not bool(result["keepgoing"]):
        return ProgressDecision.CANCEL
    return ProgressDecision.CONTINUE
