from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never


@dataclass(frozen=True, slots=True)
class ChildProcessProbe:
    pid: int


class TerminationBehavior(StrEnum):
    COOPERATIVE = "cooperative"
    IGNORE_TERMINATE = "ignore-terminate"


@dataclass(frozen=True, slots=True)
class ProcessCleanup:
    pid: int
    returncode: int
    forced: bool


def pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def spawn_child_process(behavior: TerminationBehavior) -> subprocess.Popen[bytes]:
    match behavior:
        case TerminationBehavior.COOPERATIVE:
            child_code = "; ".join(
                (
                    "import sys",
                    "print('ready', flush=True)",
                    "sys.stdin.buffer.read(1)",
                )
            )
        case TerminationBehavior.IGNORE_TERMINATE:
            child_code = "import time; print('ready', flush=True); time.sleep(60)"
        case unreachable:
            assert_never(unreachable)
    process = subprocess.Popen(
        [sys.executable, "-c", child_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    stdout = process.stdout
    assert stdout is not None
    stdout.readline()
    return process


def cleanup_child_process(
    process: subprocess.Popen[bytes], timeout_seconds: float
) -> ProcessCleanup:
    returncode = process.poll()
    if returncode is not None:
        return ProcessCleanup(process.pid, returncode, False)
    stdin = process.stdin
    assert stdin is not None
    stdin.write(b"stop")
    stdin.flush()
    stdin.close()
    try:
        returncode = process.wait(timeout=timeout_seconds)
        return ProcessCleanup(process.pid, returncode, False)
    except subprocess.TimeoutExpired:
        process.kill()
        return ProcessCleanup(process.pid, process.wait(timeout=2), True)


@contextmanager
def child_process_probe() -> Iterator[ChildProcessProbe]:
    process = spawn_child_process(TerminationBehavior.COOPERATIVE)
    try:
        yield ChildProcessProbe(process.pid)
    finally:
        cleanup_child_process(process, timeout_seconds=2)
