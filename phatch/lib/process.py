from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CommandValidationError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class Command:
    argv: tuple[str, ...]
    cwd: Path | None = None
    env: tuple[tuple[str, str], ...] | None = None
    timeout_seconds: float | None = None
    accepted_returncodes: frozenset[int] = frozenset({0})
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if type(self.argv) is not tuple:
            raise CommandValidationError("argv must be a tuple of strings")
        if not self.argv or not self.argv[0]:
            raise CommandValidationError("argv must contain an executable")
        if any(type(argument) is not str for argument in self.argv):
            raise CommandValidationError("argv must contain only strings")
        if any("\0" in argument for argument in self.argv):
            raise CommandValidationError("argv must not contain NUL characters")
        if self.env is not None:
            if type(self.env) is not tuple:
                raise CommandValidationError("environment must be an immutable tuple")
            self._validate_environment()
        if self.timeout_seconds is not None and (
            not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0
        ):
            raise CommandValidationError("timeout must be finite and positive")
        if not self.accepted_returncodes:
            raise CommandValidationError("accepted return codes must not be empty")
        if any(type(code) is not int for code in self.accepted_returncodes):
            raise CommandValidationError("accepted return codes must be integers")
        if not self.encoding:
            raise CommandValidationError("encoding must not be empty")

    def _validate_environment(self) -> None:
        assert self.env is not None
        keys: set[str] = set()
        for entry in self.env:
            if type(entry) is not tuple or len(entry) != 2:
                raise CommandValidationError(
                    "environment entries must be key/value pairs"
                )
            key, value = entry
            if type(key) is not str or type(value) is not str:
                raise CommandValidationError(
                    "environment keys and values must be strings"
                )
            if not key or "=" in key or "\0" in key or "\0" in value:
                raise CommandValidationError("environment contains an invalid entry")
            if key in keys:
                raise CommandValidationError(f"duplicate environment key: {key}")
            keys.add(key)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: Command
    returncode: int
    stdout: str
    stderr: str


class ProcessError(Exception):
    command: Command

    def __init__(self, command: Command) -> None:
        super().__init__()
        self.command = command


class ProcessLaunchError(ProcessError):
    reason: str
    errno: int | None

    def __init__(self, command: Command, reason: str, errno: int | None) -> None:
        super().__init__(command)
        self.reason = reason
        self.errno = errno

    def __str__(self) -> str:
        return f"could not launch {self.command.argv[0]}: {self.reason}"


class ProcessExitError(ProcessError):
    returncode: int
    stdout: str
    stderr: str

    def __init__(
        self,
        command: Command,
        returncode: int,
        stdout: str,
        stderr: str,
    ) -> None:
        super().__init__(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __str__(self) -> str:
        return f"{self.command.argv[0]} exited with status {self.returncode}"


class ProcessTimeoutError(ProcessError):
    timeout_seconds: float

    def __init__(self, command: Command, timeout_seconds: float) -> None:
        super().__init__(command)
        self.timeout_seconds = timeout_seconds

    def __str__(self) -> str:
        return (
            f"{self.command.argv[0]} timed out after {self.timeout_seconds:g} seconds"
        )


class ProcessCancelledError(ProcessError):
    def __str__(self) -> str:
        return f"{self.command.argv[0]} was cancelled"


class ProcessRunner(Protocol):
    def run(
        self,
        command: Command,
        *,
        cancelled: Callable[[], bool] | None = None,
    ) -> ProcessResult: ...
