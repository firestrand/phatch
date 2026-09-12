from __future__ import annotations

import re
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parents[2]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")


def _workflow() -> dict:
    with WORKFLOW.open(encoding="utf-8") as workflow_file:
        return yaml.safe_load(workflow_file)


def test_workflow_declares_least_privilege_and_all_release_gate_jobs() -> None:
    # Given: the repository's only release-gate workflow
    # When: its machine-readable job contract is inspected
    workflow = _workflow()

    # Then: every required category and downloaded-artifact boundary is explicit
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["jobs"]) == {
        "quality",
        "non_gui",
        "coverage_gate",
        "distributions",
        "windows_gui",
        "windows_paths",
        "optional_capabilities",
        "portable_build",
        "downloaded_artifact_smoke",
    }


def test_workflow_covers_supported_os_and_python_matrices() -> None:
    # Given: supported source and wheel matrices
    jobs = _workflow()["jobs"]

    # When: runner and interpreter axes are read
    non_gui = jobs["non_gui"]["strategy"]["matrix"]
    distributions = jobs["distributions"]["strategy"]["matrix"]

    # Then: source and distribution checks both cover 3 OS by 3 Pythons
    assert set(non_gui["os"]) == {
        "ubuntu-latest",
        "macos-latest",
        "windows-latest",
    }
    assert set(non_gui["python-version"]) == {"3.11", "3.12", "3.13"}
    assert set(distributions["os"]) == set(non_gui["os"])
    assert set(distributions["python-version"]) == {"3.11", "3.12", "3.13"}
    assert jobs["quality"]["runs-on"] == "ubuntu-latest"
    assert jobs["portable_build"]["runs-on"] == "windows-latest"
    distribution_commands = yaml.safe_dump(jobs["distributions"])
    assert "--wheel" in distribution_commands
    assert "matrix.python-version" in distribution_commands
    assert "distributions-${{ matrix.os }}-${{ matrix.python-version }}" in (
        distribution_commands
    )


def test_workflow_enforces_collection_coverage_and_download_layout_contracts() -> None:
    # Given: source, native GUI, and downloaded artifact jobs
    jobs = _workflow()["jobs"]

    # When: their executable commands are inspected
    non_gui = yaml.safe_dump(jobs["non_gui"])
    windows_gui = yaml.safe_dump(jobs["windows_gui"])
    quality = yaml.safe_dump(jobs["quality"])
    coverage_gate = yaml.safe_dump(jobs["coverage_gate"])
    downloaded = yaml.safe_dump(jobs["downloaded_artifact_smoke"])

    # Then: collection, zero-skip, coverage policy, and ZIP root are explicit
    assert "--ignore=tests/integration/test_windows_gui_runtime.py" in non_gui
    assert "--strict-markers" in windows_gui
    assert "--cov" not in quality
    assert "verify.py --check-coverage" not in quality
    assert jobs["coverage_gate"]["needs"] == ["non_gui", "windows_gui"]
    assert "coverage_artifacts.py" in coverage_gate
    assert "coverage combine --keep" in coverage_gate
    assert "verify.py --check-coverage" in coverage_gate
    assert any(
        "downloaded/extracted Ω/Phatch" in step.get("run", "")
        for step in jobs["downloaded_artifact_smoke"]["steps"]
    )
    assert "artifact_scan.py downloaded" in downloaded


def test_coverage_producers_upload_exact_hidden_raw_and_junit_pairs() -> None:
    # Given: the required non-GUI matrix and native Windows GUI contributor
    jobs = _workflow()["jobs"]
    non_gui = yaml.safe_dump(jobs["non_gui"])
    windows_gui = yaml.safe_dump(jobs["windows_gui"])

    # When/Then: ten raw branch-data contributors are retained without local judgment
    assert "coverage run -m pytest --no-cov" in non_gui
    assert "COVERAGE_FILE" in non_gui
    assert "--ignore=tests/unit/pywx" in non_gui
    assert "--ignore=tests/integration/test_gui_smoke.py" in non_gui
    assert "if-no-files-found: error" in non_gui
    assert "include-hidden-files: true" in non_gui
    non_gui_steps = jobs["non_gui"]["steps"]
    coverage_step = next(
        step for step in non_gui_steps if "COVERAGE_FILE" in step.get("env", {})
    )
    upload_step = next(
        step for step in non_gui_steps if "upload-artifact@" in step.get("uses", "")
    )
    contributor = "non-gui-${{ matrix.os }}-${{ matrix.python-version }}"
    assert (
        coverage_step["env"]["COVERAGE_FILE"]
        == f"artifacts/coverage/.coverage.{contributor}"
    )
    assert upload_step["with"]["path"].splitlines() == [
        f"artifacts/coverage/.coverage.{contributor}",
        f"artifacts/junit/junit-{contributor}.xml",
    ]
    assert "coverage run -m pytest --no-cov" in windows_gui
    assert "tests/unit/pywx" in windows_gui
    assert "tests/integration/test_gui_smoke.py" in windows_gui
    assert "tests/integration/test_windows_gui_runtime.py" in windows_gui
    assert "if-no-files-found: error" in windows_gui
    assert "include-hidden-files: true" in windows_gui
    assert "artifacts/coverage/.coverage.windows-gui-3.12" in windows_gui
    assert "artifacts/junit/junit-windows-gui-3.12.xml" in windows_gui
    for forbidden in ("--cov-fail-under=0", "continue-on-error"):
        assert forbidden not in non_gui
        assert forbidden not in windows_gui


