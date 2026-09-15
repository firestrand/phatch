from __future__ import annotations

import builtins
from collections.abc import Callable
from io import BytesIO
from pathlib import Path

import wx
from PIL import Image

from phatch.pyWx.preview_authorization import (
    PreviewReadAuthorizer,
    ReadDialogFactory,
    create_read_confirmation_dialog,
)
from phatch.pyWx.preview_runner import PreviewJobRunner, PreviewResult, PreviewRunner
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewRequest,
    PreviewWorkerCancelled,
    PreviewWorkerFailure,
    PreviewWorkerSuccess,
)
from phatch.services.report_privacy import privacy_for_paths, redact_text

_ = getattr(builtins, "_", lambda value: value)


class PreviewPanel(wx.Dialog):
    def __init__(
        self,
        parent: wx.Window,
        document_provider: Callable[[], ActionDocument],
        dependencies: PreviewDependencies,
        file_dialog_class: type[wx.FileDialog] = wx.FileDialog,
        runner: PreviewJobRunner | None = None,
        read_dialog_factory: ReadDialogFactory = create_read_confirmation_dialog,
    ) -> None:
        super().__init__(
            parent,
            title=_("Before and After Preview"),
            size=wx.Size(820, 560),
        )
        self._document_provider = document_provider
        self._dependencies = dependencies
        self._file_dialog_class = file_dialog_class
        self._runner = runner or PreviewRunner(wx.CallAfter)
        self._read_authorizer = PreviewReadAuthorizer(
            dependencies,
            read_dialog_factory,
        )
        self._privacy = privacy_for_paths()
        self._source: Path | None = None
        self._generation = 0
        self._build()
        self.Bind(wx.EVT_CLOSE, self.on_close)

    def _build(self) -> None:
        root = wx.BoxSizer(wx.VERTICAL)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        self.choose = wx.Button(self, label=_("Choose Sample..."))
        self.refresh = wx.Button(self, label=_("Refresh"))
        self.cancel = wx.Button(self, label=_("Cancel"))
        self.cancel.Disable()
        controls.Add(self.choose, 0, wx.RIGHT, 8)
        controls.Add(self.refresh, 0, wx.RIGHT, 8)
        controls.Add(self.cancel)
        root.Add(controls, 0, wx.ALL, 12)
        self.source_label = wx.StaticText(self, label=_("No sample selected"))
        self.source_label.Wrap(780)
        root.Add(self.source_label, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 12)
        images = wx.BoxSizer(wx.HORIZONTAL)
        self.original = self._image_column(images, _("Original"))
        self.result = self._image_column(images, _("Result"))
        root.Add(images, 1, wx.ALL | wx.EXPAND, 12)
        self.details = wx.StaticText(
            self,
            label=_("Preview only; no output file is saved."),
        )
        self.details.Wrap(780)
        root.Add(self.details, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 12)
        self.status = wx.StaticText(
            self, label=_("Choose a sample image, then Refresh.")
        )
        self.status.Wrap(780)
        root.Add(self.status, 0, wx.ALL | wx.EXPAND, 12)
        self.SetSizer(root)
        self.SetMinSize(wx.Size(540, 380))
        self.choose.Bind(wx.EVT_BUTTON, self.on_choose)
        self.refresh.Bind(wx.EVT_BUTTON, self.on_refresh)
        self.cancel.Bind(wx.EVT_BUTTON, self.on_cancel)
        self.Bind(wx.EVT_SIZE, self.on_size)

    def _image_column(self, owner: wx.BoxSizer, label: str) -> wx.StaticBitmap:
        column = wx.BoxSizer(wx.VERTICAL)
        heading = wx.StaticText(self, label=label)
        font = heading.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        heading.SetFont(font)
        bitmap = wx.StaticBitmap(self, bitmap=wx.BitmapBundle.FromBitmap(wx.NullBitmap))
        bitmap.SetMinSize(wx.Size(240, 240))
        column.Add(heading, 0, wx.BOTTOM, 6)
        column.Add(bitmap, 1, wx.EXPAND)
        owner.Add(column, 1, wx.RIGHT | wx.EXPAND, 10)
        return bitmap

    def on_choose(self, _event: wx.CommandEvent | None = None) -> None:
        dialog = self._file_dialog_class(
            self,
            message=_("Choose a sample image"),
            wildcard=_("Image files") + "|*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.tif;*.tiff",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        )
        try:
            if dialog.ShowModal() == wx.ID_OK:
                self.set_source(Path(dialog.GetPath()))
        finally:
            dialog.Destroy()

    def set_source(self, source: Path) -> None:
        self._source = source
        self._privacy = privacy_for_paths(inputs=(source,))
        self.source_label.SetLabel(source.name)
        self.source_label.Wrap(max(self.GetClientSize().width - 24, 200))
        self.mark_stale()

    def on_refresh(self, _event: wx.CommandEvent | None = None) -> None:
        if self._source is None:
            self.status.SetLabel(_("Choose a sample image first."))
            return
        document = self._document_provider()
        selected_files = self._read_authorizer.authorize(self, document)
        if selected_files is None:
            self._set_busy(False)
            self.status.SetLabel(_("Preview cancelled."))
            return
        self._privacy = self._privacy.with_paths(inputs=selected_files)
        request = PreviewRequest(document, self._source, selected_files)
        self._set_busy(True)
        self.status.SetLabel(_("Building preview..."))
        self._generation = self._runner.submit(
            request, self._dependencies, self._on_result
        )

    def on_cancel(self, _event: wx.CommandEvent | None = None) -> None:
        self._runner.cancel()
        self.cancel.Disable()
        self.status.SetLabel(_("Cancelling preview..."))

    def mark_stale(self) -> None:
        self._runner.cancel()
        self._generation += 1
        self._clear_bitmaps()
        self._set_busy(False)
        self.status.SetLabel(_("Preview is stale. Select Refresh to update it."))

    def _on_result(self, generation: int, result: PreviewResult) -> None:
        if generation != self._generation or self.IsBeingDeleted():
            return
        self._set_busy(False)
        match result:
            case PreviewWorkerSuccess(image=image):
                source = self._source
                if source is None:
                    self.status.SetLabel(
                        _("Preview failed: The preview could not be shown.")
                    )
                    return
                try:
                    self._set_bitmap(self.original, wx.Image(str(source)))
                    self._set_bitmap(self.result, self._decode_result(image.data))
                    original_size = self._read_size(source)
                    format_name = self._requested_format(self._document_provider())
                    save_note = self._save_note(self._document_provider())
                    self._set_details(
                        _(
                            "Original: %(original)s | Result: %(result)s | "
                            "Requested format: %(format)s. Preview only; no output "
                            "file is saved. %(save)s"
                        )
                        % {
                            "original": f"{original_size[0]} x {original_size[1]}",
                            "result": f"{image.width} x {image.height}",
                            "format": format_name,
                            "save": save_note,
                        }
                    )
                except Exception:
                    self.status.SetLabel(
                        _("Preview failed: The preview could not be shown.")
                    )
                    return
                self.status.SetLabel(_("Preview ready."))
            case PreviewAdmissionError() as error:
                self.status.SetLabel(
                    _("Preview unavailable: %(reason)s")
                    % {"reason": redact_text(str(error), self._privacy)}
                )
            case PreviewWorkerFailure(reason=reason):
                self.status.SetLabel(
                    _("Preview failed: %(reason)s")
                    % {"reason": redact_text(reason, self._privacy)}
                )
            case PreviewWorkerCancelled():
                self.status.SetLabel(_("Preview cancelled."))

    @staticmethod
    def _decode_result(data: bytes) -> wx.Image:
        with Image.open(BytesIO(data)) as source:
            rgba = source.convert("RGBA")
            red_green_blue = rgba.convert("RGB").tobytes()
            alpha = rgba.getchannel("A").tobytes()
            return wx.Image(rgba.width, rgba.height, red_green_blue, alpha)

    @staticmethod
    def _read_size(source: Path) -> tuple[int, int]:
        with Image.open(source) as image:
            return image.size

    def _set_details(self, label: str) -> None:
        self.details.SetLabel(label)
        self.details.Wrap(max(self.GetClientSize().width - 24, 200))
        self.Layout()

    def on_size(self, event: wx.SizeEvent) -> None:
        self.source_label.Wrap(max(self.GetClientSize().width - 24, 200))
        self.details.Wrap(max(self.GetClientSize().width - 24, 200))
        event.Skip()

    @staticmethod
    def _requested_format(document: ActionDocument) -> str:
        for action in document.actions:
            if action.action_id == "save":
                values = {field.field_id: field.value for field in action.fields}
                return values.get("as", values.get("format", _("Source format")))
        return _("Source format")

    @staticmethod
    def _save_note(document: ActionDocument) -> str:
        return (
            _("The terminal Save action is omitted from preview.")
            if any(action.action_id == "save" for action in document.actions)
            else ""
        )

    @staticmethod
    def _set_bitmap(control: wx.StaticBitmap, image: wx.Image) -> None:
        if image.IsOk():
            source_width = image.GetWidth()
            source_height = image.GetHeight()
            ratio = min(240 / source_width, 240 / source_height)
            width = max(1, round(source_width * ratio))
            height = max(1, round(source_height * ratio))
            image.Rescale(width, height, wx.IMAGE_QUALITY_HIGH)
            control.SetBitmap(wx.BitmapBundle.FromBitmap(wx.Bitmap(image)))

    def _clear_bitmaps(self) -> None:
        empty = wx.BitmapBundle.FromBitmap(wx.NullBitmap)
        self.original.SetBitmap(empty)
        self.result.SetBitmap(empty)

    def _set_busy(self, busy: bool) -> None:
        self.choose.Enable(not busy)
        self.refresh.Enable(not busy)
        self.cancel.Enable(busy)

    def on_close(self, _event: wx.CloseEvent | None = None) -> None:
        self._runner.close()
        self._clear_bitmaps()
        self.Destroy()
