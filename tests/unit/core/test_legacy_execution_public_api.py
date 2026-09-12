import io
from pathlib import Path

import pytest
from PIL import Image

from phatch.console import console
from phatch.core import api
from phatch.core.execution_types import (
    ExecutionOutcome,
    IssueStage,
    RecoveryConfiguration,
)
from phatch.services.action_list import ActionListService
from phatch.services.execution import ExecutionService
from phatch.services.execution_runner import ExecutionRunner
from tests.unit.core.test_execution_characterization_batch import batch_settings


class DisabledActionInitializedError(RuntimeError):
    pass


class ActionInitializationError(RuntimeError):
    pass


class Action:
    tags = ("file",)
    metadata = ()
    valid_last = False

    def __init__(self, label, enabled):
        self.label = label
        self.enabled = enabled

    def is_enabled(self):
        return self.enabled

    @staticmethod
    def is_overwrite_existing_images_forced():
        return False

    def init(self):
        if not self.enabled:
            raise DisabledActionInitializedError

    def is_done(self, photo):
        return self.label == "enabled"

    def _get_fields(self):
        return {}

    def apply(self, photo, settings, cache):
        return photo


class TrackingAction(Action):
    def __init__(self, label, initialized, applied):
        super().__init__(label, True)
        self.initialized = initialized
        self.applied = applied

    def init(self):
        self.initialized.append(self)

    def apply(self, photo, settings, cache):
        self.applied.append(self)
        return photo


class ReportingAction(Action):
    def __init__(self, reports):
        super().__init__("enabled", True)
        self.reports = reports

    def apply(self, photo, settings, cache):
        photo.report_files.extend(self.reports)
        return photo


class RotatingAction(Action):
    def __init__(self, source, output):
        super().__init__("enabled", True)
        self.source = source
        self.output = output

    def apply(self, photo, settings, cache):
        photo.get_layer().image.transpose(Image.Transpose.ROTATE_90).save(self.output)
        photo.report_files.append(
            {"source": str(self.source), "path": str(self.output)}
        )
        return photo


class FailingInitializationAction(Action):
    def init(self):
        raise ActionInitializationError("boom")


class RecoverableSaveAction(Action):
    def __init__(self, output: Path, interrupt_on_call: int | None = None):
        super().__init__("recoverable-save", True)
        self.output = output
        self.interrupt_on_call = interrupt_on_call
        self.calls = 0

    def dump(self):
        return {"label": self.label, "fields": {"outputs": 2}}

    def apply(self, photo, settings, cache):
        self.calls += 1
        if self.calls == self.interrupt_on_call:
            raise KeyboardInterrupt
        stem = Path(photo.info["path"]).stem
        photo.save(str(self.output / f"{stem}.png"), "PNG", False)
        photo.save(str(self.output / f"{stem}-copy.png"), "PNG", False)
        return photo


def test_legacy_entrypoint_initializes_and_runs_only_enabled_actions(
    monkeypatch, tmp_path
):
    _configure_real_execution(monkeypatch)
    initialized = []
    applied = []
    enabled = TrackingAction("enabled", initialized, applied)
    disabled = Action("disabled", False)
    monkeypatch.setattr(api, "check_actionlist", lambda actions, settings: [enabled])
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (4, 3)).save(image_path)

    api.apply_actions_to_photos(
        [enabled, disabled], batch_settings(no_save=True), [str(image_path)]
    )

    assert initialized == [enabled]
    assert applied == [enabled]


def test_legacy_entrypoint_returns_typed_reports_from_actual_outputs(
    monkeypatch, tmp_path
):
    _configure_real_execution(monkeypatch)
    results = []
    image_path = tmp_path / "photo.png"
    Image.new("RGB", (4, 3)).save(image_path)
    raw_report = {
        "source": str(image_path),
        "path": "output.jpg",
        "width": 4,
        "height": 3,
        "mode": "RGB",
    }
    raw_report_without_dimensions = {
        "source": str(image_path),
        "path": "thumbnail.jpg",
    }
    execute = ExecutionService.execute

    def observed_execute(service, request):
        result = execute(service, request)
        results.append(result)
        return result

    action = ReportingAction((raw_report, raw_report_without_dimensions))
    monkeypatch.setattr(ExecutionService, "execute", observed_execute)

    api.apply_actions_to_photos(
        [action], batch_settings(no_save=True), [str(image_path)]
    )

    assert results[0].report[0].source == image_path
    assert results[0].report[0].path == Path("output.jpg")
    assert results[0].report[0].width == 4
    assert results[0].report[1].path == Path("thumbnail.jpg")
    assert results[0].report[1].width is None
    assert len(results[0].report) == 2


def test_legacy_entrypoint_cancellation_stops_before_open(monkeypatch, tmp_path):
    _configure_real_execution(monkeypatch)
    results = []
    image_paths = [tmp_path / "first.png", tmp_path / "second.png"]
    for image_path in image_paths:
        Image.new("RGB", (4, 3)).save(image_path)
    execute = ExecutionService.execute

    def observed_execute(service, request):
        result = execute(service, request)
        results.append(result)
        return result

    monkeypatch.setattr(ExecutionService, "execute", observed_execute)
    monkeypatch.setattr(
        api.send,
        "progress_update_filename",
        lambda result, index, filename: result.update(keepgoing=False),
    )

    api.apply_actions_to_photos(
        [Action("enabled", True)],
        batch_settings(),
        [str(path) for path in image_paths],
    )

    assert results[0].files == ()
    assert results[0].outcome is ExecutionOutcome.CANCELLED


