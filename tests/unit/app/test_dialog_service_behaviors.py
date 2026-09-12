from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from phatch.core import ct
from phatch.pyWx.dialog_service import DialogDependencies, DialogService


class DialogStub:
    instances: ClassVar[list[DialogStub]] = []
    modal_result = -6
    future_errors_value = False

    def __init__(self, *args, **kwargs) -> None:
        self.args = args
        self.kwargs = kwargs
        self.destroyed = False
        self.exported = False
        self.shown = False
        self.overwrite_existing_images = SimpleNamespace(Disable=self._disable)
        self.log = SimpleNamespace(Show=self._show_log)
        self.future_errors = SimpleNamespace(GetValue=lambda: self.future_errors_value)
        self.disabled = False
        self.log_visible = False
        DialogStub.instances.append(self)

    def _disable(self) -> None:
        self.disabled = True

    def _show_log(self, visible: bool) -> None:
        self.log_visible = visible

    def import_settings(self, settings: dict) -> None:
        self.settings = settings

    def export_settings(self, settings: dict) -> None:
        self.exported = True
        settings["exported"] = True

    def ShowModal(self) -> int:
        return self.modal_result

    def Destroy(self) -> None:
        self.destroyed = True

    def GetSize(self) -> tuple[int, int]:
        return (640, 100)

    def SetSize(self, size: tuple[int, int]) -> None:
        self.size = size

    def SetMessage(self, message: str) -> None:
        self.message = message

    def SetColumnWidths(self, *widths: int) -> None:
        self.widths = widths

    def SetOkLabel(self, label: str) -> None:
        self.ok_label = label

    def ShowButtons(self, visible: bool) -> None:
        self.buttons_visible = visible

    def Show(self) -> None:
        self.shown = True


class FrameStub:
    filename = "/tmp/list.phatch"

    def GetSize(self) -> tuple[int, int]:
        return (320, 240)

    def IsShown(self) -> bool:
        return False

    def IsActive(self) -> bool:
        return True

    def get_icon_filename(self) -> str:
        return "/tmp/icon.png"

    def RequestUserAttention(self) -> None:
        self.attention_requested = True


def make_service() -> tuple[DialogService, FrameStub, SimpleNamespace]:
    DialogStub.instances.clear()
    app = SimpleNamespace(report=None, settings={}, IsActive=lambda: True)
    wx = SimpleNamespace(
        OK=1,
        ICON_ERROR=2,
        ICON_EXCLAMATION=4,
        ICON_INFORMATION=8,
        ICON_QUESTION=16,
        YES_NO=32,
        DEFAULT_DIALOG_STYLE=64,
        MAXIMIZE_BOX=128,
        RESIZE_BORDER=256,
        ID_CANCEL=-1,
        ID_ABORT=-2,
        ID_FORWARD=-3,
        ID_OK=-6,
        MessageDialog=DialogStub,
        GetApp=lambda: app,
    )
    dialogs = SimpleNamespace(
        ExecuteDialog=DialogStub,
        FilesDialog=DialogStub,
        StatusDialog=DialogStub,
        ImageTreeDialog=DialogStub,
        ProgressDialog=DialogStub,
        ErrorDialog=DialogStub,
        get_max_height=lambda height: height,
    )
    dependencies = DialogDependencies(
        wx=wx,
        wx_lib_dialogs=SimpleNamespace(ScrolledMessageDialog=DialogStub),
        dialogs=dialogs,
        list_data=SimpleNamespace(files_data_dict=lambda values: values, DataDict=dict),
        notify=SimpleNamespace(send=lambda **payload: None),
        graphics=SimpleNamespace(bitmap=lambda value: value),
        images=SimpleNamespace(ICON_PHATCH_64="icon"),
        system=SimpleNamespace(filename_to_title=lambda value: value),
        api=SimpleNamespace(SEE_LOG="See log"),
    )
    frame = FrameStub()
    return DialogService(frame, dependencies), frame, app


def test_execute_dialog_exports_settings_and_always_destroys() -> None:
    service, _, _ = make_service()
    result: dict[str, bool] = {}
    settings = {"overwrite_existing_images_forced": True}

    service.show_execute_dialog(result, settings, ["image.jpg"])

    dialog = DialogStub.instances[-1]
    assert result == {"cancel": False}
    assert settings["paths"] == ["image.jpg"]
    assert settings["exported"] is True
    assert dialog.disabled is True
    assert dialog.destroyed is True


