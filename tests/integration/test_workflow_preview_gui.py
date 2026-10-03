# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual wx controls receive an asynchronously rendered workflow preview."""

import builtins
import os
import sys
import time

import pytest

pytest.importorskip("wx")
import wx

from phatch.core import api
from phatch.pyWx.workflow_preview import WorkflowPreviewFrame

if sys.platform.startswith("linux") and not os.environ.get("DISPLAY"):
    pytest.skip("A display is required for the wx smoke check", allow_module_level=True)


def test_preview_window_renders_refreshes_and_closes(test_input_dir, tmp_path):
    builtins._ = str
    api.import_actions()
    actions = [api.ACTIONS["Invert"](), api.ACTIONS["Save"]()]
    actions[-1].set_field_as_string("In", str(tmp_path / "outputs"))
    existing_app = wx.GetApp()
    app = existing_app or wx.App(False)
    parent = wx.Frame(None)
    window = WorkflowPreviewFrame(
        parent, test_input_dir / "frog.gif", lambda: actions, lambda: {}
    )

    def wait_for_result():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            app.Yield()
            if window._result is not None:
                return window._result
            time.sleep(0.01)
        raise AssertionError("Preview worker did not deliver to the wx event loop")

    try:
        result = wait_for_result()
        assert result.status == "success", result.failure
        assert window.before_bitmap.GetBitmap().GetWidth() == 128
        assert window.after_bitmap.GetBitmap().GetWidth() == 128
        assert window.steps.GetCount() == 2
        assert "Save" in window.status.GetLabel()
        window._result = None
        actions[0].set_field_as_string("__enabled__", "no")
        window.workflow_changed()
        result = wait_for_result()
        assert not result.steps
        assert window.steps.GetCount() == 1
        assert not (tmp_path / "outputs").exists()
    finally:
        window.Close()
        parent.Destroy()
        app.Yield()
        if existing_app is None:
            app.Destroy()


@pytest.fixture
def preview_window(test_input_dir, tmp_path):
    existing_app = wx.GetApp()
    app = existing_app or wx.App(False)
    api.import_actions()
    actions = [api.ACTIONS["Invert"](), api.ACTIONS["Save"]()]
    actions[-1].set_field_as_string("In", str(tmp_path / "outputs"))
    parent = wx.Frame(None)
    window = WorkflowPreviewFrame(
        parent, test_input_dir / "frog.gif", lambda: actions, lambda: {}
    )
    try:
        yield app, window
    finally:
        window._service.close()
        if window:
            window.Close()
        parent.Destroy()
        app.Yield()
        if existing_app is None:
            app.Destroy()


def wait_for_preview(app, window):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        app.Yield()
        if window._result is not None:
            return window._result
        time.sleep(0.01)
    raise AssertionError("No preview result delivered")


def test_preview_crop_steps_and_cancellation_controls(preview_window, tmp_path):
    app, window = preview_window
    assert wait_for_preview(app, window).status == "success"
    window.steps.SetSelection(1)
    window._select_step(None)
    assert window.after_bitmap.GetBitmap().GetWidth() == 128
    window.use_crop.SetValue(True)
    for control, value in zip(window.crop_fields, (2, 3, 20, 10), strict=True):
        control.SetValue(value)
    window._crop_changed(None)
    assert all(control.IsEnabled() for control in window.crop_fields)
    window.full_resolution.SetValue(True)
    window._changed(None)
    window._result = None
    assert wait_for_preview(app, window).after.size == (20, 10)
    window._cancel(None)
    assert window.status.GetLabel() == "Preview cancelled"
    assert not (tmp_path / "outputs").exists()
    window._result = None
    window._select_step(None)
    window.crop_fields[0].SetValue(1000)
    window.refresh()
    result = wait_for_preview(app, window)
    assert result.status == "failed"
    assert window.status.GetLabel() == result.failure.message


def test_preview_choose_source_and_closed_delivery(
    preview_window, tmp_path, monkeypatch
):
    from PIL import Image

    from phatch.core.workflow_preview import PreviewResult

    app, window = preview_window
    wait_for_preview(app, window)
    source = tmp_path / "replacement.png"
    with Image.new("RGB", (32, 16), "red") as image:
        image.save(source)
    original = window.source
    monkeypatch.setattr(wx.FileDialog, "ShowModal", lambda dialog: wx.ID_CANCEL)
    window._choose_source(None)
    assert window.source == original
    monkeypatch.setattr(wx.FileDialog, "ShowModal", lambda dialog: wx.ID_OK)
    monkeypatch.setattr(wx.FileDialog, "GetPath", lambda dialog: str(source))
    window._choose_source(None)
    window._result = None
    assert wait_for_preview(app, window).before.size == (32, 16)
    window._display(PreviewResult("cancelled"))
    assert window.status.GetLabel() == "Preview cancelled"
    window._display(PreviewResult("success"))
    window._select_step(None)
    window._cancel(None)
    window._shutdown()
    previous = window._result
    window.refresh()
    window.workflow_changed()
    window._display(PreviewResult("failed"))
    assert window._result is previous
