from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import coverage_policy


def _write_policy(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """[tool.phatch.coverage-ratchet]
line = 40.0
branch = 20.0
changed = 90.0
changed-modules = ["phatch/legacy.py"]
""",
        encoding="utf-8",
    )


def _write_report(path: Path, files: dict[str, tuple[int, int]]) -> None:
    path.write_text(
        json.dumps(
            {
                "files": {
                    name: {
                        "summary": {
                            "covered_lines": covered,
                            "num_statements": total,
                            "percent_statements_covered": 100 * covered / total,
                            "covered_branches": covered,
                            "num_branches": total,
                            "percent_branches_covered": 100 * covered / total,
                        }
                    }
                    for name, (covered, total) in files.items()
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


def test_ci_derived_unknown_module_with_zero_coverage_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a CI-derived module absent from the legacy configured ratchet
    _write_policy(tmp_path)
    report = tmp_path / "coverage.json"
    _write_report(report, {"phatch/new.py": (0, 10)})
    monkeypatch.setattr(coverage_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        coverage_policy,
        "derive_changed_python_modules",
        lambda base_ref: ("phatch/new.py",),
    )

    # When/Then: direct Git-derived changed coverage is mandatory
    assert coverage_policy.check_coverage(report, "base-sha") == 1


def test_ci_docs_only_change_does_not_require_static_module_equality(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a CI comparison containing no changed production Python module
    _write_policy(tmp_path)
    report = tmp_path / "coverage.json"
    _write_report(report, {})
    monkeypatch.setattr(coverage_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        coverage_policy, "derive_changed_python_modules", lambda base_ref: ()
    )

    # When/Then: aggregate ratchets pass without static-list drift failures
    assert coverage_policy.check_coverage(report, "base-sha") == 0


def test_local_gate_enforces_git_derived_unlisted_changed_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: local Git reports a new module absent from the static legacy list
    _write_policy(tmp_path)
    report = tmp_path / "coverage.json"
    _write_report(
        report,
        {"phatch/legacy.py": (10, 10), "phatch/new.py": (0, 10)},
    )
    monkeypatch.setattr(coverage_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        coverage_policy,
        "derive_changed_python_modules",
        lambda base_ref: ("phatch/new.py",),
    )

    # When/Then: no-base verification enforces the actual changed module
    assert coverage_policy.check_coverage(report) == 1


def test_all_zero_push_base_conservatively_uses_every_tracked_module() -> None:
    # Given: an all-zero base whose branch has Python changes across many commits
    observed: list[tuple[str, ...]] = []
    outputs = iter((b"phatch/early.py\0scripts/late.py\0README.md\0", b"", b""))

    def runner(command: tuple[str, ...]) -> bytes:
        observed.append(command)
        return next(outputs)

    # When: changed modules are derived from that push boundary
    modules = coverage_policy.derive_changed_python_modules("0" * 40, runner=runner)

    # Then: no earlier commit can escape the changed-module coverage boundary
    assert modules == ("phatch/early.py", "scripts/late.py")
    assert observed[0] == ("git", "ls-files", "-z")


def test_run_git_uses_project_root_and_required_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a Git process whose invocation can be observed
    observed: dict[str, object] = {}

    def run(command: tuple[str, ...], **kwargs: object) -> SimpleNamespace:
        observed.update(command=command, **kwargs)
        return SimpleNamespace(stdout=b"tracked.py\0")

    monkeypatch.setattr(subprocess, "run", run)

    # When: the production Git runner executes a command
    output = coverage_policy.derive_changed_python_modules(None)

    # Then: it is anchored to the repository with the required Git guard
    assert output == ()
    assert observed["cwd"] == coverage_policy.PROJECT_ROOT
    assert observed["check"] is True
    assert observed["capture_output"] is True
    environment = observed["env"]
    assert isinstance(environment, dict)
    assert environment["GIT_MASTER"] == "1"


def test_missing_git_executable_is_reported() -> None:
    # Given: a runner that cannot locate Git
    def runner(command: tuple[str, ...]) -> bytes:
        del command
        raise FileNotFoundError("git not found")

    # When/Then: callers receive the stable boundary error
    with pytest.raises(coverage_policy.GitBoundaryError, match="git not found"):
        coverage_policy.derive_changed_python_modules(None, runner=runner)
