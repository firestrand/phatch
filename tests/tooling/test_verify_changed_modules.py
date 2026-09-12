import json
import subprocess
from pathlib import Path

import pytest

from scripts import coverage_policy, verify


def test_changed_modules_include_base_local_and_untracked_paths() -> None:
    outputs = iter(
        (
            b"phatch/base.py\0scripts/renamed tool.py\0",
            b"phatch/local.py\0scripts/staged.py\0",
            b"scripts/untracked.py\0tests/ignored.py\0",
        )
    )
    observed: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...]) -> bytes:
        observed.append(command)
        return next(outputs)

    modules = coverage_policy.derive_changed_python_modules(
        "origin/main", runner=runner
    )

    assert modules == (
        "phatch/base.py",
        "phatch/local.py",
        "scripts/renamed tool.py",
        "scripts/staged.py",
        "scripts/untracked.py",
    )
    assert observed == [
        (
            "git",
            "diff",
            "--name-only",
            "-z",
            "--find-renames",
            "--diff-filter=ACMR",
            "origin/main...HEAD",
        ),
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
    ]


def test_local_changed_modules_include_worktree_and_untracked_paths() -> None:
    outputs = iter((b"scripts/staged.py\0phatch/unstaged.py\0", b"scripts/new.py\0"))

    def runner(command: tuple[str, ...]) -> bytes:
        del command
        return next(outputs)

    modules = coverage_policy.derive_changed_python_modules(None, runner=runner)

    assert modules == (
        "phatch/unstaged.py",
        "scripts/new.py",
        "scripts/staged.py",
    )


def test_git_boundary_failure_is_reported() -> None:
    def runner(command: tuple[str, ...]) -> bytes:
        del command
        raise subprocess.CalledProcessError(128, ("git", "diff"), stderr=b"bad ref")

    with pytest.raises(coverage_policy.GitBoundaryError, match="bad ref"):
        coverage_policy.derive_changed_python_modules("missing", runner=runner)


def test_configured_boundary_reports_missing_and_extra_modules() -> None:
    with pytest.raises(coverage_policy.CoverageBoundaryError) as error:
        coverage_policy.validate_changed_module_boundary(
            configured=("phatch/extra.py", "scripts/verify.py"),
            derived=("scripts/__init__.py", "scripts/verify.py"),
        )

    assert error.value.missing == ("scripts/__init__.py",)
    assert error.value.extra == ("phatch/extra.py",)


def test_coverage_check_rejects_undeclared_changed_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.phatch.coverage-ratchet]
line = 41.62
branch = 23.17
changed = 90.0
changed-modules = ["phatch/lib/metadata.py", "scripts/verify.py"]
""".strip(),
        encoding="utf-8",
    )
    report_path = tmp_path / "coverage.json"
    report_path.write_text(
        json.dumps(
            {
                "files": {
                    "phatch/lib/metadata.py": {
                        "summary": {
                            "covered_lines": 100,
                            "num_statements": 100,
                            "percent_statements_covered": 100.0,
                            "covered_branches": 100,
                            "num_branches": 100,
                            "percent_branches_covered": 100.0,
                        }
                    },
                    "scripts/__init__.py": {
                        "summary": {
                            "covered_lines": 0,
                            "num_statements": 1,
                            "percent_statements_covered": 0.0,
                            "covered_branches": 0,
                            "num_branches": 1,
                            "percent_branches_covered": 0.0,
                        }
                    },
                    "scripts/verify.py": {
                        "summary": {
                            "covered_lines": 100,
                            "num_statements": 100,
                            "percent_statements_covered": 100.0,
                            "covered_branches": 100,
                            "num_branches": 100,
                            "percent_branches_covered": 100.0,
                        }
                    },
                },
                "totals": {
                    "covered_lines": 100,
                    "num_statements": 100,
                    "covered_branches": 100,
                    "num_branches": 100,
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        coverage_policy,
        "derive_changed_python_modules",
        lambda base_ref: (
            "phatch/lib/metadata.py",
            "scripts/__init__.py",
            "scripts/verify.py",
        ),
    )
    monkeypatch.setattr(coverage_policy, "PROJECT_ROOT", tmp_path)

    assert coverage_policy.check_coverage(report_path, "base-sha") == 1


def test_ci_gate_requires_explicit_base_ref(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("CI", "true")

    result = verify.main(["--profile", "gate", "--list"])

    assert result == 2
    assert "--base-ref is required in CI" in capsys.readouterr().err
