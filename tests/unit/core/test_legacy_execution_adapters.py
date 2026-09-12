from pathlib import Path

import pytest

from phatch.core import api
from phatch.core.execution_types import (
    DiscoveredFile,
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOptions,
    ExecutionOutcome,
    ExecutionPosition,
    ExecutionRequest,
    ExecutionResult,
    FileResult,
    IssueSeverity,
    IssueStage,
    ProgressDecision,
)
from phatch.services.legacy_actions import (
    LegacyActionAdapter,
    LegacyActionDependencies,
)
from phatch.services.legacy_execution import (
    LegacyExecutionContext,
    LegacyInteraction,
    LegacyIssueRecorder,
    LegacyProgress,
    LegacyValidator,
    _present_completion,
    _progress_decision,
    _setting_bool,
    _setting_int,
    _setting_strings,
)
from phatch.services.legacy_photos import (
    LegacyPhotoAccess,
    LegacyPhotoAdapter,
    LegacyPhotoState,
)
from phatch.services.legacy_types import (
    LegacyActionObject,
    LegacyImage,
    LegacyPhotoObject,
    translate,
)


class ActionFake:
    label = "Action"
    tags = ("file",)
    metadata = ("filename",)
    valid_last = True

    def __init__(self, *, error=False):
        self.error = error

    def _get_fields(self):
        return {}

    def is_enabled(self):
        return True

    def is_overwrite_existing_images_forced(self):
        return False

    def init(self):
        if self.error:
            raise ValueError("init")

    def is_done(self, photo):
        return True

    def apply(self, photo, settings, cache):
        if self.error:
            raise ValueError("apply")
        return photo

    def dump(self):
        return {}


class InteractionFake:
    def __init__(self):
        self.recorded = []

    def record_execution_error(
        self,
        photo: LegacyPhotoObject | None,
        issue: ExecutionIssue,
        action: LegacyActionObject | None,
        *,
        can_continue: bool,
    ) -> None:
        self.recorded.append((photo, issue, action, can_continue))


class ImageFake:
    def copy(self):
        return ImageFake()


class LayerFake:
    def __init__(self):
        self.image: LegacyImage = ImageFake()


class InfoFake:
    def __init__(self):
        self.values = {}

    def __getitem__(self, key):
        return self.values[key]

    def set(self, key, value):
        self.values[key] = value


class PhotoFake:
    def __init__(self, reports=None):
        self.info = InfoFake()
        self.layer = LayerFake()
        self.report_files = reports or []
        self.closed = False

    def get_layer(self):
        return self.layer

    def get_log(self):
        return ""

    def clear_log(self):
        return None

    def close(self):
        self.closed = True


def settings(**overrides):
    values = {
        "check_images_first": False,
        "extensions": ["png"],
        "recursive": False,
        "repeat": 2,
        "overwrite_existing_images": False,
        "overwrite_existing_images_forced": False,
        "no_save": False,
        "stop_for_errors": True,
        "always_show_status_dialog": False,
    }
    values.update(overrides)
    return values


def test_action_and_photo_adapters_cover_legacy_protocols(monkeypatch):
    raw = ActionFake()
    action = LegacyActionAdapter(raw)
    assert (action.label, action.tags, action.metadata, action.valid_last) == (
        "Action",
        ("file",),
        ("filename",),
        True,
    )
    assert action.is_enabled()
    assert not action.is_overwrite_existing_images_forced()

    interaction = InteractionFake()
    run = LegacyActionDependencies({}, interaction, (raw,)).begin_run(
        ExecutionOptions(())
    )
    monkeypatch.setattr(api, "get_vars", lambda actions: ["filename"])
    monkeypatch.setattr(api, "assert_safe", lambda actions: "")
    assert run.required_variables((action,)) == ("filename",)
    assert run.safety_issue((action,)) is None
    assert run.initialize(action) is None
    assert run.initialize(action) is None

    source = DiscoveredFile(Path("source.png"))
    state = LegacyPhotoState()
    photo = PhotoFake(
        [
            {"path": "one.png"},
            {
                "path": "two.png",
                "source": "source.png",
                "width": 2,
                "height": 3,
                "mode": "RGB",
            },
        ]
    )
    adapter = LegacyPhotoAdapter(source, photo, state)
    adapter.set_position(ExecutionPosition(1, 2, 3))
    original_image = photo.get_layer().image
    adapter.prepare_repeat_image(1, 3)
    assert photo.get_layer().image is not original_image
    adapter.prepare_repeat_image(2, 3)
    assert photo.get_layer().image is original_image
    assert len(adapter.reports()) == 2
    adapter.close()
    assert photo.closed
    assert run.is_done(action, adapter)
    monkeypatch.setattr(api, "flush_log", lambda *args: None)
    assert run.apply(action, adapter).succeeded


