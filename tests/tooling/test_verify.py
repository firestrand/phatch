import subprocess
import sys
from pathlib import Path

import pytest

from scripts import verify

PROJECT_ROOT = Path(__file__).parents[2]
VERIFY_PATH = PROJECT_ROOT / "scripts" / "verify.py"


def test_commands_run_in_declared_order() -> None:
    # Given: three successful verification commands
    observed = []

    def executor(command, timeout_seconds):
        observed.append((tuple(command), timeout_seconds))
        return 0

    commands = (("first",), ("second", "arg"), ("third",))

    # When: the command sequence is run
    result = verify.run_commands(commands, executor=executor, timeout_seconds=9.0)

    # Then: every command runs once and in order
    assert result == 0
    assert observed == [
        (("first",), 9.0),
        (("second", "arg"), 9.0),
        (("third",), 9.0),
    ]


def test_nonzero_result_propagates_and_stops_execution() -> None:
    # Given: a command sequence whose second command fails
    observed = []

    def executor(command, timeout_seconds):
        del timeout_seconds
        observed.append(tuple(command))
        return 23 if command[0] == "fail" else 0

    # When: verification runs
    result = verify.run_commands(
        (("pass",), ("fail",), ("must-not-run",)),
        executor=executor,
        timeout_seconds=1.0,
    )

    # Then: the failing code is returned without running later commands
    assert result == 23
    assert observed == [("pass",), ("fail",)]


def test_missing_executable_returns_command_not_found() -> None:
    # Given: a command whose executable cannot exist
    # When: it is executed through the real process boundary
    result = verify.execute_command(("phatch-task2-missing-executable",), 1.0)

    # Then: verification reports the conventional command-not-found code
    assert result == 127


def test_timeout_returns_bounded_failure() -> None:
    # Given: a command that runs longer than its small deterministic budget
    command = (sys.executable, "-c", "import time; time.sleep(10)")

    # When: the timeout expires
    result = verify.execute_command(command, 0.01)

    # Then: verification reports timeout without waiting for the command
    assert result == 124


def test_successful_real_command_returns_zero() -> None:
    # Given: a cross-platform command that exits successfully
    command = (sys.executable, "-c", "raise SystemExit(0)")

    # When: it is executed through the real process boundary
    result = verify.execute_command(command, 1.0)

    # Then: its return code decides success
    assert result == 0


@pytest.mark.parametrize(
    ("profile", "expected_labels"),
    [
        ("focused", ["format", "lint", "type", "tests"]),
        ("unit", ["tests"]),
        (
            "gate",
            [
                "lock",
                "format",
                "lint",
                "type",
                "tests",
                "coverage",
                "build",
                "metadata",
            ],
        ),
    ],
)
def test_profiles_declare_expected_order(profile, expected_labels, tmp_path) -> None:
    # Given: an isolated artifact directory and a supported profile
    # When: its verification plan is created
    steps = verify.verification_steps(profile, tmp_path)

    # Then: the profile has the documented ordered checks
    assert [step.name for step in steps] == expected_labels


def test_metadata_check_expands_real_distribution_paths(tmp_path) -> None:
    # Given: built distributions plus unrelated coverage output
    wheel = tmp_path / "Phatch.whl"
    source = tmp_path / "Phatch.tar.gz"
    wheel.write_bytes(b"wheel")
    source.write_bytes(b"source")
    (tmp_path / "coverage.xml").write_text("coverage", encoding="utf-8")
    observed = []

    def executor(command, timeout_seconds):
        observed.append((tuple(command), timeout_seconds))
        return 0

    # When: metadata verification resolves the artifact directory
    result = verify.check_distributions(tmp_path, executor=executor, timeout_seconds=5)

    # Then: Twine receives only concrete, existing distribution paths
    assert result == 0
    assert observed == [
        (
            (
                sys.executable,
                "-m",
                "twine",
                "check",
                str(wheel),
                str(source),
            ),
            5,
        )
    ]


