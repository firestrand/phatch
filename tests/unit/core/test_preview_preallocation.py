from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

import pytest
from PIL import Image

from phatch.services import preview_process, preview_worker
from phatch.services.preview import run_preview
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
    PreviewWorkerFailure,
)


class AllocationGuardAction:
    def __init__(self, action_id: str, marker: Path) -> None:
        self.action_id = action_id
        self.marker = marker

    def values(self, info):
        if self.action_id == "canvas":
            return {"new_size": (100_000, 100_000)}
        if self.action_id == "crop":
            return {"mode": "All", "all": -100_000}
        return {}

    def get_field(self, label, info):
        fields = {
            "Resolution": 72,
            "Canvas Width": 100_000,
            "Canvas Height": 100_000,
            "Scale Down Only": False,
            "Constrain Proportions": False,
        }
        return fields[label]

    def get_field_size(self, label, info, reference, dpi):
        return self.get_field(label, info)

    def apply(self, photo, settings, cache):
        self.marker.write_text("allocated", encoding="utf-8")
        return photo


def _allocation_guard_worker(request, connection) -> None:
    action_id = request.spec.actions[0].action_id
    marker = Path(dict(request.spec.actions[0].fields)["marker"])
    original = preview_worker.construct_preview_actions
    preview_worker.construct_preview_actions = lambda _specs, _fields: (
        AllocationGuardAction(action_id, marker),
    )
    try:
        preview_worker.execute_preview_worker(request, connection)
    finally:
        preview_worker.construct_preview_actions = original


def _spec(source_path: Path, action_id: str, marker: Path) -> PreviewExecutionSpec:
    source = PreviewSource(
        source_path,
        sha256(source_path.read_bytes()).hexdigest(),
        PreviewSize(31, 23),
        "RGB",
        "PNG",
    )
    return PreviewExecutionSpec(
        (PreviewActionSpec(action_id, (("marker", str(marker)),)),),
        source,
        (),
        ("size", "dpi"),
        PreviewLimits(),
        PreviewReadContext(source, ()),
        False,
    )


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.parametrize("action_id", ["scale", "canvas", "crop"])
def test_growth_is_rejected_before_action_allocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    action_id: str,
) -> None:
    source = tmp_path / "source.png"
    marker = tmp_path / "allocation.txt"
    with Image.new("RGB", (31, 23), "navy") as image:
        image.save(source)
    monkeypatch.setattr(preview_process, "_worker_entry", _allocation_guard_worker)

    result = run_preview(_spec(source, action_id, marker), f"guard-{action_id}")

    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is PreviewErrorCode.PIXEL_LIMIT
    assert not marker.exists()
    assert not _pid_exists(result.worker_pid)
