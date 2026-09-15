from __future__ import annotations

import multiprocessing
import pickle
import time
from dataclasses import dataclass
from io import BytesIO
from multiprocessing.connection import Connection
from multiprocessing.process import BaseProcess
from typing import Final

from PIL import Image, UnidentifiedImageError

from phatch.services.preview_types import (
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewFileFingerprint,
    PreviewWorkerCancelled,
    PreviewWorkerFailure,
    PreviewWorkerRequest,
    PreviewWorkerResult,
    PreviewWorkerSuccess,
    SelectedPreviewRead,
)
from phatch.services.preview_worker import execute_preview_worker

_DEADLINE_SECONDS: float = 15.0
_TERMINATE_GRACE_SECONDS: Final = 2.0
_POLL_INTERVAL_SECONDS: Final = 0.01
_worker_entry = execute_preview_worker


class PreviewStartupError(OSError):
    __slots__ = ("reason", "request_id")

    def __init__(self, request_id: str, reason: str) -> None:
        super().__init__(reason)
        self.request_id = request_id
        self.reason = reason


@dataclass(slots=True)
class PreviewHandle:
    request_id: str
    _process: BaseProcess
    _receiver: Connection
    _deadline: float
    _max_payload_bytes: int
    _closed: bool = False
    _pending_result: PreviewWorkerResult | None = None

    @property
    def worker_pid(self) -> int:
        pid = self._process.pid
        if pid is None:
            raise PreviewStartupError(self.request_id, "preview process has no PID")
        return pid

    def poll(self, current_request_id: str | None = None) -> PreviewWorkerResult | None:
        if self._closed:
            return None
        if current_request_id is not None and current_request_id != self.request_id:
            return self._cancel(PreviewErrorCode.STALE_REQUEST)
        self._receive_available()
        if self._process.is_alive():
            if time.monotonic() >= self._deadline:
                return self._fail(
                    PreviewErrorCode.WORKER_TIMEOUT, "preview deadline exceeded"
                )
            return None
        self._process.join()
        self._receive_available()
        if self._pending_result is not None:
            if self._pending_result.request_id != self.request_id:
                return self._fail(
                    PreviewErrorCode.STALE_REQUEST,
                    "preview worker returned a mismatched request ID",
                )
            if (
                isinstance(self._pending_result, PreviewWorkerSuccess)
                and len(self._pending_result.image.data) > self._max_payload_bytes
            ):
                return self._fail(
                    PreviewErrorCode.MEMORY_LIMIT,
                    "preview result exceeds the IPC payload limit",
                )
            if isinstance(
                self._pending_result, PreviewWorkerSuccess
            ) and not _valid_payload(self._pending_result):
                return self._fail(
                    PreviewErrorCode.WORKER_FAILED,
                    "preview worker returned a corrupt image payload",
                )
            return self._finish(self._pending_result)
        return self._fail(
            PreviewErrorCode.WORKER_FAILED,
            f"preview worker exited with code {self._process.exitcode}",
        )

    def cancel(self) -> PreviewWorkerCancelled:
        return self._cancel(PreviewErrorCode.WORKER_CANCELLED)

    def _cancel(self, code: PreviewErrorCode) -> PreviewWorkerCancelled:
        pid = self.worker_pid
        self._stop()
        result = PreviewWorkerCancelled(self.request_id, code, pid)
        self._finish(result)
        return result

    def _fail(self, code: PreviewErrorCode, reason: str) -> PreviewWorkerFailure:
        pid = self.worker_pid
        self._stop()
        result = PreviewWorkerFailure(self.request_id, code, reason, pid)
        self._finish(result)
        return result

    def _stop(self) -> None:
        _stop_process(self._process)

    def _receive_available(self) -> None:
        if self._pending_result is not None or not self._receiver.poll():
            return
        try:
            result = self._receiver.recv()
        except (EOFError, OSError, pickle.UnpicklingError):
            return
        if isinstance(
            result,
            (PreviewWorkerSuccess, PreviewWorkerFailure, PreviewWorkerCancelled),
        ):
            self._pending_result = result

    def _finish(self, result: PreviewWorkerResult) -> PreviewWorkerResult:
        self._receiver.close()
        self._closed = True
        return result


def start_preview(spec: PreviewExecutionSpec, request_id: str) -> PreviewHandle:
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    selected = tuple(
        PreviewFileFingerprint(read.path, read.sha256)
        for read in spec.reads
        if isinstance(read, SelectedPreviewRead)
    )
    request = PreviewWorkerRequest(request_id, spec, selected)
    process = context.Process(target=_worker_entry, args=(request, sender))
    try:
        process.start()
    except OSError as error:
        sender.close()
        receiver.close()
        _stop_process(process)
        raise PreviewStartupError(request_id, str(error)) from error
    sender.close()
    return PreviewHandle(
        request_id,
        process,
        receiver,
        time.monotonic() + _DEADLINE_SECONDS,
        spec.limits.max_live_bytes,
    )


def run_preview(spec: PreviewExecutionSpec, request_id: str) -> PreviewWorkerResult:
    handle = start_preview(spec, request_id)
    while True:
        result = handle.poll(request_id)
        if result is not None:
            return result
        time.sleep(_POLL_INTERVAL_SECONDS)


def _stop_process(process: BaseProcess) -> None:
    if process.pid is None:
        return
    if process.is_alive():
        process.terminate()
        process.join(_TERMINATE_GRACE_SECONDS)
    if process.is_alive():
        process.kill()
        process.join(_TERMINATE_GRACE_SECONDS)
    if not process.is_alive():
        process.join()


def _valid_payload(result: PreviewWorkerSuccess) -> bool:
    try:
        with Image.open(BytesIO(result.image.data)) as image:
            dimensions_match = image.size == (
                result.image.width,
                result.image.height,
            )
            mode_matches = image.mode == result.image.mode
            format_matches = image.format == result.image.format_name
            image.verify()
    except (OSError, SyntaxError, UnidentifiedImageError):
        return False
    return dimensions_match and mode_matches and format_matches
