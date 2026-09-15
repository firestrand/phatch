from __future__ import annotations

import builtins
import json
import sys
from pathlib import Path

import pytest
import wx

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)

from .native_dialog_support import ActionFixture, image_tree_data
from .native_dialog_support import dialog_runtime as dialog_runtime

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_files_dialog_populates_filename_folder_and_minimum_column(
    dialog_runtime, tmp_path: Path
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    files = [tmp_path / "a.jpg", tmp_path / "nested" / "b.png"]

    # When
    dialog = dialogs.FilesDialog(parent, "Invalid", "Check images", files)

    # Then
    assert dialog.GetTitle() == "Check images"
    assert dialog.message.GetLabel() == "Invalid"
    assert dialog.list.GetItemCount() == 2
    assert dialog.list.GetItemText(0) == "a.jpg"
    assert dialog.list.GetItem(1, 1).GetText() == str(tmp_path / "nested")
    assert dialog.list.GetColumnWidth(0) >= 100


def test_progress_dialog_tracks_continue_skip_and_cancel_states(dialog_runtime) -> None:
    # Given
    from phatch.pyWx import dialogs

    class ScriptedProgressDialog(dialogs.ProgressDialog):
        update_result: tuple[bool, bool] = (True, False)

        def Update(self, value: int, newmsg: str = "") -> tuple[bool, bool]:
            return self.update_result

    parent, _counter, _root = dialog_runtime
    dialog = ScriptedProgressDialog(parent, "Progress", 2, 3)
    result = {}

    # When
    dialog.update(result, 1, newmsg="working")

    # Then
    assert result == {"keepgoing": True, "skip": False}

    message_dialog = ScriptedProgressDialog(parent, "Progress", 1, message="ready")
    message_dialog.close()
    dialog.update_result = (False, False)
    dialog.update(result, 3)
    wx.Yield()
    assert result == {"keepgoing": False, "skip": False}


def test_valid_file_confirmation_closes_verification_progress(
    dialog_runtime, monkeypatch
) -> None:
    # Given
    from phatch.core import api
    from phatch.pyWx import dialogs
    from phatch.services.legacy_execution import LegacyExecutionContext
    from phatch.services.legacy_interaction import LegacyInteraction

    parent, _counter, _root = dialog_runtime
    context = LegacyExecutionContext(
        (),
        (),
        {"stop_for_errors": False, "repeat": 1},
        None,
        False,
    )
    context.photo_state.valid_infos.append({"path": "valid.png"})
    verification = dialogs.ProgressDialog(parent, "Checking images", 1)
    monkeypatch.setattr(
        api.send,
        "frame_show_image_tree",
        lambda result, *args, **kwargs: result.update(answer=True),
    )

    # When
    assert LegacyInteraction(context).confirm_valid_files(())

    # Then
    assert verification._listeners == []
    execution = dialogs.ProgressDialog(parent, "Executing action list", 1, 2)
    result = {}
    api.send.progress_update_filename(result, 0, "valid.png")
    api.send.progress_update_index(result, 0, 0)
    assert result == {"keepgoing": True, "skip": False}
    execution.close()


def test_action_dialog_filters_real_list_and_exposes_selected_values(
    dialog_runtime
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    actions = {"resize": ActionFixture()}
    dialog = dialogs.ActionDialog(parent, actions, size=(420, 360))
    list_box = dialog.GetListBox()
    assert isinstance(list_box, dialogs.ActionListBox)

    # When
    list_box.SetFilter("resize")
    list_box.SetSelection(0)

    # Then
    assert dialog.ExtractTags(list(actions.values())) == [
        "Select",
        "All",
        "geometry",
    ]
    assert not list_box.IsEmpty()
    assert list_box.GetStringSelection() == "Resize"
    assert dialog.GetStringSelection() == "Resize"
    label, summary = list_box.GetItem(0)[:2]
    assert label == "Resize"
    assert summary.endswith("\nResize an image")
    assert summary.startswith("[Available] [Preview unavailable")
    assert dialog.ok.IsEnabled()

    list_box.SetFilter("absent")
    assert list_box.IsEmpty()
    assert not dialog.ok.IsEnabled()


def test_action_dialog_uses_capability_badges_without_constructing_action(
    dialog_runtime,
) -> None:
    from phatch.pyWx import dialogs

    class ExplodingAction(ActionFixture):
        label = "Imagemagick"

        def __init__(self) -> None:
            raise AssertionError("presentation must not construct actions")

    capability = Capability(
        CapabilityId("imagemagick-6"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "install ImageMagick 6",
    )
    parent, _counter, _root = dialog_runtime

    dialog = dialogs.ActionDialog(
        parent,
        {"Imagemagick": ExplodingAction},
        capabilities={"imagemagick-6": capability},
        size=(420, 360),
    )
    summary = dialog.GetListBox().GetItem(0)[1]

    assert "Unavailable" in summary
    assert "install ImageMagick 6" in summary
    assert "Preview blocked" in summary


def test_action_dialog_renders_full_translated_unavailability_reason(
    dialog_runtime,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from phatch.pyWx import dialogs

    translations = {
        "Unavailable": "Nicht verfügbar",
        "install ImageMagick 6": "ImageMagick 6 installieren",
        "Preview blocked: external process": "Vorschau gesperrt: externer Prozess",
    }
    monkeypatch.setattr(
        builtins,
        "_",
        lambda source: translations.get(source, source),
    )

    class ExternalAction(ActionFixture):
        label = "Imagemagick"
        __doc__ = "Run ImageMagick"

    capability = Capability(
        CapabilityId("imagemagick-6"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "install ImageMagick 6",
    )
    parent, _counter, _root = dialog_runtime
    dialog = dialogs.ActionDialog(
        parent,
        {"Imagemagick": ExternalAction},
        capabilities={"imagemagick-6": capability},
        size=(420, 360),
    )
    list_box = dialog.GetListBox()

    event = wx.CommandEvent(wx.EVT_LISTBOX.typeId, list_box.GetId())
    event.SetInt(0)
    wx.PostEvent(list_box, event)
    wx.Yield()

    rendered_detail = dialog.status.GetLabel()
    assert rendered_detail == (
        "[Nicht verfügbar] ImageMagick 6 installieren\n"
        "[Vorschau gesperrt: externer Prozess]"
    )
    assert "Unavailable" not in rendered_detail
    assert "install ImageMagick 6" not in rendered_detail
    assert "Preview blocked" not in rendered_detail
    sys.stdout.write(
        json.dumps({"rendered_detail": rendered_detail}, ensure_ascii=False) + "\n"
    )


def test_image_tree_controller_updates_controls_and_inspection_frame(
    dialog_runtime, tmp_path: Path
) -> None:
    # Given
    from phatch.pyWx import dialogs

    parent, _counter, _root = dialog_runtime
    image_path = tmp_path / "image.jpg"
    data, data_type = image_tree_data(image_path)
    dialog = dialogs.ImageTreeDialog(
        data,
        data_type,
        ["filename", "width", "height"],
        parent,
        size=(520, 340),
    )

    # When
    dialog.SetColumnWidths(140, 60, 60)
    dialog.UpdateHeaders(["filename", "width", "height"])
    dialog.SetOkLabel("Use image")
    dialog.ShowButtons(False)
    dialog.SetData(data)

    # Then
    assert dialog.GetSize() == wx.Size(520, 340)
    assert dialog.ok.GetLabel() == "Use image"
    assert not dialog.hint.IsShown()
    assert not dialog.cancel.IsShown()
    assert dialog.browser.list.GetItemCount() == 1


def test_status_dialog_reflects_report_and_dispatches_parent_actions(
    dialog_runtime
) -> None:
    # Given
    from phatch.pyWx import dialogs

    class RecordingStatusDialog(dialogs.StatusDialog):
        def __init__(self, parent: wx.Window) -> None:
            self.modal_results: list[int] = []
            super().__init__(parent)

        def EndModal(self, retCode: int) -> None:
            self.modal_results.append(retCode)

    parent, _counter, _root = dialog_runtime
    calls: list[str] = []
    parent.show_report = lambda: calls.append("report")
    parent.show_log = lambda: calls.append("log")
    dialog = RecordingStatusDialog(parent)
    app = wx.GetApp()

    # When
    dialog.SetMessage("Complete", report=[("image.jpg",)])

    # Then
    assert dialog.message.GetLabel() == "Complete"
    assert vars(app)["report"] == [("image.jpg",)]
    assert dialog.report.IsShown()

    dialog.on_button_report(wx.CommandEvent())
    dialog.on_button_log(wx.CommandEvent())
    assert calls == ["report", "log"]
    assert dialog.modal_results == [wx.ID_OK, wx.ID_OK]
