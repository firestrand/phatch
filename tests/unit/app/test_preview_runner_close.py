from __future__ import annotations

import threading
import time
from concurrent.futures import Future
from pathlib import Path

import pytest

from phatch.core.user_paths import HostPlatform
from phatch.pyWx.preview_runner import PreviewRunner
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_types import (
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
    PreviewWorkerCancelled,
)


class Catalog:
    def action_label(self, action_id: str) -> str | None:
        return action_id

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return field_id

    def invalid_fields(self, spec) -> tuple[str, ...]:
        return ()


def test_close_joins_the_supervising_worker_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = threading.Event()
    finished = threading.Event()

    def run_until_cancelled(request, dependencies, generation, cancel):
        started.set()
        assert cancel.wait(timeout=1)
        time.sleep(0.05)
        finished.set()
        return PreviewWorkerCancelled(
            f"preview-{generation}",
            PreviewErrorCode.WORKER_CANCELLED,
            0,
        )

    resources = tmp_path / "resources"
    resources.mkdir()
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    monkeypatch.setattr(runner, "_run", run_until_cancelled)
    runner.submit(
        PreviewRequest(ActionDocument.from_values("", ()), tmp_path / "source.png"),
        PreviewDependencies(
            Catalog,
            ResourceProvider.from_root(resources),
            HostPlatform.MACOS,
        ),
        lambda generation, result: None,
    )
    assert started.wait(timeout=1)

    runner.close()

    assert finished.is_set()


def test_submit_after_close_fails_without_changing_generation(tmp_path: Path) -> None:
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    runner.close()
    generation = runner.generation

    with pytest.raises(RuntimeError, match="closed"):
        runner.submit(
            PreviewRequest(ActionDocument.from_values("", ()), tmp_path / "source.png"),
            PreviewDependencies(
                Catalog,
                ResourceProvider.from_root(tmp_path),
                HostPlatform.MACOS,
            ),
            lambda current_generation, result: None,
        )

    assert runner.generation == generation
    assert runner._cancelled_generations == set()


def test_cancelled_future_discards_generation_bookkeeping() -> None:
    runner = PreviewRunner(lambda callback, *args: callback(*args))
    future: Future = Future()
    future.cancel()
    runner._cancelled_generations.add(7)
    runner._active_generation = 7

    runner._schedule(future, 7, lambda generation, result: None)

    assert runner._cancelled_generations == set()
    assert runner._active_generation is None
    runner.close()