def test_core_distribution_matrix_does_not_install_or_inventory_gui_extras() -> None:
    # Given: the portable and ordinary wheel build routes
    jobs = _workflow()["jobs"]
    distributions = yaml.safe_dump(jobs["distributions"])
    portable = yaml.safe_dump(jobs["portable_build"])

    # When/Then: core wheels are platform-neutral while portable Windows stays complete
    assert "--extra gui" not in distributions
    assert "--extra windows" not in distributions
    assert "--extra gui" in portable
    assert "--extra windows" in portable


def test_every_external_action_is_pinned_to_a_full_commit_sha() -> None:
    # Given: all workflow steps that execute third-party actions
    workflow = _workflow()
    uses = [
        step["uses"]
        for job in workflow["jobs"].values()
        for step in job["steps"]
        if "uses" in step
    ]

    # When: action references are split from their repositories
    pins = [reference.rpartition("@")[2] for reference in uses]

    # Then: no mutable tag or branch can alter CI execution
    assert uses
    assert all(FULL_SHA.fullmatch(pin) for pin in pins)


def test_downloaded_artifact_smoke_uses_a_separate_download_directory() -> None:
    # Given: portable build and consumer jobs
    jobs = _workflow()["jobs"]
    consumer = jobs["downloaded_artifact_smoke"]

    # When: the consumer's dependencies and commands are inspected
    serialized = yaml.safe_dump(consumer)

    # Then: smoke testing happens only after a workflow artifact download
    assert consumer["needs"] == "portable_build"
    assert "actions/download-artifact@" in serialized
    assert "downloaded" in serialized
    assert "portable_smoke.py" in serialized


def test_portable_build_uses_reviewed_spec_and_release_harnesses() -> None:
    # Given: the native Windows portable build job
    job = _workflow()["jobs"]["portable_build"]
    serialized = yaml.safe_dump(job)

    # When: its commands and uploaded files are inspected
    # Then: real frozen executables, manifests, scans, and reports are required
    for contract in (
        "packaging/phatch.spec",
        "release_manifest.py",
        "artifact_scan.py",
        "portable_smoke.py",
        "SHA256SUMS",
        "sbom.spdx.json",
        "licenses.tsv",
        "pyspdxtools",
        "junit",
        "coverage",
    ):
        assert contract in serialized
    assert "continue-on-error" not in serialized


def test_native_commands_with_artifact_wildcards_use_bash_expansion() -> None:
    # Given: every workflow command that passes artifact globs to a native process
    jobs = _workflow()["jobs"]
    wildcard_steps = [
        step
        for job in jobs.values()
        for step in job["steps"]
        if "run" in step and "*" in step["run"]
    ]

    # When/Then: GitHub's Windows PowerShell default cannot receive literal globs
    assert wildcard_steps
    assert all(step.get("shell") == "bash" for step in wildcard_steps)


def test_pyinstaller_spec_wires_merge_dependencies_and_all_dynamic_packages() -> None:
    # Given: the reviewed multiprogram spec and project hook
    spec = (PROJECT_ROOT / "packaging" / "phatch.spec").read_text(encoding="utf-8")
    hook = (PROJECT_ROOT / "packaging" / "hooks" / "hook-phatch.py").read_text(
        encoding="utf-8"
    )

    # When/Then: both executables receive MERGE dependencies
    # and GUI modules are collected
    assert "console_analysis.dependencies" in spec
    assert "gui_analysis.dependencies" in spec
    assert 'collect_submodules("phatch.pyWx")' in hook


def test_action_pins_have_verified_official_sources() -> None:
    # Given: a reviewable action-pin inventory
    inventory = PROJECT_ROOT / ".github" / "action-pins.txt"

    # When: each non-comment record is parsed
    records = [
        line.split()
        for line in inventory.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]

    # Then: every full SHA is paired with an official GitHub API tag source
    assert records
    assert all(len(record) == 3 for record in records)
    assert all(FULL_SHA.fullmatch(record[1]) for record in records)
    assert all(
        record[2].startswith("https://api.github.com/repos/") for record in records
    )
