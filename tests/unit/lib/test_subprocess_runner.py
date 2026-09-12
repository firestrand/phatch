from __future__ import annotations

import errno
import subprocess
import sys
from pathlib import Path

import pytest

from phatch.lib.process import (
    Command,
    ProcessCancelledError,
    ProcessExitError,
    ProcessLaunchError,
    ProcessTimeoutError,
)
from phatch.lib.subprocess_runner import (
    RunnerOptions,
    RunnerOptionsError,
    StdlibProcessRunner,
)


def python_command(source: str, *arguments: str, **options) -> Command:
    return Command(argv=(sys.executable, "-c", source, *arguments), **options)


def test_runner_passes_literal_arguments_and_decodes_unicode(tmp_path: Path) -> None:
    command = python_command(
        "import os,sys; print(os.getcwd()); print(os.environ['PHATCH_TEST']); "
        "print('|'.join(sys.argv[1:]))",
        "semi;colon",
        "snowman-☃",
        cwd=tmp_path,
        env=(("PHATCH_TEST", "välue"),),
    )

    result = StdlibProcessRunner().run(command)

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        str(tmp_path),
        "välue",
        "semi;colon|snowman-☃",
    ]


def test_runner_captures_large_streams_without_deadlock() -> None:
    command = python_command(
        "import sys; sys.stdout.write('o' * 100000); sys.stderr.write('e' * 100000)"
    )

    result = StdlibProcessRunner().run(command)

    assert len(result.stdout) == len(result.stderr) == 100000


def test_runner_uses_explicit_replacement_decoding() -> None:
    command = python_command("import os; os.write(1, b'bad\\xff')")

    assert StdlibProcessRunner().run(command).stdout == "bad�"


def test_runner_raises_typed_error_for_nonzero_status() -> None:
    command = python_command(
        "import sys; print('out'); print('bad', file=sys.stderr); raise SystemExit(7)"
    )

    with pytest.raises(ProcessExitError) as captured:
        StdlibProcessRunner().run(command)

    assert captured.value.returncode == 7
    assert captured.value.stdout == "out\n"
    assert captured.value.stderr == "bad\n"


def test_runner_accepts_an_explicit_nonzero_status() -> None:
    command = python_command(
        "raise SystemExit(3)", accepted_returncodes=frozenset({0, 3})
    )

    assert StdlibProcessRunner().run(command).returncode == 3


def test_runner_wraps_missing_executable() -> None:
    command = Command(argv=("/definitely/missing/phatch-tool",))

    with pytest.raises(ProcessLaunchError) as captured:
        StdlibProcessRunner().run(command)

    assert captured.value.command is command
    assert captured.value.errno == errno.ENOENT


def test_runner_times_out_and_reaps_child() -> None:
    command = python_command("import time; time.sleep(10)", timeout_seconds=0.02)
    runner = StdlibProcessRunner(RunnerOptions(poll_interval_seconds=0.005))

    with pytest.raises(ProcessTimeoutError):
        runner.run(command)


def test_runner_honors_prelaunch_and_running_cancellation() -> None:
    command = python_command("import time; time.sleep(10)")
    runner = StdlibProcessRunner(RunnerOptions(poll_interval_seconds=0.005))

    with pytest.raises(ProcessCancelledError):
        runner.run(command, cancelled=lambda: True)

    checks = 0

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks > 2

    with pytest.raises(ProcessCancelledError):
        runner.run(command, cancelled=cancelled)


def test_runner_checks_cancellation_before_returning_success() -> None:
    checks = 0

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks > 2

    with pytest.raises(ProcessCancelledError):
        StdlibProcessRunner().run(python_command("pass"), cancelled=cancelled)


def test_runner_routes_completion_details_to_supplied_logger(caplog) -> None:
    import logging

    logger = logging.getLogger("phatch.tests.process")
    with caplog.at_level(logging.DEBUG, logger=logger.name):
        StdlibProcessRunner(logger=logger).run(python_command("pass"))

    record = caplog.records[-1]
    assert record.executable == sys.executable
    assert record.returncode == 0


def test_runner_escalates_from_terminate_to_kill(monkeypatch) -> None:
    class ResistantProcess:
        returncode: int | None = None
        terminated = False
        killed = False
        communicate_calls = 0

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True

        def communicate(self, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls == 1:
                import subprocess

                wait_seconds = 0.0 if timeout is None else timeout
                raise subprocess.TimeoutExpired(("tool",), wait_seconds)
            return b"", b""

    process = ResistantProcess()
    StdlibProcessRunner()._stop(process)

    assert process.terminated
    assert process.killed
    assert process.communicate_calls == 2


def test_runner_preserves_cancellation_when_terminate_loses_exit_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExitedProcess:
        returncode: int | None = 0
        communicate_calls = 0

        def terminate(self) -> None:
            raise ProcessLookupError

        def kill(self) -> None:
            raise AssertionError("kill must not follow a lost terminate race")

        def communicate(self, input=None, timeout=None):
            self.communicate_calls += 1
            return b"", b""

    process = ExitedProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    checks = iter((False, True))

    with pytest.raises(ProcessCancelledError):
        StdlibProcessRunner().run(Command(("tool",)), cancelled=lambda: next(checks))

    assert process.communicate_calls == 1


def test_runner_preserves_timeout_when_kill_loses_exit_race(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ExitingProcess:
        returncode: int | None = 0
        terminated = False
        killed = False
        communicate_calls = 0

        def terminate(self) -> None:
            self.terminated = True

        def kill(self) -> None:
            self.killed = True
            raise ProcessLookupError

        def communicate(self, input=None, timeout=None):
            self.communicate_calls += 1
            if self.communicate_calls < 3:
                wait_seconds = 0.0 if timeout is None else timeout
                raise subprocess.TimeoutExpired(("tool",), wait_seconds)
            return b"", b""

    process = ExitingProcess()
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: process)
    monotonic = iter((0.0, 0.0, 1.0))
    monkeypatch.setattr(
        "phatch.lib.subprocess_runner.time.monotonic", lambda: next(monotonic)
    )

    with pytest.raises(ProcessTimeoutError):
        StdlibProcessRunner(RunnerOptions(poll_interval_seconds=0.01)).run(
            Command(("tool",), timeout_seconds=0.1)
        )

    assert process.terminated
    assert process.killed
    assert process.communicate_calls == 3


@pytest.mark.parametrize("value", [0, -1, float("inf")])
def test_runner_options_reject_invalid_intervals(value: float) -> None:
    with pytest.raises(RunnerOptionsError, match="finite and positive"):
        RunnerOptions(poll_interval_seconds=value)
