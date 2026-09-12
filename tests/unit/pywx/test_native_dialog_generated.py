from __future__ import annotations

import runpy
from pathlib import Path

import pytest
import wx

from .native_dialog_support import command_event, image_tree_data
from .native_dialog_support import dialog_runtime as dialog_runtime

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_generated_status_error_and_files_controls_use_native_layout(
    dialog_runtime, capsys
) -> None:
    # Given
    from phatch.pyWx.wxGlade import dialogs as generated

    parent, _counter, _root = dialog_runtime
    status = generated.StatusDialog(parent)
    error = generated.ErrorDialog(parent)
    files = generated.FilesDialog(parent)

    # When
    status.on_button_log(command_event(status.log))
    status.on_button_report(command_event(status.report))
    error.on_abort(command_event(error.abort))
    error.on_ignore(command_event(error.ignore))
    error.on_skip(command_event(error.skip))
    error.on_details(command_event(error.abort))

    # Then
    assert status.GetSizer().GetItemCount() == 1
    assert status.ok.GetId() == wx.ID_OK
    assert error.GetDefaultItem() is error.ignore
    assert files.GetDefaultItem() is files.ok
    assert files.list.GetWindowStyleFlag() & wx.LC_REPORT
    assert "not implemented" in capsys.readouterr().out


def test_generated_execute_and_plugin_controls_expose_expected_defaults(
    dialog_runtime, capsys
) -> None:
    # Given
    from phatch.pyWx.wxGlade import dialogs as generated

    parent, _counter, _root = dialog_runtime
    execute = generated.ExecuteDialog(parent)
    plugin = generated.WritePluginDialog(parent)

    # When
    execute.on_browse(command_event(execute.browse))
    execute.on_source(wx.CommandEvent(wx.EVT_RADIOBOX.typeId, execute.source.GetId()))
    execute.on_default(command_event(execute.select))
    plugin.on_help(command_event(plugin.help))
    plugin.on_template(wx.CommandEvent(wx.EVT_CHECKBOX.typeId, plugin.template.GetId()))

    # Then
    assert execute.source.GetSelection() == 0
    assert execute.stop_for_errors.GetValue()
    assert execute.check_images_first.GetValue()
    assert execute.always_show_status_dialog.GetValue()
    assert execute.repeat.GetRange() == (1, 9999999)
    assert execute.options_sizer.GetItemCount() == 7
    assert plugin.code.IsMultiLine()
    assert plugin.code.IsEditable() is False
    assert "not implemented" in capsys.readouterr().out


def test_generated_image_tree_builds_real_browser_and_normalizes_home_label(
    dialog_runtime, tmp_path: Path
) -> None:
    # Given
    from phatch.pyWx.wxGlade import dialogs as generated

    parent, _counter, _root = dialog_runtime
    image_path = tmp_path / "folder" / "image.jpg"
    image_path.parent.mkdir()
    data, data_type = image_tree_data(image_path)

    # When
    dialog = generated.ImageTreeDialog(
        data, data_type, ["filename", "width", "height"], parent
    )
    dialog.browser.SetColumnWidths(120, 60, 60)
    dialog.browser.UpdateHeaders(["filename", "width", "height"])

    # Then
    assert dialog.browser.list.GetItemCount() == 1
    assert dialog.browser.list.GetColumnWidth(0) == 120
    assert dialog.browser.GetTreeLabel("/Users/name/", "/Users/") == "name"
    assert dialog.GetDefaultItem() is dialog.ok
    assert not dialog.hint.IsEnabled()


def test_generated_module_entrypoint_shows_window_with_guarded_main_loop(
    dialog_runtime, native_interaction, monkeypatch
) -> None:
    # Given
    parent, _counter, _root = dialog_runtime

    class ExampleApp:
        def __init__(self, redirect: bool) -> None:
            self.top_window = parent

        def SetTopWindow(self, window: wx.Window) -> None:
            self.top_window = window

        def MainLoop(self) -> None:
            native_interaction.main_loop(self)

    monkeypatch.setattr(wx, "PySimpleApp", ExampleApp, raising=False)
    native_interaction.expect_main_loop()

    # When
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        runpy.run_module("phatch.pyWx.wxGlade.dialogs", run_name="__main__")

    # Then
    assert native_interaction.main_loop_apps
    assert any(
        window.GetTitle() == "Ready!"
        for window in vars(wx)["GetTopLevelWindows"]()
    )
