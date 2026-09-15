from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Protocol, TypeAlias, assert_never

from phatch.services.preview import admit_preview, start_preview
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
    PreviewWorkerCancelled,
    PreviewWorkerFailure,
    PreviewWorkerResult,
    PreviewWorkerSuccess,
)

PreviewResult: TypeAlias = PreviewWorkerResult | PreviewAdmissionError
PreviewCallback: TypeAlias = Callable[[int, PreviewResult], None]
Scheduler: TypeAlias = Callable[..., None]


class PreviewJobRunner(Protocol):
    def submit(
        self,
        request: PreviewRequest,
        dependencies: PreviewDependencies,
        callback: PreviewCallback,
    ) -> int: ...

    def cancel(self) -> None: ...

    def close(self) -> None: ...


class PreviewRunner:
    def __init__(self, scheduler: Scheduler) -> None:
        self._scheduler = scheduler
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="preview")
        self._generation = 0
        self._cancel = threading.Event()
        self._active_generation: int | None = None
        self._cancelled_generations: set[int] = set()
        self._state_lock = threading.Lock()
        self._closed = False

    @property
    def generation(self) -> int:
        return self._generation

    def submit(
        self,
        request: PreviewRequest,
        dependencies: PreviewDependencies,
        callback: PreviewCallback,
    ) -> int:
        with self._state_lock:
            if self._closed:
                raise RuntimeError("preview runner is closed")
            self._cancel_current()
            self._generation += 1
            generation = self._generation
            self._cancel = threading.Event()
            self._active_generation = generation
            future = self._executor.submit(
                self._run, request, dependencies, generation, self._cancel
            )
        future.add_done_callback(
            lambda completed: self._schedule(completed, generation, callback)
        )
        return generation

    def cancel(self) -> None:
        with self._state_lock:
            self._cancel_current()
            self._generation += 1

    def close(self) -> None:
        with self._state_lock:
            self._closed = True
            self._cancel_current()
            self._generation += 1
        self._executor.shutdown(wait=True, cancel_futures=True)
        with self._state_lock:
            self._active_generation = None
            self._cancelled_generations.clear()

    def _cancel_current(self) -> None:
        if self._active_generation is not None:
            self._cancel.set()
            self._cancelled_generations.add(self._active_generation)
            self._active_generation = None

    @staticmethod
    def _run(
        request: PreviewRequest,
        dependencies: PreviewDependencies,
        generation: int,
        cancel: threading.Event,
    ) -> PreviewResult:
        try:
            specification = admit_preview(request, dependencies)
        except PreviewAdmissionError as error:
            return error
        request_id = f"preview-{generation}"
        if cancel.is_set():
            return PreviewWorkerCancelled(
                request_id, PreviewErrorCode.WORKER_CANCELLED, 0
            )
        try:
            handle = start_preview(specification, request_id)
        except OSError:
            return PreviewWorkerFailure(
                request_id,
                PreviewErrorCode.WORKER_FAILED,
                "The preview worker could not be started.",
                0,
            )
        while True:
            if cancel.is_set():
                return handle.cancel()
            result = handle.poll(handle.request_id)
            if result is not None:
                return result
            time.sleep(0.01)

    def _schedule(
        self,
        future: Future[PreviewResult],
        generation: int,
        callback: PreviewCallback,
    ) -> None:
        if future.cancelled():
            with self._state_lock:
                self._cancelled_generations.discard(generation)
                if self._active_generation == generation:
                    self._active_generation = None
            return
        match future.exception():
            case None:
                result = future.result()
            case Exception():
                result = PreviewWorkerFailure(
                    f"preview-{generation}",
                    PreviewErrorCode.WORKER_FAILED,
                    "The preview worker failed unexpectedly.",
                    0,
                )
            case BaseException() as interrupt:
                raise interrupt
        with self._state_lock:
            if self._closed:
                return
            if (
                generation != self._generation
                and generation not in self._cancelled_generations
            ):
                return
        self._scheduler(self._deliver, callback, generation, result)

    def _deliver(
        self,
        callback: PreviewCallback,
        generation: int,
        result: PreviewResult,
    ) -> None:
        with self._state_lock:
            if self._closed:
                return
            cancelled = generation in self._cancelled_generations
            self._cancelled_generations.discard(generation)
            if self._active_generation == generation:
                self._active_generation = None
            if not cancelled and generation != self._generation:
                return
            if cancelled:
                match result:
                    case PreviewAdmissionError():
                        result = PreviewWorkerCancelled(
                            f"preview-{generation}",
                            PreviewErrorCode.WORKER_CANCELLED,
                            0,
                        )
                    case PreviewWorkerSuccess() | PreviewWorkerFailure() as completed:
                        result = PreviewWorkerCancelled(
                            completed.request_id,
                            PreviewErrorCode.WORKER_CANCELLED,
                            completed.worker_pid,
                        )
                    case PreviewWorkerCancelled():
                        pass
                    case unreachable:
                        assert_never(unreachable)
        callback(generation, result)
