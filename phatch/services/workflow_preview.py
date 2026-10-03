# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned preview worker with latest-request delivery on the UI dispatcher."""

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import threading
from typing import Any

from phatch.core.batch import Failure
from phatch.core.workflow_preview import (
    PreviewAction,
    PreviewOptions,
    PreviewRenderer,
    PreviewResult,
    preview_safe,
    snapshot_actions,
)


class WorkflowPreviewService:
    """At most one running render and one queued latest request.

    The dispatcher receives a no-argument callable (wx.CallAfter is suitable).
    Delivery checks generation again after dispatch, so queued UI callbacks
    cannot display stale results. Close suppresses all subsequent delivery.
    """

    def __init__(
        self,
        dispatch: Callable[[Callable[[], None]], Any],
        *,
        renderer: PreviewRenderer | None = None,
    ) -> None:
        self._dispatch = dispatch
        self._renderer = renderer or PreviewRenderer()
        self._executor = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix='phatch-preview'
        )
        self._lock = threading.RLock()
        self._generation = 0
        self._closed = False
        self._cancel = threading.Event()
        self._future: Future[PreviewResult] | None = None
        self._pending: Callable[[], None] | None = None
        self._running = False

    def submit(
        self,
        source: Path | str,
        actions: Sequence[PreviewAction],
        callback: Callable[[PreviewResult], None],
        options: PreviewOptions | None = None,
        settings: Mapping[str, Any] | None = None,
    ) -> int:
        """Snapshot parameters on the caller thread and supersede older work."""
        with self._lock:
            if self._closed:
                raise RuntimeError('Preview service is closed')
            self._generation += 1
            generation = self._generation
            self._cancel.set()
            if self._future:
                self._future.cancel()
            self._pending = None
            cancellation = self._cancel = threading.Event()
            skipped = ()
            try:
                snapshots = snapshot_actions(actions)
                skipped = tuple(
                    action.label
                    for action in snapshots
                    if not preview_safe(action)
                )
                safe = [action for action in snapshots if preview_safe(action)]
                settings = deepcopy(dict(settings or {}))
            except (
                Exception
            ) as exc:  # Isolate custom form serialization failures.
                future = Future()
                future.set_result(
                    PreviewResult(
                        'failed',
                        failure=Failure(
                            'Preview setup', type(exc).__name__, str(exc)
                        ),
                    )
                )
            else:
                future = Future()

                def render_job() -> None:
                    if not future.set_running_or_notify_cancel():
                        return
                    try:
                        rendered = self._renderer.render(
                            source,
                            safe,
                            options,
                            settings,
                            cancel=cancellation.is_set,
                        )
                    except (
                        Exception
                    ) as exc:  # Each render owns its failure result.
                        future.set_exception(exc)
                    else:
                        future.set_result(rendered)

                # Coalesce before the executor queue: cancelling a Future alone
                # would retain old snapshots until its queued WorkItem is drained.
                self._pending = render_job
            self._future = future
            future.add_done_callback(
                lambda completed: self._completed(
                    generation, cancellation, completed, callback, skipped
                )
            )
            if self._pending is not None and not self._running:
                self._running = True
                self._executor.submit(self._drain)
            return generation

    def _drain(self) -> None:
        while True:
            with self._lock:
                job = self._pending
                self._pending = None
                if self._closed or job is None:
                    self._running = False
                    return
            job()

    def _completed(
        self,
        generation: int,
        cancellation: threading.Event,
        future: Future[PreviewResult],
        callback: Callable[[PreviewResult], None],
        skipped: tuple[str, ...],
    ) -> None:
        try:
            result = future.result()
        except CancelledError:
            return
        except (
            Exception
        ) as exc:  # Supervise any worker failure before UI dispatch.
            result = PreviewResult(
                'failed',
                failure=Failure('Preview', type(exc).__name__, str(exc)),
            )
        result = replace(result, skipped=skipped + result.skipped)
        with self._lock:
            if (
                self._closed
                or generation != self._generation
                or cancellation.is_set()
            ):
                return

        def deliver() -> None:
            with self._lock:
                if (
                    self._closed
                    or generation != self._generation
                    or cancellation.is_set()
                ):
                    return
                callback(result)

        self._dispatch(deliver)

    def invalidate(self) -> None:
        """Cancel and suppress delivery when source or workflow parameters change."""
        with self._lock:
            self._generation += 1
            self._cancel.set()
            if self._future:
                self._future.cancel()
            self._pending = None

    def close(self, *, wait: bool = True) -> None:
        """Cancel queued work, request cooperative stop and own worker shutdown."""
        with self._lock:
            self._closed = True
            self.invalidate()
        self._executor.shutdown(wait=wait, cancel_futures=True)

    def __enter__(self) -> 'WorkflowPreviewService':
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
