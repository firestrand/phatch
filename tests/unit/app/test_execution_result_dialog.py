from collections.abc import Callable
from pathlib import Path

import pytest

from phatch.core.execution_types import (
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    OutputRecord,
    ReportFile,
)
from phatch.pyWx.execution_results import show_result_dialog


class FakeFont:
    def __init__(self) -> None:
        self.point_size = 12

    def MakeBold(self) -> None:
        return None

    def GetPointSize(self) -> int:
        return self.point_size

    def SetPointSize(self, point_size: int) -> None:
        self.point_size = point_size


class FakeWindow:
    def SetMinSize(self, size) -> None:
        self.min_size = size

    def SetMaxSize(self, size) -> None:
        self.max_size = size


class FakeStaticText(FakeWindow):
    def __init__(self, parent, label: str) -> None:
        self.label = label
        self.font = FakeFont()

    def GetFont(self) -> FakeFont:
        return self.font

    def SetFont(self, font: FakeFont) -> None:
        self.font = font

    def Wrap(self, width: int) -> None:
        self.wrap_width = width


class FakeTextCtrl(FakeWindow):
    def __init__(self, parent, value: str, style: int) -> None:
        self.value = value

    def AppendText(self, text: str) -> None:
        self.value += text


class FakeButton:
    def __init__(self, wx, label: str) -> None:
        self.enabled = True
        self.handler = None
        wx.buttons[label] = self

    def Enable(self, enabled: bool) -> None:
        self.enabled = enabled

    def Disable(self) -> None:
        self.enabled = False

    def Bind(self, event, handler) -> None:
        self.handler = handler


class FakeDialog:
    def __init__(self, wx) -> None:
        self.wx = wx
        self.destroyed = False

    def SetSizerAndFit(self, body) -> None:
        return None

    def GetSize(self):
        return (512, 400)

    def SetMinSize(self, size) -> None:
        self.min_size = size

    def SetEscapeId(self, identifier: int) -> None:
        self.escape_id = identifier

    def EndModal(self, identifier: int) -> None:
        self.modal_result = identifier

    def ShowModal(self) -> int:
        self.wx.modal_action()
        return self.wx.ID_CLOSE

    def Destroy(self) -> None:
        self.destroyed = True


class FakeChoiceDialog:
    def __init__(self, wx, choices) -> None:
        self.wx = wx
        self.choices = choices
        self.destroyed = False
        wx.choice = self

    def ShowModal(self) -> int:
        return self.wx.choice_result

    def GetSelection(self) -> int:
        return self.wx.choice_selection

    def Destroy(self) -> None:
        self.destroyed = True


class FakeSizer:
    def Add(self, *args) -> None:
        return None


class FakeWx:
    VERTICAL = 1
    HORIZONTAL = 2
    DEFAULT_DIALOG_STYLE = 4
    RESIZE_BORDER = 8
    TE_MULTILINE = 16
    TE_READONLY = 32
    BORDER_NONE = 64
    TE_WORDWRAP = 128
    LEFT = 256
    RIGHT = 512
    TOP = 1024
    EXPAND = 2048
    ALL = 4096
    ALIGN_RIGHT = 8192
    BOTTOM = 16384
    ID_CLOSE = 1
    ID_OK = 2
    EVT_BUTTON = object()

    def __init__(self) -> None:
        self.buttons: dict[str, FakeButton] = {}
        self.dialog: FakeDialog | None = None
        self.details: FakeTextCtrl | None = None
        self.choice: FakeChoiceDialog | None = None
        self.choice_result = self.ID_OK
        self.choice_selection = 0
        self.modal_action: Callable[[], object] = lambda: None

    def Dialog(self, parent, title: str, style: int) -> FakeDialog:
        self.dialog = FakeDialog(self)
        return self.dialog

    def BoxSizer(self, orientation: int) -> FakeSizer:
        return FakeSizer()

    def StaticText(self, parent, label: str) -> FakeStaticText:
        return FakeStaticText(parent, label)

    def TextCtrl(self, parent, value: str, style: int) -> FakeTextCtrl:
        self.details = FakeTextCtrl(parent, value, style)
        return self.details

    def Button(self, parent, *args, **kwargs) -> FakeButton:
        label = kwargs["label"] if "label" in kwargs else args[-1]
        return FakeButton(self, label)

    def SingleChoiceDialog(
        self, parent, message: str, title: str, choices
    ) -> FakeChoiceDialog:
        return FakeChoiceDialog(self, choices)


