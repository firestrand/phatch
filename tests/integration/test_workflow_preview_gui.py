# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Actual wx controls receive an asynchronously rendered workflow preview."""

import builtins
import os
import sys
import time

import pytest

wx = pytest.importorskip('wx')
if sys.platform.startswith('linux') and not os.environ.get('DISPLAY'):
    pytest.skip(
        'A display is required for the wx smoke check', allow_module_level=True
    )

from phatch.core import api
from phatch.pyWx.workflow_preview import WorkflowPreviewFrame


def test_preview_window_renders_refreshes_and_closes(test_input_dir, tmp_path):
    builtins._ = str
    api.import_actions()
    actions = [api.ACTIONS['Invert'](), api.ACTIONS['Save']()]
    actions[-1].set_field_as_string('In', str(tmp_path / 'outputs'))
    app = wx.App(False)
    parent = wx.Frame(None)
    window = WorkflowPreviewFrame(
        parent, test_input_dir / 'frog.gif', lambda: actions, lambda: {}
    )

    def wait_for_result():
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            app.Yield()
            if window._result is not None:
                return window._result
            time.sleep(0.01)
        raise AssertionError(
            'Preview worker did not deliver to the wx event loop'
        )

    try:
        result = wait_for_result()
        assert result.status == 'success', result.failure
        assert window.before_bitmap.GetBitmap().GetWidth() == 128
        assert window.after_bitmap.GetBitmap().GetWidth() == 128
        assert window.steps.GetCount() == 2
        assert 'Save' in window.status.GetLabel()
        window._result = None
        actions[0].set_field_as_string('__enabled__', 'no')
        window.workflow_changed()
        result = wait_for_result()
        assert not result.steps
        assert window.steps.GetCount() == 1
        assert not (tmp_path / 'outputs').exists()
    finally:
        window.Close()
        parent.Destroy()
        app.Yield()
        app.Destroy()
