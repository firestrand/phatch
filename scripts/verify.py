from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, assert_never

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
if __package__ is None:
    sys.path.insert(0, str(PROJECT_ROOT))
    __package__ = "scripts"

from .coverage_policy import check_coverage

Command = tuple[str, ...]
CommandExecutor = Callable[[Sequence[str], float], int]
Profile = Literal["focused", "unit", "gate"]

DEFAULT_TIMEOUT_SECONDS: Final = 600.0


@dataclass(frozen=True, slots=True)
class VerificationStep:
    name: str
    command: Command


def execute_command(command: Sequence[str], timeout_seconds: float) -> int:
    print(f"$ {subprocess.list2cmdline(command)}", flush=True)
    try:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError:
        return 127
    except subprocess.TimeoutExpired:
        return 124
    return completed.returncode


def run_commands(
    commands: Sequence[Command],
    executor: CommandExecutor = execute_command,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    for command in commands:
        return_code = executor(command, timeout_seconds)
        if return_code != 0:
            return return_code
    return 0


def check_distributions(
    artifact_dir: Path,
    executor: CommandExecutor = execute_command,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> int:
    artifacts = (
        *sorted(artifact_dir.glob("*.whl")),
        *sorted(artifact_dir.glob("*.tar.gz")),
    )
    if (
        len(tuple(artifact_dir.glob("*.whl"))) != 1
        or len(tuple(artifact_dir.glob("*.tar.gz"))) != 1
    ):
        print("expected exactly one wheel and one source distribution", file=sys.stderr)
        return 1
    return executor(
        (sys.executable, "-m", "twine", "check", *(str(path) for path in artifacts)),
        timeout_seconds,
    )


def verification_steps(
    profile: Profile,
    artifact_dir: Path,
    base_ref: str | None = None,
) -> tuple[VerificationStep, ...]:
    python = sys.executable
    match profile:
        case "focused":
            return (
                VerificationStep(
                    "format",
                    (python, "-m", "ruff", "format", "--check", "."),
                ),
                VerificationStep("lint", (python, "-m", "ruff", "check", ".")),
                VerificationStep(
                    "type",
                    (python, "-m", "ty", "check", "--extra-search-path", "."),
                ),
                VerificationStep(
                    "tests",
                    (
                        python,
                        "-m",
                        "pytest",
                        "tests/tooling",
                        "--cov=scripts.coverage_artifacts",
                        "--cov=scripts.verify",
                        "--cov=scripts.coverage_policy",
                        "--cov-branch",
                        "--cov-report=term-missing",
                        "--cov-fail-under=90",
                    ),
                ),
            )
        case "unit":
            return (VerificationStep("tests", (python, "-m", "pytest", "tests/unit")),)
        case "gate":
            coverage_report = artifact_dir / "coverage.json"
            return (
                VerificationStep("lock", ("uv", "lock", "--check")),
                VerificationStep(
                    "format",
                    (python, "-m", "ruff", "format", "--check", "."),
                ),
                VerificationStep("lint", (python, "-m", "ruff", "check", ".")),
                VerificationStep(
                    "type",
                    (python, "-m", "ty", "check", "--extra-search-path", "."),
                ),
                VerificationStep(
                    "tests",
                    (
                        python,
                        "-m",
                        "pytest",
                        "--cov=phatch",
                        "--cov=scripts",
                        "--cov-branch",
                        f"--cov-report=json:{coverage_report}",
                        f"--cov-report=xml:{artifact_dir / 'coverage.xml'}",
                        "--cov-report=term-missing",
                        f"--junitxml={artifact_dir / 'junit.xml'}",
                    ),
                ),
                VerificationStep(
                    "coverage",
                    (
                        python,
                        str(Path(__file__).resolve()),
                        "--check-coverage",
                        str(coverage_report),
                        *(("--base-ref", base_ref) if base_ref is not None else ()),
                    ),
                ),
                VerificationStep(
                    "build",
                    (python, "-m", "build", "--outdir", str(artifact_dir)),
                ),
                VerificationStep(
                    "metadata",
                    (
                        python,
                        str(Path(__file__).resolve()),
                        "--check-distributions",
                        str(artifact_dir),
                    ),
                ),
            )
        case unreachable:
            assert_never(unreachable)


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Phatch verification checks.")
    parser.add_argument(
        "--profile",
        choices=("focused", "unit", "gate"),
        default="gate",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List checks without running them.",
    )
    parser.add_argument("--check-coverage", type=Path, metavar="REPORT")
    parser.add_argument("--check-distributions", type=Path, metavar="DIRECTORY")
    parser.add_argument("--base-ref")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(arguments)
    if (
        options.base_ref is None
        and os.environ.get("CI")
        and options.check_distributions is None
    ):
        print("--base-ref is required in CI", file=sys.stderr)
        return 2
    if options.check_coverage is not None:
        return check_coverage(options.check_coverage, options.base_ref)
    if options.check_distributions is not None:
        return check_distributions(
            options.check_distributions, timeout_seconds=options.timeout
        )
    with tempfile.TemporaryDirectory(prefix="phatch-verify-") as temporary_dir:
        steps = verification_steps(
            options.profile, Path(temporary_dir), options.base_ref
        )
        if options.list:
            for step in steps:
                print(f"{step.name}: {subprocess.list2cmdline(step.command)}")
            return 0
        return run_commands(
            tuple(step.command for step in steps),
            timeout_seconds=options.timeout,
        )


if __name__ == "__main__":
    raise SystemExit(main())
