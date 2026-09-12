from __future__ import annotations

from collections.abc import Iterator

import pytest

pytest.importorskip("wx")
import wx

from phatch.lib.pyWx import popup
from phatch.other.pyWx import TextCtrlAutoComplete as autocomplete_module

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


@pytest.fixture
def autocomplete_demo(native_interaction) -> Iterator[autocomplete_module.test]:
    native_interaction.expect_main_loop()
    demo = autocomplete_module.test()
    yield demo
    app = native_interaction.main_loop_apps[-1]
    app.GetTopWindow().Destroy()
    wx.Yield()
    app.Destroy()


def test_popup_example_builds_real_controls_without_blocking(native_interaction):
    # Given
    native_interaction.expect_main_loop()

    # When
    popup.example()

    # Then
    app = native_interaction.main_loop_apps[-1]
    frame = app.GetTopWindow()
    editors = [
        child
        for child in frame.GetChildren()
        if isinstance(child, popup.EditPanel)
    ]
    assert frame.IsShown()
    assert len(editors) >= 8
    assert all(editor.edit for editor in editors)
    frame.Destroy()
    wx.Yield()
    app.Destroy()


def test_autocomplete_example_builds_real_control_and_buttons(autocomplete_demo):
    # Given / When
    control = autocomplete_demo._ctrl
    frame = wx.GetTopLevelParent(control)
    panel = frame.GetChildren()[0]

    # Then
    assert isinstance(control, autocomplete_module.TextCtrlAutoComplete)
    assert control.dropdownlistbox.GetItemCount() == 6
    buttons = [
        child for child in panel.GetChildren() if isinstance(child, wx.Button)
    ]
    assert len(buttons) == 4


def test_autocomplete_example_switches_choice_shapes_on_real_list(autocomplete_demo):
    # Given
    event = wx.CommandEvent(wx.EVT_BUTTON.typeId)

    # When
    autocomplete_demo.onBtMultiChoice(event)
    multi_columns = autocomplete_demo._ctrl.dropdownlistbox.GetColumnCount()
    autocomplete_demo.onBtChangeChoice(event)

    # Then
    assert multi_columns == 2
    assert autocomplete_demo._ctrl.GetChoices() == [
        "123",
        "Alpha",
        "Bob",
        "cds",
        "cs",
        "Marley",
    ]


@pytest.mark.parametrize(
    ("text", "choice", "expected"),
    [
        ("alpha", "Alpha", True),
        ("python", "http://python.org", True),
        ("wx", "www.wxPython.org", True),
        ("missing", "http://python.org", False),
    ],
)
def test_autocomplete_example_matches_supported_prefixes(
    autocomplete_demo, text, choice, expected
):
    # Given / When
    result = autocomplete_demo.match(text, choice)

    # Then
    assert result is expected


def test_autocomplete_example_updates_dynamic_choices_only_when_changed(
    autocomplete_demo,
):
    # Given
    autocomplete_demo.onBtDynamicChoices(wx.CommandEvent(wx.EVT_BUTTON.typeId))
    autocomplete_demo._ctrl.SetValue("ae")

    # When
    autocomplete_demo.setDynamicChoices()
    first_choices = autocomplete_demo._ctrl.GetChoices()
    autocomplete_demo.setDynamicChoices()

    # Then
    assert first_choices == ["aegis"]
    assert autocomplete_demo._ctrl.GetChoices() == ["aegis"]
