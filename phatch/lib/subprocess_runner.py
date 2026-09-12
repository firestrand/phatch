from __future__ import annotations

import logging
import math
import subprocess
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Final, Protocol

from phatch.lib.process import (
    Command,
    ProcessCancelledError,
    ProcessExitError,
    ProcessLaunchError,
    ProcessResult,
    ProcessTimeoutError,
)


@dataclass(frozen=True, slots=True)
class RunnerOptions:
    poll_interval_seconds: float = 0.05
    termination_grace_seconds: float = 0.25

    def __post_init__(self) -> None:
        values = (self.poll_interval_seconds, self.termination_grace_seconds)
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise RunnerOptionsError("runner intervals must be finite and positive")


@dataclass(frozen=True, slots=True)
class RunnerOptionsError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


DEFAULT_RUNNER_OPTIONS: Final = RunnerOptions()


class _RunningProcess(Protocol):
    returncode: int | None

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def communicate(
        self,
        input: bytes | None = None,
        timeout: float | None = None,
    ) -> tuple[bytes, bytes]: ...


class StdlibProcessRunner:
    def __init__(
        self,
        options: RunnerOptions = DEFAULT_RUNNER_OPTIONS,
        logger: logging.Logger | None = None,
    ) -> None:
        self._options = options
        self._logger = logger

    def run(
        self,
        command: Command,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> ProcessResult:
        if cancelled is not None and cancelled():
            raise ProcessCancelledError(command)

        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command.argv,
                cwd=command.cwd,
                env=None if command.env is None else dict(command.env),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except OSError as error:
            raise ProcessLaunchError(command, str(error), error.errno) from error

        deadline = (
            None
            if command.timeout_seconds is None
            else started + command.timeout_seconds
        )
        while True:
            if cancelled is not None and cancelled():
                self._stop(process)
                raise ProcessCancelledError(command)

            wait_seconds = self._options.poll_interval_seconds
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._stop(process)
                    assert command.timeout_seconds is not None
                    raise ProcessTimeoutError(command, command.timeout_seconds)
                wait_seconds = min(wait_seconds, remaining)

            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=wait_seconds)
            except subprocess.TimeoutExpired:
                continue

            if cancelled is not None and cancelled():
                raise ProcessCancelledError(command)
            stdout = stdout_bytes.decode(command.encoding, errors="replace")
            stderr = stderr_bytes.decode(command.encoding, errors="replace")
            returncode = process.returncode
            assert returncode is not None
            duration = time.monotonic() - started
            if self._logger is not None:
                self._logger.debug(
                    "process completed",
                    extra={
                        "executable": command.argv[0],
                        "returncode": returncode,
                        "duration_seconds": duration,
                    },
                )
            if returncode not in command.accepted_returncodes:
                raise ProcessExitError(command, returncode, stdout, stderr)
            return ProcessResult(command, returncode, stdout, stderr)

    def _stop(self, process: _RunningProcess) -> None:
        try:
            process.terminate()
        except ProcessLookupError:
            process.communicate()
            return
        try:
            process.communicate(timeout=self._options.termination_grace_seconds)
        except subprocess.TimeoutExpired:
            with suppress(ProcessLookupError):
                process.kill()
            process.communicate()
