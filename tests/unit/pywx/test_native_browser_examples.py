from __future__ import annotations

import glob
import runpy
import sys
from types import ModuleType

import pytest
import wx

from phatch.lib.pyWx import folderFileBrowser, imageFileBrowser, vlist, vlistTag
from tests.unit.pywx.native_browser_support import seed_browser_paths

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def run_as_main(module: ModuleType) -> None:
    loaded_module = sys.modules.pop(module.__name__)
    try:
        runpy.run_module(module.__name__, run_name="__main__", alter_sys=True)
    finally:
        sys.modules[module.__name__] = loaded_module


def test_folder_browser_examples_construct_real_controls_without_event_loop(
    native_frame, native_interaction, monkeypatch
) -> None:
    # Given
    app = wx.App.GetInstance()
    assert app is not None
    monkeypatch.setattr(folderFileBrowser.wx, "PySimpleApp", lambda *_args: app)
    native_interaction.expect_main_loop()

    # When
    folderFileBrowser.example_dict_data()

    # Then
    assert len(native_interaction.main_loop_apps) == 1
    assert all(item is app for item in native_interaction.main_loop_apps)
    frames = [
        window for window in wx.GetTopLevelWindows() if window is not native_frame
    ]
    assert len(frames) == 1
    assert all(
        isinstance(frame.GetChildren()[0], folderFileBrowser.Panel)
        for frame in frames
    )


def test_image_browser_example_scripts_both_picker_results(
    native_frame, native_interaction, monkeypatch, tmp_path, test_input_dir
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    loops: list[bool] = []

    class ExampleApp:
        def __init__(self, _redirect: bool) -> None:
            self.top_window: wx.Frame | None = None
            self.OnInit()

        def OnInit(self) -> bool:
            return True

        def SetTopWindow(self, frame: wx.Frame) -> None:
            self.top_window = frame

        def MainLoop(self) -> None:
            loops.append(True)

    monkeypatch.setattr(imageFileBrowser.wx, "App", ExampleApp)
    monkeypatch.setattr(glob, "glob", lambda _pattern: [str(paths.first)])
    native_interaction.expect_dialog(imageFileBrowser.Dialog, wx.ID_CANCEL)
    native_interaction.expect_dialog(imageFileBrowser.Dialog, wx.ID_CANCEL)

    # When
    imageFileBrowser.example()

    # Then
    assert loops == [True]
    frames = [
        window for window in wx.GetTopLevelWindows() if window is not native_frame
    ]
    assert any(frame.GetTitle() == "image file test" for frame in frames)


def test_vlist_examples_construct_real_lists_without_event_loop(
    native_frame, native_interaction, monkeypatch
) -> None:
    # Given
    app = wx.App.GetInstance()
    assert app is not None
    monkeypatch.setattr(vlist.wx, "PySimpleApp", lambda *_args: app)
    native_interaction.expect_main_loop()
    native_interaction.expect_main_loop()

    # When
    vlist.example()
    vlistTag.example()

    # Then
    assert len(native_interaction.main_loop_apps) == 2
    titles = {window.GetTitle() for window in wx.GetTopLevelWindows()}
    assert "Test Tag Browser" in titles


def test_folder_browser_main_constructs_native_browser_without_event_loop(
    native_frame, native_interaction, monkeypatch
) -> None:
    # Given
    app = wx.GetApp()
    assert app is not None
    monkeypatch.setattr(wx, "PySimpleApp", lambda *_args: app)
    native_interaction.expect_main_loop()

    # When
    run_as_main(folderFileBrowser)

    # Then
    assert native_interaction.main_loop_apps == [app]


def test_image_browser_main_accepts_both_scripted_selections(
    native_frame, native_interaction, monkeypatch, tmp_path, test_input_dir
) -> None:
    # Given
    paths = seed_browser_paths(tmp_path, test_input_dir, nested=False)
    loops: list[bool] = []

    class MainApp:
        def __init__(self, _redirect: bool) -> None:
            self.OnInit()

        def OnInit(self) -> bool:
            return True

        def SetTopWindow(self, _frame: wx.Frame) -> None:
            return None

        def MainLoop(self) -> None:
            loops.append(True)

    monkeypatch.setattr(wx, "App", MainApp)
    monkeypatch.setattr(glob, "glob", lambda _pattern: [str(paths.first)])
    native_interaction.expect_dialog(wx.Dialog, wx.ID_OK)
    native_interaction.expect_dialog(wx.Dialog, wx.ID_OK)

    # When
    run_as_main(imageFileBrowser)

    # Then
    assert loops == [True]


@pytest.mark.parametrize("module", [vlist, vlistTag])
def test_vlist_main_constructs_native_controls_without_event_loop(
    module: ModuleType, native_frame, native_interaction, monkeypatch
) -> None:
    # Given
    app = wx.App.GetInstance()
    assert app is not None
    monkeypatch.setattr(wx, "PySimpleApp", lambda *_args: app)
    native_interaction.expect_main_loop()

    # When
    run_as_main(module)

    # Then
    assert native_interaction.main_loop_apps == [app]
