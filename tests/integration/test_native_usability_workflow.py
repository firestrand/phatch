from __future__ import annotations

import multiprocessing
import os
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.core.execution_types import ExecutionOutcome, FileOutcome
from tests.unit.pywx.native_popup_support import wait_until

wx = pytest.importorskip("wx")

pytestmark = [pytest.mark.acceptance, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_frame_support"]


def _set_action_field(frame, action_index: int, label: str, value: str) -> None:
    frame.tree.select_index(action_index)
    action_item = frame.tree.GetSelection()
    field_item = next(
        item
        for item in frame.tree.GetItemChildren(action_item)
        if frame.tree.GetItemData(item)[0] == label
    )
    transaction = frame.controller.begin_transaction()
    assert frame.tree.set_form_field_value(field_item, value)
    assert frame.controller.commit_transaction(transaction)


def _capture_native_window(window, destination: Path) -> None:
    window.Raise()
    wx.Yield()
    size = window.GetSize()
    position = window.GetScreenPosition()
    bitmap = wx.Bitmap(size.width, size.height)
    memory = wx.MemoryDC(bitmap)
    memory.Blit(
        0,
        0,
        size.width,
        size.height,
        wx.ScreenDC(),
        position.x,
        position.y,
    )
    memory.SelectObject(wx.NullBitmap)
    assert bitmap.SaveFile(str(destination), wx.BITMAP_TYPE_PNG)


def test_native_candidate_runs_complete_edit_preview_save_execute_workflow(
    native_frame_harness,
    tmp_path: Path,
) -> None:
    # Given: a deterministic source and a visible native editor frame
    frame = native_frame_harness.frame
    source = tmp_path / "source image.png"
    output_folder = tmp_path / "output folder; $(literal)"
    output_folder.mkdir()
    with Image.new("RGB", (12, 8), (20, 90, 160)) as image:
        image.save(source)
    source_hash = sha256(source.read_bytes()).hexdigest()
    evidence_root = Path(os.environ.get("PHATCH_TASK22_EVIDENCE", tmp_path))
    evidence_root.mkdir(parents=True, exist_ok=True)
    screenshot = evidence_root / "native-workflow-preview.png"

    # When: one native document is edited and previewed in a spawned worker
    frame.controller.add_action_by_label("Border")
    _set_action_field(frame, 0, "Border Width", "2px")
    frame.on_menu_tools_preview(None)
    preview = frame.preview_dialog
    assert preview is not None
    preview.set_source(source)
    preview.refresh.Command(
        wx.CommandEvent(wx.EVT_BUTTON.typeId, preview.refresh.GetId())
    )
    wait_until(lambda: preview.status.GetLabel() == "Preview ready.", timeout_ms=5000)
    _capture_native_window(preview, screenshot)

    # Then: preview is side-by-side, exact, non-writing, and fully joined
    assert preview.original.GetBitmap().IsOk()
    assert preview.result.GetBitmap().IsOk()
    assert "12 x 8" in preview.details.GetLabel()
    assert "16 x 12" in preview.details.GetLabel()
    assert "no output file is saved" in preview.details.GetLabel()
    assert sha256(source.read_bytes()).hexdigest() == source_hash
    assert not tuple(output_folder.iterdir())
    wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)

    # When: the same edit is undone, redone, saved, and loaded again
    frame.on_menu_edit_undo(None)
    undone = next(iter(frame.controller.export_actions())).get_field_string(
        "Border Width"
    )
    frame.on_menu_edit_redo(None)
    redone = next(iter(frame.controller.export_actions())).get_field_string(
        "Border Width"
    )
    frame.controller.add_action_by_label_to_last("Save")
    _set_action_field(frame, 1, "As", "PNG")
    _set_action_field(frame, 1, "In", str(output_folder))
    _set_action_field(frame, 1, "File Name", "result")
    action_list = tmp_path / "candidate workflow.phatch"
    frame._save(str(action_list))
    saved_hash = sha256(action_list.read_bytes()).hexdigest()
    frame._open(str(action_list))

    # Then: raw values and the clean checkpoint survive the lifecycle
    assert undone == "1px"
    assert redone == "2px"
    assert action_list.is_file()
    assert sha256(action_list.read_bytes()).hexdigest() == saved_hash
    assert (
        next(iter(frame.controller.export_actions())).get_field_string("Border Width")
        == "2px"
    )
    assert tuple(frame.controller.export_actions())[1].get_field_string("In") == str(
        output_folder
    )
    assert not frame.controller.state.dirty

    # When: the loaded native document executes through the real service
    result = frame._execute(frame.controller.export_actions(), paths=[str(source)])
    destination = output_folder / "result.PNG"

    # Then: one owned completion reports the exact surviving output
    assert result.outcome is ExecutionOutcome.COMPLETED
    assert result.counts.processed == 1
    assert result.counts.total == 1
    assert result.files[0].outcome is FileOutcome.PROCESSED
    assert result.files[0].source == source
    assert result.files[0].outputs[0].report.path == destination
    assert result.files[0].outputs[0].survived
    assert destination.is_file()
    with Image.open(destination) as output:
        assert output.size == (16, 12)
        assert output.getpixel((0, 0)) == (255, 255, 255)
    assert sha256(source.read_bytes()).hexdigest() == source_hash
    assert frame._last_completion.owner == "gui"
    assert frame._last_completion.request_id
    assert (
        len(
            [
                call
                for call in native_frame_harness.dialogs.calls
                if call[0] == "execution_result"
            ]
        )
        == 1
    )
    assert screenshot.is_file()
    assert screenshot.stat().st_size > 0
    preview.on_close()
    wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)