class FakeSystem:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.opened = []

    def open_directory(self, folder: Path) -> None:
        if self.error is not None:
            raise self.error
        self.opened.append(folder)


def result_with_folders(source: Path, *folders: Path) -> ExecutionResult:
    outputs = tuple(
        OutputRecord(ReportFile(source, folder / "image.png")) for folder in folders
    )
    return ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (FileResult(source, FileOutcome.PROCESSED, outputs=outputs),),
    )


def click(wx: FakeWx, label: str) -> None:
    handler = wx.buttons[label].handler
    assert handler is not None
    handler(None)


def test_dialog_disables_missing_folder_and_destroys() -> None:
    wx = FakeWx()
    system = FakeSystem()
    wx.modal_action = lambda: (
        click(wx, "Open Output Folder"),
        click(wx, "Close"),
    )

    show_result_dialog(
        None,
        ExecutionResult(ExecutionOutcome.COMPLETED, ()),
        "Completed",
        wx,
        system,
    )

    assert not wx.buttons["Open Output Folder"].enabled
    assert wx.details is not None
    assert "no longer available" in wx.details.value
    assert wx.dialog is not None
    assert wx.dialog.destroyed


def test_dialog_chooses_sorted_output_folder(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    first = tmp_path / "a"
    second = tmp_path / "b"
    first.mkdir()
    second.mkdir()
    wx = FakeWx()
    wx.choice_selection = 1
    system = FakeSystem()
    wx.modal_action = lambda: click(wx, "Open Output Folder")

    show_result_dialog(
        None,
        result_with_folders(source, second, first),
        "Completed\nDetails",
        wx,
        system,
    )

    assert wx.choice is not None
    assert wx.choice.choices == (str(first.resolve()), str(second.resolve()))
    assert wx.choice.destroyed
    assert system.opened == [second.resolve()]


def test_dialog_keeps_open_error_visible(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    folder = tmp_path / "output"
    folder.mkdir()
    wx = FakeWx()
    system = FakeSystem(FileNotFoundError(folder))
    wx.modal_action = lambda: click(wx, "Open Output Folder")

    show_result_dialog(
        None, result_with_folders(source, folder), "Completed\nDetails", wx, system
    )

    assert not wx.buttons["Open Output Folder"].enabled
    assert wx.details is not None
    assert "no longer available" in wx.details.value


def test_dialog_destroys_cancelled_folder_chooser(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    folders = (tmp_path / "a", tmp_path / "b")
    for folder in folders:
        folder.mkdir()
    wx = FakeWx()
    wx.choice_result = wx.ID_CLOSE
    system = FakeSystem()
    wx.modal_action = lambda: click(wx, "Open Output Folder")

    show_result_dialog(
        None, result_with_folders(source, *folders), "Completed", wx, system
    )

    assert wx.choice is not None
    assert wx.choice.destroyed
    assert system.opened == []


def test_dialog_is_destroyed_when_modal_display_fails() -> None:
    wx = FakeWx()
    wx.modal_action = lambda: (_ for _ in ()).throw(RuntimeError("display failed"))

    with pytest.raises(RuntimeError, match="display failed"):
        show_result_dialog(
            None,
            ExecutionResult(ExecutionOutcome.COMPLETED, ()),
            "Completed",
            wx,
            FakeSystem(),
        )

    assert wx.dialog is not None
    assert wx.dialog.destroyed
