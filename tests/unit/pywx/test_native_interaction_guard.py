from __future__ import annotations

import pytest
import wx

from tests.native_interaction_guard import (
    install_native_interaction_guard,
    run_bounded_main_loop,
)

from .native_popup_support import SelectionDialog

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def test_unexpected_modal_fails_before_native_loop(native_frame) -> None:
    dialog = wx.Dialog(native_frame)

    with pytest.raises(AssertionError, match=r"Unexpected Dialog\.ShowModal"):
        dialog.ShowModal()


def test_unexpected_native_message_box_fails_without_showing_ui() -> None:
    with pytest.raises(AssertionError, match="Unexpected native prompt"):
        wx.MessageBox("This must never wait for a human")


def test_scripted_modal_populates_controls_and_is_consumed_once(
    native_frame, native_interaction
) -> None:
    dialog = SelectionDialog(native_frame, "before")
    native_interaction.expect_dialog(SelectionDialog, wx.ID_OK, ("selected",))

    result = dialog.ShowModal()

    assert result == wx.ID_OK
    assert dialog.image_path.GetValue() == "selected"
    with pytest.raises(AssertionError, match=r"Unexpected SelectionDialog\.ShowModal"):
        dialog.ShowModal()


def test_scripted_picker_sets_real_dialog_path(
    native_frame, native_interaction, tmp_path
) -> None:
    selected = tmp_path / "selected.png"
    dialog = wx.FileDialog(native_frame)
    native_interaction.expect_dialog(wx.FileDialog, wx.ID_OK, path=str(selected))

    result = dialog.ShowModal()

    assert result == wx.ID_OK
    assert dialog.GetPath() == str(selected)


def test_scripted_text_entry_sets_dialog_value(
    native_frame, native_interaction
) -> None:
    dialog = wx.TextEntryDialog(native_frame, "Question", value="before")
    native_interaction.expect_dialog(wx.TextEntryDialog, wx.ID_OK, ("scripted value",))

    result = dialog.ShowModal()

    assert result == wx.ID_OK
    assert dialog.GetValue() == "scripted value"


def test_popup_and_main_loop_require_explicit_scripts(
    native_frame, wx_app, native_interaction
) -> None:
    menu = wx.Menu()
    native_interaction.expect_popup()
    native_interaction.expect_main_loop()

    popup_result = native_frame.PopupMenu(menu)
    wx_app.MainLoop()

    assert popup_result is False
    assert native_interaction.main_loop_apps == [wx_app]


def test_bounded_real_main_loop_runs_callback_and_propagates_failure(
    wx_app, native_frame
) -> None:
    observed: list[str] = []

    def fail_in_callback() -> None:
        observed.append("called")
        raise AssertionError("callback failed")

    with pytest.raises(AssertionError, match="callback failed"):
        run_bounded_main_loop(wx_app, fail_in_callback, timeout_ms=1_000)

    assert observed == ["called"]


def test_bounded_real_main_loop_runs_expected_callback(wx_app, native_frame) -> None:
    observed: list[str] = []

    run_bounded_main_loop(
        wx_app, lambda: observed.append(native_frame.GetTitle()), timeout_ms=1_000
    )

    assert observed == ["Native popup test"]


def test_bounded_real_main_loop_rejects_nested_loop(
    wx_app, native_frame, monkeypatch
) -> None:
    install_native_interaction_guard(monkeypatch)

    with pytest.raises(AssertionError, match=r"nested wx\.App\.MainLoop"):
        run_bounded_main_loop(wx_app, wx_app.MainLoop, timeout_ms=1_000)


def test_bounded_real_main_loop_rejects_native_prompt(
    wx_app, native_frame, monkeypatch
) -> None:
    install_native_interaction_guard(monkeypatch)

    with pytest.raises(AssertionError, match="Unexpected native prompt"):
        run_bounded_main_loop(
            wx_app,
            lambda: wx.MessageBox("must not wait for a human"),
            timeout_ms=1_000,
        )


def test_bounded_real_main_loop_timeout_is_actionable(
    wx_app, native_frame, monkeypatch
) -> None:
    monkeypatch.setattr(wx, "CallAfter", lambda callback: None)

    with pytest.raises(AssertionError, match="timed out after 10 ms"):
        run_bounded_main_loop(wx_app, lambda: None, timeout_ms=10)