def test_public_entrypoint_runs_real_image_through_execution_runner(
    monkeypatch, tmp_path
):
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    Image.new("RGB", (4, 3), "red").save(source)
    action = RotatingAction(source, output)
    traversed = []
    run = ExecutionRunner.run

    monkeypatch.setattr(
        ExecutionRunner,
        "run",
        lambda runner, context, plan: (
            traversed.append(plan) or run(runner, context, plan)
        ),
    )
    _configure_real_execution(monkeypatch)

    api.apply_actions_to_photos(
        [action], batch_settings(no_save=True, overwrite=True), [str(source)]
    )

    assert len(traversed) == 1
    with Image.open(output) as image:
        assert image.size == (3, 4)


def test_public_entrypoint_reports_unreadable_photo_once_without_crashing(
    monkeypatch, tmp_path
):
    source = tmp_path / "broken.png"
    source.write_text("not an image")
    errors = _configure_real_execution(monkeypatch)

    api.apply_actions_to_photos(
        [Action("enabled", True)],
        batch_settings(no_save=True, overwrite=True),
        [str(source)],
    )

    assert len(errors) == 1


def test_public_entrypoint_presents_initialization_error_once(monkeypatch, tmp_path):
    source = tmp_path / "source.png"
    Image.new("RGB", (1, 1)).save(source)
    action = FailingInitializationAction("broken", True)
    errors = _configure_real_execution(monkeypatch)

    api.apply_actions_to_photos(
        [action], batch_settings(no_save=True, overwrite=True), [str(source)]
    )

    assert len(errors) == 1
    assert errors[0].count("boom") == 1


def test_console_frame_executes_real_runner(monkeypatch, tmp_path):
    source = tmp_path / "console-source.png"
    output = tmp_path / "console-output.png"
    Image.new("RGB", (4, 3), "red").save(source)
    action = RotatingAction(source, output)
    _configure_real_execution(monkeypatch)
    monkeypatch.setattr(console.Frame, "_pubsub", lambda self: None)
    monkeypatch.setattr(
        api, "open_actionlist", lambda path: ({"actions": [action]}, "")
    )
    settings = batch_settings(no_save=True, overwrite=True)
    settings.update(verbose=False, interactive=False)

    console.Frame("actions.phatch", [str(source)], settings, output=io.StringIO())

    with Image.open(output) as image:
        assert image.size == (3, 4)


def test_headless_action_controller_executes_real_runner(monkeypatch, tmp_path):
    source = tmp_path / "controller-source.png"
    output = tmp_path / "controller-output.png"
    Image.new("RGB", (4, 3), "red").save(source)
    _configure_real_execution(monkeypatch)

    ActionListService().execute(
        [RotatingAction(source, output)],
        batch_settings(no_save=True, overwrite=True),
        paths=[str(source)],
    )

    with Image.open(output) as image:
        assert image.size == (3, 4)


def test_public_recovery_resumes_real_multi_output_batch_after_interruption(
    monkeypatch, tmp_path
):
    _configure_real_execution(monkeypatch)
    sources = (tmp_path / "first.png", tmp_path / "second.png")
    for source in sources:
        Image.new("RGB", (3, 2), "red").save(source)
    output = tmp_path / "outputs"
    output.mkdir()
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    interrupted = RecoverableSaveAction(output, interrupt_on_call=2)

    with pytest.raises(KeyboardInterrupt):
        api.apply_actions_to_photos_with_recovery(
            [interrupted],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source) for source in sources],
        )

    resumed = RecoverableSaveAction(output)
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source) for source in sources],
    )

    assert resumed.calls == 1
    assert all((output / f"{source.stem}.png").is_file() for source in sources)
    assert all((output / f"{source.stem}-copy.png").is_file() for source in sources)


def test_public_recovery_reports_changed_output_before_reevaluation(
    monkeypatch, tmp_path
):
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    output = tmp_path / "output"
    output.mkdir()
    Image.new("RGB", (3, 2), "red").save(source)
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    observed = []
    execute = ExecutionService.execute

    def observed_execute(service, request):
        result = execute(service, request)
        observed.append(result)
        return result

    monkeypatch.setattr(ExecutionService, "execute", observed_execute)
    api.apply_actions_to_photos_with_recovery(
        [RecoverableSaveAction(output)],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )
    (output / "source.png").write_bytes(b"changed")
    resumed = RecoverableSaveAction(output)

    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )

    assert resumed.calls == 1
    assert observed[-1].issues[0].stage is IssueStage.RECOVERY
    assert observed[-1].issues[0].source == source


def _configure_real_execution(monkeypatch):
    errors = []
    monkeypatch.setattr(api, "init_error_log_file", lambda: None)
    monkeypatch.setattr(api, "log_error", lambda *args: None)
    monkeypatch.setattr(api.formField, "get_safe", lambda: False)
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)
    monkeypatch.setattr(
        api.send,
        "frame_show_progress_error",
        lambda result, message, ignore: (
            errors.append(message),
            result.update(answer="skip"),
        ),
    )
    monkeypatch.setattr(api.send, "frame_show_progress", lambda **kwargs: None)
    monkeypatch.setattr(
        api.send, "progress_update_filename", lambda result, *args: None
    )
    monkeypatch.setattr(api.send, "progress_update_index", lambda result, *args: None)
    monkeypatch.setattr(api.send, "progress_close", lambda: None)
    monkeypatch.setattr(
        api.send, "frame_show_notification", lambda message, report: None
    )
    monkeypatch.setattr(api, "ERROR_LOG_COUNTER", 0, raising=False)
    return errors
