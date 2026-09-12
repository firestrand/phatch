from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from phatch.lib.process import (
    Command,
    CommandValidationError,
    ProcessCancelledError,
    ProcessExitError,
    ProcessLaunchError,
    ProcessResult,
    ProcessTimeoutError,
)


def construct_command(**values):
    return type.__call__(Command, **values)


def test_command_is_immutable_and_normalizes_owned_values() -> None:
    command = Command(
        argv=("tool", ""),
        cwd=Path("work"),
        env=(("MODE", "safe"),),
        accepted_returncodes=frozenset({0, 3}),
    )

    assert command.argv == ("tool", "")
    assert command.accepted_returncodes == frozenset({0, 3})
    with pytest.raises(FrozenInstanceError):
        command.__setattr__("cwd", None)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Command(argv=()),
        lambda: Command(argv=("",)),
        lambda: Command(argv=("tool\0name",)),
        lambda: Command(argv=("tool", "bad\0arg")),
        lambda: Command(argv=("tool",), env=(("A=B", "value"),)),
        lambda: Command(argv=("tool",), env=(("A", "1"), ("A", "2"))),
        lambda: construct_command(argv=("tool",), env=[]),
        lambda: construct_command(argv=("tool",), env=(("A",),)),
        lambda: construct_command(argv=("tool",), env=((1, "value"),)),
        lambda: Command(argv=("tool",), timeout_seconds=0),
        lambda: Command(argv=("tool",), timeout_seconds=float("inf")),
        lambda: Command(argv=("tool",), accepted_returncodes=frozenset()),
    ],
)
def test_command_rejects_invalid_boundary_values(
    factory: Callable[[], Command],
) -> None:
    with pytest.raises(CommandValidationError):
        factory()


def test_command_rejects_a_command_string() -> None:
    invalid_argv = "tool"
    with pytest.raises(CommandValidationError):
        construct_command(argv=invalid_argv)


def test_validation_error_has_an_actionable_message() -> None:
    assert str(CommandValidationError("invalid command")) == "invalid command"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: construct_command(argv=("tool", 1)),
        lambda: Command(argv=("tool",), accepted_returncodes=frozenset({True})),
        lambda: Command(argv=("tool",), encoding=""),
    ],
)
def test_command_rejects_non_string_and_ambiguous_values(factory) -> None:
    with pytest.raises(CommandValidationError):
        factory()


def test_process_result_and_failures_retain_typed_diagnostics() -> None:
    command = Command(argv=("tool",))
    result = ProcessResult(command=command, returncode=0, stdout="ok", stderr="")

    assert result.command is command
    assert str(ProcessLaunchError(command, "denied", 13)) == (
        "could not launch tool: denied"
    )
    assert str(ProcessExitError(command, 7, "partial", "bad")) == (
        "tool exited with status 7"
    )
    assert str(ProcessTimeoutError(command, 2.5)) == "tool timed out after 2.5 seconds"
    assert str(ProcessCancelledError(command)) == "tool was cancelled"