@pytest.mark.parametrize("artifacts", [(), ("Phatch.whl",)])
def test_metadata_check_rejects_incomplete_distribution_pairs(
    tmp_path: Path, artifacts: tuple[str, ...], capsys
) -> None:
    # Given: a distribution directory missing one or both required artifacts
    for name in artifacts:
        (tmp_path / name).write_bytes(b"artifact")

    # When: metadata verification resolves the incomplete artifact directory
    result = verify.check_distributions(
        tmp_path,
        executor=lambda command, timeout: pytest.fail(
            f"unexpected execution: {command!r}, {timeout}"
        ),
    )

    # Then: it fails before invoking Twine with an actionable diagnostic
    assert result == 1
    assert "exactly one wheel and one source distribution" in capsys.readouterr().err


def test_gate_checks_the_lock_before_all_other_steps(tmp_path) -> None:
    # Given: the complete repository gate
    steps = verify.verification_steps("gate", tmp_path)

    # When: its first step is inspected
    # Then: stale lock data fails before tools or tests can run
    assert steps[0] == verify.VerificationStep("lock", ("uv", "lock", "--check"))


def test_unsupported_internal_profile_is_exhaustive(tmp_path) -> None:
    # Given: a profile value outside the parsed CLI choices
    planner = vars(verify)["verification_steps"]

    # When: internal planning receives the impossible variant
    # Then: exhaustive matching rejects it
    with pytest.raises(AssertionError):
        planner("invalid", tmp_path)


def test_main_lists_commands_without_running_them(capsys) -> None:
    # Given: the focused verification profile
    # When: main runs in list mode
    result = verify.main(["--profile", "focused", "--list"])

    # Then: listing succeeds and starts with the formatter
    assert result == 0
    assert capsys.readouterr().out.splitlines()[0].startswith("format:")


def test_main_runs_selected_commands_with_timeout(monkeypatch) -> None:
    # Given: a unit profile and an observable command runner
    observed = []

    def run_commands(commands, executor=verify.execute_command, timeout_seconds=600.0):
        del executor
        observed.append((commands, timeout_seconds))
        return 29

    monkeypatch.setattr(verify, "run_commands", run_commands)

    # When: main executes the profile
    result = verify.main(["--profile", "unit", "--timeout", "7"])

    # Then: it propagates the runner result and timeout
    assert result == 29
    assert observed[0][1] == 7.0


def test_main_delegates_distribution_check_with_timeout(
    monkeypatch, tmp_path: Path
) -> None:
    # Given: a selected distribution directory and observable metadata checker
    observed = []

    def check_distributions(
        artifact_dir, executor=verify.execute_command, timeout_seconds=600.0
    ):
        del executor
        observed.append((artifact_dir, timeout_seconds))
        return 31

    monkeypatch.setattr(verify, "check_distributions", check_distributions)

    # When: the metadata-only command boundary runs
    result = verify.main(["--check-distributions", str(tmp_path), "--timeout", "8"])

    # Then: it forwards the concrete directory and selected timeout
    assert result == 31
    assert observed == [(tmp_path, 8.0)]


def test_list_mode_reports_gate_commands_without_executing_them() -> None:
    # Given: the real verification CLI
    # When: gate commands are listed
    result = subprocess.run(
        [sys.executable, str(VERIFY_PATH), "--profile", "gate", "--list"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    # Then: the complete gate is printed in configured order
    assert result.returncode == 0
    labels = [line.split(":", 1)[0] for line in result.stdout.splitlines()]
    assert labels == [
        "lock",
        "format",
        "lint",
        "type",
        "tests",
        "coverage",
        "build",
        "metadata",
    ]


def test_invalid_profile_fails_clearly() -> None:
    # Given: an unsupported verification profile
    # When: the real CLI parses it
    result = subprocess.run(
        [sys.executable, str(VERIFY_PATH), "--profile", "invalid"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )

    # Then: argparse rejects it without executing commands
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
