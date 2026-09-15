from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from phatch.services import preview_process
from phatch.services.preview import run_preview
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewErrorCode,
    PreviewReadContext,
    PreviewWorkerFailure,
    PreviewWorkerSuccess,
    SelectedPreviewRead,
)
from tests.unit.core.test_preview_worker import (
    _large_result_worker,
    _pid_exists,
    _spawn_source,
    _spec,
)


def test_canvas_over_pixel_limit_is_rejected_before_allocation(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    action = PreviewActionSpec(
        "canvas",
        (("canvas_width", "4000px"), ("canvas_height", "4000px")),
    )

    result = run_preview(_spec(source, (action,)), "too-large")

    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is PreviewErrorCode.PIXEL_LIMIT
    assert not _pid_exists(result.worker_pid)


def test_parent_drains_large_result_before_waiting_for_child(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    monkeypatch.setattr(preview_process, "_worker_entry", _large_result_worker)

    result = run_preview(_spec(source, ()), "large-result")

    assert isinstance(result, PreviewWorkerSuccess)
    assert len(result.image.data) > 64 * 1024
    assert not _pid_exists(result.worker_pid)


def test_worker_rechecks_selected_read_fingerprint(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    selected = tmp_path / "mark.png"
    _spawn_source(source)
    _spawn_source(selected)
    original = _spec(source, ())
    fingerprint = sha256(selected.read_bytes()).hexdigest()
    read = SelectedPreviewRead(0, "mark", selected, fingerprint)
    spec = replace(
        original,
        reads=(read,),
        context=PreviewReadContext(original.source, (read,)),
    )
    selected.write_bytes(b"changed after admission")

    result = run_preview(spec, "changed-read")

    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is PreviewErrorCode.SOURCE_CHANGED
    assert not _pid_exists(result.worker_pid)


def test_worker_rejects_read_action_without_admitted_binding(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    _spawn_source(source)
    action = PreviewActionSpec("watermark", (("mark", str(source)),))

    result = run_preview(_spec(source, (action,)), "undeclared-read")

    assert isinstance(result, PreviewWorkerFailure)
    assert result.code is PreviewErrorCode.UNDECLARED_READ
    assert not _pid_exists(result.worker_pid)
