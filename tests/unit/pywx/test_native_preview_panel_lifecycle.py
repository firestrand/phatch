from __future__ import annotations

import multiprocessing
from hashlib import sha256
from pathlib import Path

import pytest
import wx
from PIL import Image

from phatch.pyWx import preview_runner
from phatch.pyWx.preview_panel import PreviewPanel
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import (
    PreviewErrorCode,
    PreviewImagePayload,
    PreviewWorkerFailure,
    PreviewWorkerSuccess,
)
from tests.unit.pywx.native_popup_support import wait_until
from tests.unit.pywx.test_native_preview_panel import (
    CapturingRunner,
    _dependencies,
    _panel,
    _source,
)
from tests.usability_fixtures import pid_exists

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_popup_support"]


def test_start_oserror_reaches_terminal_idle_failure(
    native_frame: wx.Frame,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_start(specification, request_id):
        raise OSError("/Volumes/private-client/worker detail")

    monkeypatch.setattr(preview_runner, "start_preview", fail_start)
    panel = PreviewPanel(
        native_frame,
        lambda: ActionDocument.from_values("", ()),
        _dependencies(tmp_path),
    )
    panel.Show()
    panel.set_source(_source(tmp_path, "startup.png"))

    panel.on_refresh()
    wait_until(
        lambda: panel.status.GetLabel().startswith("Preview failed:"),
        timeout_ms=5000,
    )

    assert panel.choose.IsEnabled()
    assert panel.refresh.IsEnabled()
    assert not panel.cancel.IsEnabled()
    assert "/Volumes/private-client" not in panel.status.GetLabel()
    panel.on_close()


def test_real_spawned_preview_completes_and_leaves_no_worker(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    panel = PreviewPanel(
        native_frame,
        lambda: ActionDocument.from_values("", ()),
        _dependencies(tmp_path),
    )
    panel.Show()
    panel.set_source(_source(tmp_path, "spawn.png"))

    panel.on_refresh()
    wait_until(lambda: panel.status.GetLabel() == "Preview ready.", timeout_ms=5000)

    assert panel.result.GetBitmap().IsOk()
    panel.on_close()
    wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)


def test_close_during_real_spawned_preview_reaps_worker_and_preserves_source(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    source = tmp_path / "close during preview.png"
    Image.new("RGB", (4000, 2000), "navy").save(source)
    source_hash = sha256(source.read_bytes()).hexdigest()
    panel = PreviewPanel(
        native_frame,
        lambda: ActionDocument.from_values("", ()),
        _dependencies(tmp_path),
    )
    panel.Show()
    panel.set_source(source)

    panel.on_refresh()
    wait_until(lambda: bool(multiprocessing.active_children()), timeout_ms=5000)
    worker_pids = tuple(child.pid for child in multiprocessing.active_children())
    panel.on_close()
    wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)

    assert all(pid is not None and not pid_exists(pid) for pid in worker_pids)
    assert sha256(source.read_bytes()).hexdigest() == source_hash


def test_cancel_real_spawned_preview_reaches_idle_terminal_state(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    source = tmp_path / "cancel during preview.png"
    Image.new("RGB", (4000, 2000), "navy").save(source)
    panel = PreviewPanel(
        native_frame,
        lambda: ActionDocument.from_values("", ()),
        _dependencies(tmp_path),
    )
    panel.Show()
    panel.set_source(source)
    panel.refresh.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId, panel.refresh.GetId()))
    wait_until(lambda: bool(multiprocessing.active_children()), timeout_ms=5000)

    panel.cancel.Command(wx.CommandEvent(wx.EVT_BUTTON.typeId, panel.cancel.GetId()))

    wait_until(
        lambda: panel.status.GetLabel() == "Cancelling preview...", timeout_ms=1000
    )
    wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)
    wait_until(lambda: panel.status.GetLabel() == "Preview cancelled.", timeout_ms=5000)
    assert panel.choose.IsEnabled()
    assert panel.refresh.IsEnabled()
    assert not panel.cancel.IsEnabled()
    assert not panel.result.GetBitmap().IsOk()
    panel.on_close()


@pytest.mark.parametrize("result", [wx.ID_CANCEL, wx.ID_OK])
def test_choose_sample_always_destroys_dialog(
    native_frame: wx.Frame, tmp_path: Path, result: int
) -> None:
    source = _source(tmp_path, "chosen.png")

    class FileDialog(wx.FileDialog):
        destroyed = False

        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def ShowModal(self) -> int:
            return result

        def GetPath(self) -> str:
            return str(source)

        def Destroy(self) -> bool:
            FileDialog.destroyed = True
            return True

    panel = _panel(native_frame, tmp_path, CapturingRunner(), FileDialog)

    panel.on_choose()

    assert FileDialog.destroyed
    assert panel._source == (source if result == wx.ID_OK else None)
    panel.on_close()


def test_invalid_bitmap_is_ignored(native_frame: wx.Frame) -> None:
    control = wx.StaticBitmap(native_frame)
    assert not control.GetBitmap().IsOk()

    PreviewPanel._set_bitmap(control, wx.Image())

    assert not control.GetBitmap().IsOk()


def test_source_label_does_not_expose_private_path(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    panel = _panel(native_frame, tmp_path, CapturingRunner())

    panel.set_source(Path("/Volumes/private-client/input/source.png"))

    assert panel.source_label.GetLabel() == "source.png"
    panel.on_close()


def test_worker_failure_reason_is_redacted(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path, "worker-failure.png"))
    panel.on_refresh()

    assert runner.callback is not None
    runner.callback(
        panel._generation,
        PreviewWorkerFailure(
            "preview-1",
            PreviewErrorCode.SOURCE_CHANGED,
            f"preview input changed: {panel._source}",
            0,
        ),
    )

    assert str(tmp_path) not in panel.status.GetLabel()
    assert "<input>" in panel.status.GetLabel()
    panel.on_close()


def test_invalid_success_payload_becomes_bounded_terminal_failure(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    runner = CapturingRunner()
    panel = _panel(native_frame, tmp_path, runner)
    panel.set_source(_source(tmp_path, "invalid-result.png"))
    panel.on_refresh()

    assert runner.callback is not None
    runner.callback(
        panel._generation,
        PreviewWorkerSuccess(
            "preview-1",
            PreviewImagePayload(b"not-an-image", 1, 1, "RGB", "PNG"),
            0,
        ),
    )

    assert panel.status.GetLabel() == "Preview failed: The preview could not be shown."
    assert panel.choose.IsEnabled()
    assert panel.refresh.IsEnabled()
    assert not panel.cancel.IsEnabled()
    panel.on_close()
