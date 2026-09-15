from __future__ import annotations

from pathlib import Path

from tests.usability_fixtures import (
    TerminationBehavior,
    build_output_layout,
    cleanup_child_process,
    pid_exists,
    spawn_child_process,
)


def test_output_layout_models_interrupted_and_rolled_back_multi_output_state(
    tmp_path: Path,
) -> None:
    # Given / When
    layout = build_output_layout(tmp_path)

    # Then
    assert len({path.parent for path in layout.outputs}) == 2
    assert tuple(path.read_bytes() for path in layout.preexisting_outputs) == (
        b"previous-output-a",
        b"previous-output-b",
    )
    assert tuple(path.read_bytes() for path in layout.staged_outputs) == (
        b"new-output-a",
        b"new-output-b",
    )
    assert tuple(path.read_bytes() for path in layout.backup_outputs) == (
        b"previous-output-a",
        b"previous-output-b",
    )
    assert layout.rollback_survivors == layout.preexisting_outputs
    assert layout.rollback_removed == (*layout.staged_outputs, *layout.backup_outputs)


def test_cleanup_child_process_reports_cooperative_termination() -> None:
    # Given
    process = spawn_child_process(TerminationBehavior.COOPERATIVE)
    child_pid = process.pid

    # When
    try:
        cleanup = cleanup_child_process(process, timeout_seconds=0.25)
    finally:
        if pid_exists(child_pid):
            process.kill()
            process.wait(timeout=2)

    # Then
    assert cleanup.forced is False
    assert cleanup.pid == child_pid
    assert not pid_exists(child_pid)


def test_cleanup_child_process_reports_forced_kill_after_timeout() -> None:
    # Given
    process = spawn_child_process(TerminationBehavior.IGNORE_TERMINATE)
    child_pid = process.pid

    # When
    try:
        cleanup = cleanup_child_process(process, timeout_seconds=0.05)
    finally:
        if pid_exists(child_pid):
            process.kill()
            process.wait(timeout=2)

    # Then
    assert cleanup.forced is True
    assert cleanup.pid == child_pid
    assert not pid_exists(child_pid)