def test_action_adapter_reports_safety_initialization_and_apply_errors(monkeypatch):
    raw = ActionFake(error=True)
    action = LegacyActionAdapter(raw)
    interaction = InteractionFake()
    run = LegacyActionDependencies({}, interaction, (raw,)).begin_run(
        ExecutionOptions(())
    )
    monkeypatch.setattr(api, "assert_safe", lambda actions: "unsafe")
    monkeypatch.setattr(api, "flush_log", lambda *args: None)
    assert run.safety_issue((action,)) is not None
    assert run.initialize(action) is not None
    photo = LegacyPhotoAdapter(
        DiscoveredFile(Path("source.png")), PhotoFake(), LegacyPhotoState()
    )
    assert not run.apply(action, photo).succeeded
    assert interaction.recorded


def test_photo_access_verification_and_open_paths(monkeypatch):
    source = DiscoveredFile(Path("source.png"))
    info: dict[str, object] = {"path": "source.png"}
    state = LegacyPhotoState()
    state.add(source, info)
    interaction = InteractionFake()
    access = LegacyPhotoAccess(state, interaction)
    monkeypatch.setattr(
        api.send, "progress_update_filename", lambda result, *args: None
    )
    monkeypatch.setattr(
        api.openImage,
        "verify_image",
        lambda value, valid, invalid: valid.append(value),
    )
    assert access.verify(source)

    state = LegacyPhotoState()
    state.add(source, info)
    access = LegacyPhotoAccess(state, interaction)
    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, *args: result.update(keepgoing=False),
    )
    assert not access.verify(source)
    assert state.verification_cancelled

    state = LegacyPhotoState()
    state.add(source, info)
    access = LegacyPhotoAccess(state, interaction)
    monkeypatch.setattr(api.pil, "Photo", lambda *args: PhotoFake())
    assert isinstance(access.open(source, ()), LegacyPhotoAdapter)

    state.add(source, info)
    monkeypatch.setattr(
        api.pil, "Photo", lambda *args: (_ for _ in ()).throw(OSError("bad"))
    )
    monkeypatch.setattr(api, "exception_to_unicode", str)
    assert isinstance(access.open(source, ()), ExecutionIssue)


def test_interaction_progress_and_setting_branches(monkeypatch):
    raw = ActionFake()
    adapter = LegacyActionAdapter(raw)
    context = LegacyExecutionContext(
        (adapter,), (raw,), settings(check_images_first=True), ["source.png"], False
    )
    interaction = LegacyInteraction(context)
    calls = []
    monkeypatch.setattr(
        api, "get_paths_and_settings", lambda *args, **kwargs: ["source.png"]
    )
    monkeypatch.setattr(
        api.send, "frame_show_progress", lambda **kwargs: calls.append(kwargs)
    )
    request = ExecutionRequest((adapter,), ExecutionOptions(("png",)))
    selection = interaction.select_execution(request)
    assert selection is not None and calls
    monkeypatch.setattr(api, "get_paths_and_settings", lambda *args, **kwargs: [])
    assert interaction.select_execution(request) is None

    monkeypatch.setattr(
        api.send, "frame_show_error", lambda message: calls.append(message)
    )
    for message in (
        "The action list is empty.",
        "There is no enabled action.",
        "unsafe",
    ):
        interaction.present_issue(
            ExecutionIssue(IssueStage.ACTION_VALIDATION, IssueSeverity.ERROR, message)
        )
    interaction.present_issue(
        ExecutionIssue(
            IssueStage.ACTION_INITIALIZATION,
            IssueSeverity.ERROR,
            "bad",
            action_label="Action",
        )
    )
    monkeypatch.setattr(
        api.send, "frame_append_save_action", lambda actions: calls.append(actions)
    )
    interaction.request_save_action((adapter,))

    context.photo_state.invalid_infos.append({"path": "bad"})
    monkeypatch.setattr(api.send, "progress_close", lambda: calls.append("close"))
    monkeypatch.setattr(
        api.send,
        "frame_show_files_message",
        lambda result, **kwargs: result.update(cancel=False),
    )
    assert interaction.confirm_invalid_files(())
    context.photo_state.valid_infos.append({"path": "ok"})
    monkeypatch.setattr(
        api.send,
        "frame_show_image_tree",
        lambda result, *args, **kwargs: result.update(answer=True),
    )
    assert interaction.confirm_valid_files(())

    progress = LegacyProgress()
    progress.start(1, 2)
    monkeypatch.setattr(
        api.send, "progress_update_filename", lambda result, *args: None
    )
    monkeypatch.setattr(
        api.send,
        "progress_update_index",
        lambda result, *args: result.update(keepgoing=False),
    )
    position = ExecutionPosition(0, 0, 0)
    assert (
        progress.file_started(DiscoveredFile(Path("a")), position)
        is ProgressDecision.CONTINUE
    )
    assert progress.action_started(position, 0) is ProgressDecision.CANCEL
    progress.close()

    assert _setting_bool({"x": True}, "x")
    assert _setting_int({"x": 2}, "x") == 2
    assert _setting_strings({"x": ["a"]}, "x") == ("a",)
    assert _progress_decision({}) is ProgressDecision.CONTINUE
    assert translate("text") == "text"
    for function, value in (
        (_setting_bool, 1),
        (_setting_int, True),
        (_setting_strings, "a"),
        (_setting_strings, [1]),
    ):
        with pytest.raises(TypeError):
            function({"x": value}, "x")


