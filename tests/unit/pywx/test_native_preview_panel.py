from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
import wx
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.pyWx.preview_panel import PreviewPanel
from phatch.pyWx.preview_runner import PreviewRunner
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewImagePayload,
    PreviewWorkerCancelled,
    PreviewWorkerFailure,
    PreviewWorkerSuccess,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_popup_support"]


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


class CapturingRunner(PreviewRunner):
    def __init__(self) -> None:
        self.callback = None
        self.cancel_calls = 0
        self.closed = False

    def submit(self, request, dependencies, callback) -> int:
        self.callback = callback
        return 7

    def cancel(self) -> None:
        self.cancel_calls += 1

    def close(self) -> None:
        self.closed = True


class SequencedRunner(CapturingRunner):
    def __init__(self) -> None:
        super().__init__()
        self.callbacks = {}
        self._next_generation = 0

    def submit(self, request, dependencies, callback) -> int:
        self._next_generation += 1
        self.callbacks[self._next_generation] = callback
        return self._next_generation


def _dependencies(tmp_path: Path) -> PreviewDependencies:
    resources = tmp_path / "resources"
    resources.mkdir()
    return PreviewDependencies(
        lambda: FixtureCatalog(),
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )


def _source(tmp_path: Path, name: str = "样本 image.png") -> Path:
    path = tmp_path / name
    with Image.new("RGB", (12, 8), "navy") as image:
        image.save(path)
    return path


def _payload() -> PreviewImagePayload:
    output = BytesIO()
    with Image.new("RGB", (6, 4), "orange") as image:
        image.save(output, format="PNG")
    return PreviewImagePayload(output.getvalue(), 6, 4, "RGB", "PNG")


def _panel(
    native_frame: wx.Frame,
    tmp_path: Path,
    runner: CapturingRunner,
    file_dialog_class: type[wx.FileDialog] = wx.FileDialog,
):
    document = ActionDocument.from_values(
        "",
        (("scale", ()), ("save", (("as", "PNG"),))),
    )
    panel = PreviewPanel(
        native_frame,
        lambda: document,
        _dependencies(tmp_path),
        runner=runner,
        file_dialog_class=file_dialog_class,
    )
    panel.Show()
    wx.Yield()
    return panel


def test_refresh_presents_dimensions_format_and_save_disclaimer(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path))

    panel.on_refresh()
    assert not panel.refresh.IsEnabled()
    assert panel.cancel.IsEnabled()
    assert runner.callback is not None
    runner.callback(7, PreviewWorkerSuccess("preview-7", _payload(), 4321))

    assert panel.refresh.IsEnabled()
    assert panel.original.GetBitmap().IsOk()
    assert panel.result.GetBitmap().IsOk()
    assert "12 x 8" in panel.details.GetLabel()
    assert "6 x 4" in panel.details.GetLabel()
    assert "PNG" in panel.details.GetLabel()
    assert "no output file is saved" in panel.details.GetLabel()
    assert "Save action is omitted" in panel.details.GetLabel()
    panel.on_close()


@pytest.mark.parametrize(
    "result",
    [
        PreviewAdmissionError(
            PreviewErrorCode.BLOCKED_ACTION,
            "external process/temp output",
            "blender",
        ),
        PreviewWorkerFailure(
            "preview-7",
            PreviewErrorCode.WORKER_TIMEOUT,
            "preview deadline exceeded",
            4321,
        ),
        PreviewWorkerCancelled("preview-7", PreviewErrorCode.WORKER_CANCELLED, 4321),
    ],
)
def test_terminal_states_are_actionable(
    native_frame: wx.Frame, tmp_path: Path, result
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path))
    panel.on_refresh()
    assert runner.callback is not None

    runner.callback(7, result)

    assert panel.refresh.IsEnabled()
    assert any(
        token in panel.status.GetLabel().casefold()
        for token in ("unavailable", "failed", "cancelled")
    )
    panel.on_close()


def test_edit_invalidation_cancels_and_discards_bitmaps(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path))
    panel.on_refresh()
    assert runner.callback is not None
    runner.callback(7, PreviewWorkerSuccess("preview-7", _payload(), 4321))

    panel.mark_stale()

    assert runner.cancel_calls >= 2
    assert not panel.original.GetBitmap().IsOk()
    assert not panel.result.GetBitmap().IsOk()
    assert "stale" in panel.status.GetLabel().casefold()
    panel.on_close()
    assert runner.closed


def test_refresh_without_sample_does_not_start_work(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)

    panel.on_refresh()

    assert runner.callback is None
    assert "first" in panel.status.GetLabel().casefold()
    panel.on_close()


def test_cancelled_old_refresh_does_not_overwrite_newer_busy_or_ready_state(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = SequencedRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path))
    panel.on_refresh()
    first_callback = runner.callbacks[1]

    panel.on_refresh()
    first_callback(
        1,
        PreviewWorkerCancelled("preview-1", PreviewErrorCode.WORKER_CANCELLED, 1),
    )

    assert panel.status.GetLabel() == "Building preview..."
    assert not panel.refresh.IsEnabled()
    runner.callbacks[2](2, PreviewWorkerSuccess("preview-2", _payload(), 2))
    assert panel.status.GetLabel() == "Preview ready."
    panel.on_close()


def test_stale_invalidation_ignores_cancelled_cleanup_completion(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = SequencedRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path))
    panel.on_refresh()
    callback = runner.callbacks[1]

    panel.mark_stale()
    callback(
        1,
        PreviewWorkerCancelled("preview-1", PreviewErrorCode.WORKER_CANCELLED, 1),
    )

    assert "stale" in panel.status.GetLabel().casefold()
    assert panel.refresh.IsEnabled()
    panel.on_close()
