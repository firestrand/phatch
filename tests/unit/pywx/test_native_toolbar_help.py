from __future__ import annotations

import pytest

from .native_frame_support import native_frame_harness, native_runtime

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
__all__ = ["native_frame_harness", "native_runtime"]


def test_toolbar_icons_explain_their_actions_on_hover(native_frame_harness) -> None:
    # Given: the real action-list frame and its native toolbar.
    frame = native_frame_harness.frame
    toolbar = frame.frame_toolbar

    # When: the platform requests the hover help attached to each icon.
    help_by_label = {
        toolbar.FindById(tool_id).GetLabel(): toolbar.GetToolShortHelp(tool_id)
        for tool_id in frame.tools_all
    }

    # Then: every icon explains its effect without relying on the icon alone.
    assert help_by_label == {
        "Open": "Open a saved list of image-processing steps.",
        "Execute": "Choose photos and run all enabled actions in this list.",
        "Add": "Add an image-processing step, such as resize or rotate.",
        "Remove": "Remove the selected action from the list, not your photos.",
        "Up": "Move the selected action earlier in the processing order.",
        "Down": "Move the selected action later in the processing order.",
        "Image Inspector": "View photo details and camera metadata (EXIF and IPTC).",
        "Description": "Show or hide notes describing what this action list does.",
    }
