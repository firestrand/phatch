from __future__ import annotations

import os
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final

Command = tuple[str, ...]
GitRunner = Callable[[Command], bytes]

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]


class GitBoundaryError(RuntimeError):
    pass


def changed_python_modules(paths: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        sorted(
            path
            for path in paths
            if path.endswith(".py")
            and (path.startswith("phatch/") or path.startswith("scripts/"))
        )
    )


def run_git(command: Command) -> bytes:
    completed = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        env={**os.environ, "GIT_MASTER": "1"},
    )
    return completed.stdout


def derive_changed_python_modules(
    base_ref: str | None,
    runner: GitRunner = run_git,
) -> tuple[str, ...]:
    commands: list[Command] = []
    if base_ref is not None:
        if base_ref and set(base_ref) == {"0"}:
            commands.append(("git", "ls-files", "-z"))
        else:
            commands.append(
                (
                    "git",
                    "diff",
                    "--name-only",
                    "-z",
                    "--find-renames",
                    "--diff-filter=ACMR",
                    f"{base_ref}...HEAD",
                )
            )
    commands.extend(
        (
            (
                "git",
                "diff",
                "--name-only",
                "-z",
                "--find-renames",
                "--diff-filter=ACMR",
                "HEAD",
            ),
            ("git", "ls-files", "--others", "--exclude-standard", "-z"),
        )
    )
    paths: set[str] = set()
    try:
        for command in commands:
            paths.update(
                path for path in runner(command).decode("utf-8").split("\0") if path
            )
    except subprocess.CalledProcessError as error:
        stderr = (
            error.stderr.decode("utf-8", errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr or ""
        )
        raise GitBoundaryError(stderr.strip() or str(error)) from error
    except FileNotFoundError as error:
        raise GitBoundaryError(str(error)) from error
    return changed_python_modules(tuple(paths))