def test_execute_dialog_returns_without_export_when_cancelled() -> None:
    service, _, _ = make_service()
    DialogStub.modal_result = -1
    result: dict[str, bool] = {}
    settings: dict[str, bool] = {}

    service.show_execute_dialog(result, settings)

    dialog = DialogStub.instances[-1]
    assert result == {"cancel": True}
    assert dialog.exported is False
    assert dialog.destroyed is True
    DialogStub.modal_result = -6


def test_files_status_and_progress_dialogs_receive_public_inputs() -> None:
    service, _, _ = make_service()
    result: dict[str, bool] = {}

    service.show_files_message(result, "message", "title", ["a.jpg"])
    files_dialog = DialogStub.instances[-1]
    service.show_status("working", log=False)
    status_dialog = DialogStub.instances[-1]
    service.show_progress("title", 4, 2, "message")

    assert result == {"cancel": False}
    assert files_dialog.size == (640, 200)
    assert files_dialog.destroyed is True
    assert status_dialog.message == "working"
    assert status_dialog.log_visible is False
    assert status_dialog.destroyed is True
    assert DialogStub.instances[-1].args[1:] == ("title", 4, 2, "message")


@pytest.mark.parametrize(
    ("modal", "buttons"), [(False, False), (True, False), (False, True)]
)
def test_image_tree_uses_modal_or_modeless_lifecycle(
    modal: bool, buttons: bool
) -> None:
    service, _, _ = make_service()
    result: dict[str, bool] = {}

    service.show_image_tree(
        result, [["image.jpg"]], [120], ["filename"], modal=modal, buttons=buttons
    )

    dialog = DialogStub.instances[-1]
    assert dialog.widths == (120,)
    assert dialog.buttons_visible is buttons
    assert dialog.shown is not (modal or buttons)
    assert dialog.destroyed is (modal or buttons)


def test_report_routes_processed_and_empty_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _, app = make_service()
    calls: list[str] = []
    monkeypatch.setattr(
        service, "show_image_tree", lambda *args, **kwargs: calls.append("tree")
    )
    monkeypatch.setattr(
        service, "show_message", lambda *args, **kwargs: calls.append("empty")
    )

    app.report = [["image.jpg"]]
    service.show_report()
    app.report = []
    service.show_report()

    assert calls == ["tree", "empty"]


@pytest.mark.parametrize(
    ("content", "expected"), [(None, "Nothing"), ("", "Hooray"), ("problem", "problem")]
)
def test_log_reports_missing_empty_and_populated_files(
    content: str | None,
    expected: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _, _ = make_service()
    log_path = tmp_path / "phatch.log"
    if content is not None:
        log_path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(ct, "USER_LOG_PATH", str(log_path))
    messages: list[str] = []
    monkeypatch.setattr(
        service,
        "show_scrolled_message",
        lambda message, title: messages.append(message),
    )

    service.show_log()

    assert expected in messages[0]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [(-2, "abort"), (-3, "skip"), (-99, "ignore")],
)
def test_progress_error_maps_dialog_answers(
    answer: int,
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, _, _ = make_service()
    DialogStub.modal_result = answer
    result: dict[str, bool | str] = {}
    logs: list[bool] = []
    monkeypatch.setattr(service, "show_log", lambda: logs.append(True))

    service.show_progress_error(result, "failure")

    assert result["answer"] == expected
    assert result["stop_for_errors"] is True
    assert logs == ([True] if answer == -2 else [])
    assert DialogStub.instances[-1].destroyed is True
    DialogStub.modal_result = -6


def test_message_variants_and_scrolled_dialog_destroy_resources() -> None:
    service, _, _ = make_service()

    assert service.show_error("error") == -6
    assert service.show_question("question") == -6
    assert service.show_info("info") == -6
    service.show_scrolled_message("details", "title", size=(20, 20))

    assert all(dialog.destroyed for dialog in DialogStub.instances)


def test_active_notification_is_suppressed_unless_forced() -> None:
    service, frame, _ = make_service()
    sent: list[str] = []
    service._deps.notify.send = lambda **payload: sent.append(payload["message"])

    service.show_notification("normal")
    service.show_notification("forced", force=True)

    assert sent == ["forced"]
    assert not hasattr(frame, "attention_requested")