def test_legacy_error_and_completion_branches(monkeypatch):
    raw = ActionFake()
    adapter = LegacyActionAdapter(raw)
    context = LegacyExecutionContext(
        (adapter,), (raw,), settings(), ["source.png"], False
    )
    interaction = LegacyInteraction(context)
    request = ExecutionRequest((adapter,), ExecutionOptions(("png",)))

    monkeypatch.setattr(api, "check_actionlist", lambda actions, values: None)
    assert LegacyValidator(context).validate(request, object()) is not None
    context.validation_presented = True
    monkeypatch.setattr(
        api.send,
        "frame_show_error",
        lambda message: pytest.fail("validation was already presented"),
    )
    interaction.present_issue(
        ExecutionIssue(
            IssueStage.ACTION_VALIDATION,
            IssueSeverity.ERROR,
            "The action list is empty.",
        )
    )

    context.validation_presented = False
    context.photo_state.verification_cancelled = True
    assert not interaction.confirm_invalid_files(())
    context.photo_state.verification_cancelled = False
    context.photo_state.invalid_infos.clear()
    monkeypatch.setattr(api.send, "progress_close", lambda: None)
    assert interaction.confirm_invalid_files(())

    issue = ExecutionIssue(IssueStage.PHOTO_OPEN, IssueSeverity.ERROR, "bad")
    for state, expected in (
        (
            {"abort": True, "skip": False, "stop_for_errors": True},
            ExecutionDecision.ABORT,
        ),
        (
            {"abort": False, "skip": True, "stop_for_errors": False},
            ExecutionDecision.SKIP,
        ),
        (
            {"abort": False, "skip": False, "stop_for_errors": True},
            ExecutionDecision.CONTINUE,
        ),
    ):
        monkeypatch.setattr(
            api, "process_error", lambda *args, value=state: (None, value)
        )
        interaction.record_execution_error(None, issue, None, can_continue=False)
        assert interaction.decide_issue(issue, False).decision is expected

    recorder = LegacyIssueRecorder()
    monkeypatch.setattr(api, "init_error_log_file", lambda: None)
    recorder.begin()
    recorder.record(issue, 0)
    recorder.close()

    notices = []
    monkeypatch.setattr(
        api.send,
        "frame_show_notification",
        lambda message, report: notices.append(message),
    )
    monkeypatch.setattr(
        api.send,
        "frame_show_status",
        lambda message, **kwargs: notices.append(message),
    )
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (
            FileResult(Path("one"), ExecutionDecision.CONTINUE),
            FileResult(Path("two"), ExecutionDecision.CONTINUE),
        ),
    )
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 1, raising=False)
    _present_completion(result, context)
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 2)
    _present_completion(result, context)
    context.settings["always_show_status_dialog"] = True
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 0)
    _present_completion(result, context)
    assert notices
