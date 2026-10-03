# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Modeless before/after workflow preview with owned asynchronous rendering."""

from collections.abc import Callable, Mapping, Sequence
import builtins
from pathlib import Path
from typing import Any

import wx

from phatch.core.workflow_preview import (
    PreviewAction,
    PreviewImage,
    PreviewOptions,
    PreviewResult,
)
from phatch.services.workflow_preview import WorkflowPreviewService

_: Callable[[str], str] = getattr(builtins, '_', str)


class WorkflowPreviewFrame(wx.Frame):
    """All widget updates run on the UI thread via wx.CallAfter."""

    def __init__(
        self,
        parent: Any,
        source: Path | str,
        actions: Callable[[], Sequence[PreviewAction]],
        settings: Callable[[], Mapping[str, Any]],
    ) -> None:
        super().__init__(
            parent, title=_('Workflow preview'), size=wx.Size(1120, 740)
        )
        self.source = Path(source)
        self._actions = actions
        self._settings = settings
        self._result: PreviewResult | None = None
        self._closed = False
        self._refresh_timer = None
        self._service = WorkflowPreviewService(wx.CallAfter)
        panel = wx.Panel(self)
        layout = wx.BoxSizer(wx.VERTICAL)
        controls = wx.BoxSizer(wx.HORIZONTAL)
        choose = wx.Button(panel, label=_('Choose image'))
        refresh = wx.Button(panel, label=_('Refresh'))
        cancel = wx.Button(panel, label=_('Cancel'))
        self.full_resolution = wx.CheckBox(
            panel, label=_('Render at full resolution')
        )
        self.use_crop = wx.CheckBox(panel, label=_('Inspect crop'))
        self.crop_fields = [
            wx.SpinCtrl(
                panel,
                min=0 if index < 2 else 1,
                max=1_000_000,
                initial=0 if index < 2 else 256,
                size=wx.Size(75, -1),
            )
            for index in range(4)
        ]
        for widget in (
            choose,
            refresh,
            cancel,
            self.full_resolution,
            self.use_crop,
        ):
            controls.Add(widget, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 4)
        for label, widget in zip(
            ('x', 'y', _('width'), _('height')), self.crop_fields
        ):
            controls.Add(
                wx.StaticText(panel, label=label),
                0,
                wx.ALIGN_CENTER_VERTICAL | wx.LEFT,
                4,
            )
            controls.Add(widget, 0, wx.ALL, 4)
            widget.Enable(False)
            widget.Bind(wx.EVT_SPINCTRL, self._changed)
        self.full_resolution.Bind(wx.EVT_CHECKBOX, self._changed)
        self.use_crop.Bind(wx.EVT_CHECKBOX, self._crop_changed)
        choose.Bind(wx.EVT_BUTTON, self._choose_source)
        refresh.Bind(wx.EVT_BUTTON, self.refresh)
        cancel.Bind(wx.EVT_BUTTON, self._cancel)
        layout.Add(controls, 0, wx.EXPAND)
        comparisons = wx.BoxSizer(wx.HORIZONTAL)
        self.before_window, self.before_bitmap = self._image_panel(
            panel, _('Before')
        )
        self.after_window, self.after_bitmap = self._image_panel(
            panel, _('After / intermediate')
        )
        comparisons.Add(self.before_window, 1, wx.EXPAND | wx.ALL, 5)
        comparisons.Add(self.after_window, 1, wx.EXPAND | wx.ALL, 5)
        layout.Add(comparisons, 1, wx.EXPAND)
        self.steps = wx.Choice(panel, choices=[_('After')])
        self.steps.SetSelection(0)
        self.steps.Bind(wx.EVT_CHOICE, self._select_step)
        layout.Add(self.steps, 0, wx.EXPAND | wx.ALL, 5)
        self.status = wx.StaticText(panel, label=str(self.source))
        layout.Add(self.status, 0, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(layout)
        self.Bind(wx.EVT_CLOSE, self._close)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._destroyed)
        wx.CallAfter(self.refresh)

    @staticmethod
    def _image_panel(parent: Any, label: str) -> tuple[Any, Any]:
        window = wx.ScrolledWindow(parent)
        window.SetScrollRate(10, 10)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(wx.StaticText(window, label=label), 0, wx.ALL, 5)
        bitmap = wx.StaticBitmap(window)
        layout.Add(bitmap, 0, wx.ALL, 5)
        window.SetSizer(layout)
        return window, bitmap

    def refresh(self, event: Any = None) -> None:
        if self._closed:
            return
        crop = None
        if self.use_crop.GetValue():
            x, y, width, height = [
                field.GetValue() for field in self.crop_fields
            ]
            crop = (x, y, x + width, y + height)
        self.status.SetLabel(_('Rendering…') + ' ' + str(self.source))
        self._service.submit(
            self.source,
            list(self._actions()),
            self._display,
            PreviewOptions(
                full_resolution=self.full_resolution.GetValue(), crop=crop
            ),
            self._settings(),
        )

    def workflow_changed(self) -> None:
        """Called by the editor on action or parameter changes."""
        if self._closed:
            return
        self._service.invalidate()
        if self._refresh_timer:
            self._refresh_timer.Stop()
        self.status.SetLabel(_('Workflow changed; refreshing preview…'))
        self._refresh_timer = wx.CallLater(200, self.refresh)

    def _changed(self, event: Any) -> None:
        self.workflow_changed()

    def _crop_changed(self, event: Any) -> None:
        for field in self.crop_fields:
            field.Enable(self.use_crop.GetValue())
        self.workflow_changed()

    def _choose_source(self, event: Any) -> None:
        with wx.FileDialog(
            self,
            _('Choose an image to preview'),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:
            if dialog.ShowModal() == wx.ID_OK:
                self.source = Path(dialog.GetPath())
                self.workflow_changed()

    def _cancel(self, event: Any) -> None:
        if self._refresh_timer:
            self._refresh_timer.Stop()
        self._service.invalidate()
        self.status.SetLabel(_('Preview cancelled'))

    @staticmethod
    def _set_bitmap(widget: Any, window: Any, frame: PreviewImage) -> None:
        with frame.open() as image:
            converted = image.convert('RGBA')
            try:
                width, height = converted.size
                widget.SetBitmap(
                    wx.Bitmap.FromBufferRGBA(
                        width, height, converted.tobytes()
                    )
                )
            finally:
                converted.close()
        window.GetSizer().Layout()
        window.FitInside()

    def _display(self, result: PreviewResult) -> None:
        if self._closed:
            return
        self._result = result
        if result.status != 'success':
            self.status.SetLabel(
                result.failure.message
                if result.failure
                else _('Preview cancelled')
            )
            return
        if result.before:
            self._set_bitmap(
                self.before_bitmap, self.before_window, result.before
            )
        if result.after:
            self._set_bitmap(
                self.after_bitmap, self.after_window, result.after
            )
        self.steps.SetItems(
            [_('After')]
            + [
                f'{index + 1}. {step.label}'
                for index, step in enumerate(result.steps)
            ]
        )
        self.steps.SetSelection(0)
        notes = [str(self.source)]
        if result.approximate:
            notes.append(_('Thumbnail approximation'))
        if result.skipped:
            notes.append(_('Skipped: ') + ', '.join(result.skipped))
        notes.extend(result.warnings)
        self.status.SetLabel('\n'.join(notes))

    def _select_step(self, event: Any) -> None:
        if self._result is None:
            return
        index = self.steps.GetSelection()
        image = (
            self._result.after if index == 0 else self._result.steps[index - 1]
        )
        if image:
            self._set_bitmap(self.after_bitmap, self.after_window, image)

    def _close(self, event: Any) -> None:
        self._shutdown()
        self.Destroy()

    def _shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._refresh_timer:
            self._refresh_timer.Stop()
        self._service.close(wait=False)

    def _destroyed(self, event: Any) -> None:
        if event.GetEventObject() is self:
            self._shutdown()
        event.Skip()
