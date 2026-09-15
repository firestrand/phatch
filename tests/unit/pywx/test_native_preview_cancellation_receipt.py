from __future__ import annotations

import json
import multiprocessing
import sys
from pathlib import Path

import pytest
import wx
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.pyWx.preview_panel import PreviewPanel
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import PreviewDependencies
from tests.unit.pywx.native_popup_support import wait_until
from tests.usability_fixtures import pid_exists

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]
pytest_plugins = ["tests.unit.pywx.native_popup_support"]


class FixtureCatalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


def test_five_consecutive_cancellations_join_before_terminal_state(
    native_frame: wx.Frame,
    tmp_path: Path,
) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    dependencies = PreviewDependencies(
        lambda: FixtureCatalog(),
        ResourceProvider.from_root(resources),
        HostPlatform.MACOS,
    )

    for cycle in range(1, 6):
        source = tmp_path / f"cancel-preview-{cycle}.png"
        Image.new("RGB", (4000, 2000), "navy").save(source)
        panel = PreviewPanel(
            native_frame,
            lambda: ActionDocument.from_values("", ()),
            dependencies,
        )
        panel.Show()
        panel.set_source(source)
        panel.refresh.Command(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, panel.refresh.GetId())
        )
        wait_until(lambda: bool(multiprocessing.active_children()), timeout_ms=5000)
        worker_pids = tuple(
            process.pid for process in multiprocessing.active_children()
        )

        panel.cancel.Command(
            wx.CommandEvent(wx.EVT_BUTTON.typeId, panel.cancel.GetId())
        )
        cancelling_label = panel.status.GetLabel()
        wait_until(lambda: not multiprocessing.active_children(), timeout_ms=5000)
        wait_until(
            lambda current_panel=panel: (
                current_panel.status.GetLabel() == "Preview cancelled."
            ),
            timeout_ms=5000,
        )
        receipt = {
            "cycle": cycle,
            "worker_pids": worker_pids,
            "cancelling_label": cancelling_label,
            "joined": all(
                pid is not None and not pid_exists(pid) for pid in worker_pids
            ),
            "active_children": tuple(
                process.pid for process in multiprocessing.active_children()
            ),
            "terminal_label": panel.status.GetLabel(),
            "choose_enabled": panel.choose.IsEnabled(),
            "refresh_enabled": panel.refresh.IsEnabled(),
            "cancel_enabled": panel.cancel.IsEnabled(),
            "result_bitmap_ok": panel.result.GetBitmap().IsOk(),
            "pending_notification_collected": (
                panel.status.GetLabel() == "Preview cancelled."
            ),
        }
        sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")

        assert receipt["cancelling_label"] == "Cancelling preview..."
        assert receipt["joined"]
        assert receipt["active_children"] == ()
        assert receipt["pending_notification_collected"]
        assert receipt["terminal_label"] == "Preview cancelled."
        assert receipt["choose_enabled"]
        assert receipt["refresh_enabled"]
        assert not receipt["cancel_enabled"]
        assert not receipt["result_bitmap_ok"]
        panel.on_close()
