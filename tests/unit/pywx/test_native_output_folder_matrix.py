from __future__ import annotations

from pathlib import Path

import pytest
import wx

from phatch.core.execution_types import (
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    OutputRecord,
    ReportFile,
)
from phatch.pyWx.execution_results import (
    format_completion,
    show_result_dialog,
)

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def _result(source: Path, *folders: Path) -> ExecutionResult:
    outputs = tuple(
        OutputRecord(ReportFile(source, folder / "image.png")) for folder in folders
    )
    return ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (FileResult(source, FileOutcome.PROCESSED, outputs=outputs),),
    )


def _button(dialog, label: str):
    return next(
        child
        for child in dialog.GetChildren()
        if isinstance(child, wx.Button) and child.GetLabel() == label
    )


class SystemRecorder:
    def __init__(self) -> None:
        self.opened: list[Path] = []

    def open_directory(self, folder: Path) -> None:
        self.opened.append(folder)


def test_native_zero_folder_result_disables_owned_action(
    wx_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    enabled: list[bool] = []

    def show_modal(dialog) -> int:
        enabled.append(_button(dialog, "Open Output Folder").IsEnabled())
        return wx.ID_CLOSE

    monkeypatch.setattr(wx.Dialog, "ShowModal", show_modal)

    show_result_dialog(
        None,
        _result(tmp_path / "source.png"),
        "Completed",
        wx,
        SystemRecorder(),
    )

    assert enabled == [False]


def test_native_one_folder_opens_directly_with_literal_path(
    wx_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    folder = tmp_path / "output folder; $(literal)"
    folder.mkdir()
    system = SystemRecorder()

    def show_modal(dialog) -> int:
        button = _button(dialog, "Open Output Folder")
        button.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
        return wx.ID_CLOSE

    monkeypatch.setattr(wx.Dialog, "ShowModal", show_modal)

    show_result_dialog(
        None,
        _result(tmp_path / "source.png", folder),
        "Completed",
        wx,
        system,
    )

    assert system.opened == [folder.resolve()]


def test_native_many_folder_chooser_is_sorted_and_opens_selection(
    wx_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha"
    middle = tmp_path / "Middle"
    zulu = tmp_path / "zulu"
    for folder in (alpha, middle, zulu):
        folder.mkdir()
    chooser_values: list[tuple[str, ...]] = []
    system = SystemRecorder()

    def show_modal(dialog) -> int:
        if isinstance(dialog, wx.SingleChoiceDialog):
            choices = next(
                child for child in dialog.GetChildren() if isinstance(child, wx.ListBox)
            )
            chooser_values.append(tuple(choices.GetItems()))
            dialog.SetSelection(1)
            return wx.ID_OK
        button = _button(dialog, "Open Output Folder")
        button.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
        return wx.ID_CLOSE

    monkeypatch.setattr(wx.Dialog, "ShowModal", show_modal)
    monkeypatch.setattr(wx.SingleChoiceDialog, "ShowModal", show_modal)

    show_result_dialog(
        None,
        _result(tmp_path / "source.png", zulu, alpha, middle),
        "Completed",
        wx,
        system,
    )

    assert chooser_values == [
        tuple(map(str, (alpha.resolve(), middle.resolve(), zulu.resolve())))
    ]
    assert system.opened == [middle.resolve()]


def test_native_disappearing_folder_reports_owned_error(
    wx_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    folder = tmp_path / "vanishing"
    folder.mkdir()
    states: list[tuple[bool, str]] = []

    def show_modal(dialog) -> int:
        folder.rmdir()
        button = _button(dialog, "Open Output Folder")
        button.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
        details = next(
            child for child in dialog.GetChildren() if isinstance(child, wx.TextCtrl)
        )
        states.append((button.IsEnabled(), details.GetValue()))
        return wx.ID_CLOSE

    monkeypatch.setattr(wx.Dialog, "ShowModal", show_modal)

    show_result_dialog(
        None,
        _result(tmp_path / "source.png", folder),
        "Completed",
        wx,
        SystemRecorder(),
    )

    assert states[0][0] is False
    assert "no longer available" in states[0][1]


def test_native_private_paths_are_hidden_but_folder_action_uses_raw_target(
    wx_app,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = Path("/Volumes/private-client/input/source.png")
    folder = tmp_path / "private-client-output"
    folder.mkdir()
    result = _result(source, folder)
    visible_text: list[str] = []
    system = SystemRecorder()

    def show_modal(dialog) -> int:
        details = next(
            child for child in dialog.GetChildren() if isinstance(child, wx.TextCtrl)
        )
        visible_text.append(details.GetValue())
        button = _button(dialog, "Open Output Folder")
        button.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
        return wx.ID_CLOSE

    monkeypatch.setattr(wx.Dialog, "ShowModal", show_modal)

    show_result_dialog(None, result, format_completion(result), wx, system)

    assert "/Volumes/private-client" not in visible_text[0]
    assert str(folder.resolve()) not in visible_text[0]
    assert system.opened == [folder.resolve()]
