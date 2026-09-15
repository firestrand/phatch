from __future__ import annotations

from pathlib import Path

import wx
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.pyWx.preview_panel import PreviewPanel
from phatch.pyWx.preview_runner import PreviewCallback, PreviewJobRunner
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import PreviewDependencies, PreviewRequest
from tests.unit.pywx.native_popup_support import wait_until


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


class CapturingRunner(PreviewJobRunner):
    def __init__(self) -> None:
        self.request: PreviewRequest | None = None
        self.callback: PreviewCallback | None = None

    def submit(
        self,
        request: PreviewRequest,
        dependencies: PreviewDependencies,
        callback: PreviewCallback,
    ) -> int:
        self.request = request
        self.callback = callback
        return 1

    def cancel(self) -> None:
        return None

    def close(self) -> None:
        return None


class ConfirmationDialog:
    result = wx.ID_CANCEL
    selections: tuple[int, ...] = ()
    shown_choices: tuple[str, ...] = ()
    destroyed = False

    def __init__(
        self,
        parent: wx.Window,
        message: str,
        caption: str,
        choices: tuple[str, ...],
    ) -> None:
        del parent, message, caption
        type(self).shown_choices = choices
        type(self).destroyed = False

    def ShowModal(self) -> int:
        return type(self).result

    def GetSelections(self) -> tuple[int, ...]:
        return type(self).selections

    def Destroy(self) -> None:
        type(self).destroyed = True


def _dependencies(tmp_path: Path) -> PreviewDependencies:
    resources = tmp_path / "resources"
    resources.mkdir(exist_ok=True)
    return PreviewDependencies(
        lambda: FixtureCatalog(),
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )


def _image(path: Path, color: str) -> Path:
    with Image.new("RGBA", (16, 12), color) as image:
        image.save(path)
    return path


def _panel(
    native_frame: wx.Frame,
    tmp_path: Path,
    document: ActionDocument,
    runner: PreviewJobRunner | None = None,
) -> PreviewPanel:
    panel = PreviewPanel(
        native_frame,
        lambda: document,
        _dependencies(tmp_path),
        runner=runner,
        read_dialog_factory=ConfirmationDialog,
    )
    panel.Show()
    panel.set_source(_image(tmp_path / "source.png", "navy"))
    return panel


def test_imported_external_read_defaults_to_cancel_without_submission(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    mark = _image(tmp_path / "private-mark.png", "red")
    document = ActionDocument.from_values("", (("watermark", (("mark", str(mark)),)),))
    runner = CapturingRunner()
    ConfirmationDialog.result = wx.ID_CANCEL
    ConfirmationDialog.selections = ()
    panel = _panel(native_frame, tmp_path, document, runner)

    panel.on_refresh()

    assert runner.request is None
    assert panel.refresh.IsEnabled()
    assert not panel.cancel.IsEnabled()
    assert ConfirmationDialog.destroyed
    panel.on_close()


def test_confirmed_external_read_is_the_only_selected_file(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    mark = _image(tmp_path / "picked-mark.png", "red")
    document = ActionDocument.from_values("", (("watermark", (("mark", str(mark)),)),))
    runner = CapturingRunner()
    ConfirmationDialog.result = wx.ID_OK
    ConfirmationDialog.selections = (0,)
    panel = _panel(native_frame, tmp_path, document, runner)

    panel.on_refresh()

    assert runner.request is not None
    assert runner.request.selected_files == (mark.resolve(),)
    assert "watermark.mark" in ConfirmationDialog.shown_choices[0]
    assert str(mark.parent) not in ConfirmationDialog.shown_choices[0]
    panel.on_close()


def test_confirmation_requires_every_external_read_selection(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    mark = _image(tmp_path / "unselected-mark.png", "red")
    document = ActionDocument.from_values("", (("watermark", (("mark", str(mark)),)),))
    runner = CapturingRunner()
    ConfirmationDialog.result = wx.ID_OK
    ConfirmationDialog.selections = ()
    panel = _panel(native_frame, tmp_path, document, runner)

    panel.on_refresh()

    assert runner.request is None
    assert ConfirmationDialog.destroyed
    panel.on_close()


def test_packaged_read_bypasses_confirmation(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    packaged = tmp_path / "resources" / "data" / "masks" / "daisy.png"
    packaged.parent.mkdir(parents=True)
    packaged.write_bytes(b"packaged")
    document = ActionDocument.from_values("", (("mask", (("mask", "Daisy"),)),))
    runner = CapturingRunner()
    ConfirmationDialog.shown_choices = ()
    panel = _panel(native_frame, tmp_path, document, runner)

    panel.on_refresh()

    assert runner.request is not None
    assert runner.request.selected_files == ()
    assert ConfirmationDialog.shown_choices == ()
    panel.on_close()


def test_confirmed_missing_read_surfaces_admission_error_and_returns_idle(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    missing = tmp_path / "missing-watermark.png"
    document = ActionDocument.from_values(
        "", (("watermark", (("mark", str(missing)),)),)
    )
    ConfirmationDialog.result = wx.ID_OK
    ConfirmationDialog.selections = (0,)
    panel = _panel(native_frame, tmp_path, document)

    panel.on_refresh()
    wait_until(
        lambda: "unavailable" in panel.status.GetLabel().casefold(), timeout_ms=5000
    )

    assert panel.refresh.IsEnabled()
    assert not panel.cancel.IsEnabled()
    panel.on_close()


def test_confirmed_custom_watermark_completes_real_preview(
    native_frame: wx.Frame, tmp_path: Path
) -> None:
    mark = _image(tmp_path / "custom-watermark.png", "red")
    document = ActionDocument.from_values("", (("watermark", (("mark", str(mark)),)),))
    ConfirmationDialog.result = wx.ID_OK
    ConfirmationDialog.selections = (0,)
    panel = _panel(native_frame, tmp_path, document)

    panel.on_refresh()
    wait_until(lambda: panel.status.GetLabel() == "Preview ready.", timeout_ms=5000)

    assert panel.result.GetBitmap().IsOk()
    assert "undeclared" not in panel.status.GetLabel().casefold()
    panel.on_close()
