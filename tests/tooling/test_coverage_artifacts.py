from __future__ import annotations

import runpy
import xml.etree.ElementTree as ET
from pathlib import Path

import coverage
import pytest

from scripts import coverage_artifacts

NON_GUI_CONTRIBUTORS = tuple(
    f"non-gui-{os_name}-{python_version}"
    for os_name in ("ubuntu-latest", "macos-latest", "windows-latest")
    for python_version in ("3.11", "3.12", "3.13")
)
CONTRIBUTORS = (*NON_GUI_CONTRIBUTORS, "windows-gui-3.12")


def _write_contributor(
    root: Path,
    module: Path,
    contributor: str,
    *,
    choose_left: bool,
    skipped: int = 0,
) -> None:
    artifact = root / contributor
    coverage_dir = artifact / "coverage"
    junit_dir = artifact / "junit"
    coverage_dir.mkdir(parents=True)
    junit_dir.mkdir()
    raw_path = coverage_dir / f".coverage.{contributor}"
    measurement = coverage.Coverage(
        branch=True,
        data_file=str(raw_path),
        config_file=False,
    )
    measurement.start()
    runpy.run_path(str(module), init_globals={"CHOOSE_LEFT": choose_left})
    measurement.stop()
    measurement.save()
    suite = ET.Element("testsuite", tests="1", skipped=str(skipped))
    ET.ElementTree(suite).write(
        junit_dir / f"junit-{contributor}.xml",
        encoding="utf-8",
        xml_declaration=True,
    )


@pytest.fixture
def coverage_artifact_tree(tmp_path: Path) -> tuple[Path, Path]:
    module = tmp_path / "branch_fixture.py"
    module.write_text(
        "if CHOOSE_LEFT:\n    result = 'left'\nelse:\n    result = 'right'\n",
        encoding="utf-8",
    )
    artifacts = tmp_path / "downloaded"
    for index, contributor in enumerate(CONTRIBUTORS):
        _write_contributor(
            artifacts,
            module,
            contributor,
            choose_left=index != 1,
        )
    return artifacts, module


def _arcs(data_file: Path, module: Path) -> set[tuple[int, int]]:
    result = coverage.Coverage(data_file=str(data_file), config_file=False)
    result.load()
    return set(result.get_data().arcs(str(module.resolve())) or ())


def test_validator_stages_real_disjoint_coverage_for_union(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: ten required real coverage databases including disjoint branch arcs
    artifacts, module = coverage_artifact_tree
    staged = tmp_path / "combine"

    # When: contributors are validated, staged, and combined by coverage.py
    coverage_artifacts.validate_and_stage(artifacts, staged)
    first = staged / f".coverage.{CONTRIBUTORS[0]}"
    second = staged / f".coverage.{CONTRIBUTORS[1]}"
    combined_path = tmp_path / ".coverage"
    combined = coverage.Coverage(data_file=str(combined_path), config_file=False)
    combined.combine(data_paths=[str(staged)], strict=True, keep=True)
    combined.save()

    # Then: the union retains arcs that no individual contributor contains
    expected = _arcs(first, module) | _arcs(second, module)
    assert _arcs(combined_path, module).issuperset(expected)
    assert _arcs(first, module) != _arcs(second, module)


@pytest.mark.parametrize("kind", ["coverage", "junit"])
def test_validator_rejects_a_missing_required_pair(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path, kind: str
) -> None:
    # Given: one required contributor file is absent
    artifacts, _module = coverage_artifact_tree
    pattern = (
        f".coverage.{CONTRIBUTORS[0]}"
        if kind == "coverage"
        else f"junit-{CONTRIBUTORS[0]}.xml"
    )
    next(artifacts.rglob(pattern)).unlink()

    # When/Then: the union boundary rejects the incomplete artifact set
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match="missing"):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


def test_validator_rejects_duplicate_contributor_artifacts(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a second raw file claims the same contributor identity
    artifacts, _module = coverage_artifact_tree
    original = next(artifacts.rglob(f".coverage.{CONTRIBUTORS[0]}"))
    duplicate = artifacts / "duplicate" / "coverage" / original.name
    duplicate.parent.mkdir(parents=True)
    duplicate.write_bytes(original.read_bytes())

    # When/Then: duplicate evidence cannot enter the final union
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match="duplicate"):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


def test_validator_rejects_corrupt_coverage_data(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a required raw coverage database is unreadable
    artifacts, _module = coverage_artifact_tree
    next(artifacts.rglob(f".coverage.{CONTRIBUTORS[0]}")).write_bytes(b"corrupt")

    # When/Then: corrupt evidence fails before coverage combine
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match="unreadable"):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


def test_validator_rejects_coverage_without_branch_data(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a readable contributor database collected without branch coverage
    artifacts, module = coverage_artifact_tree
    raw = next(artifacts.rglob(f".coverage.{CONTRIBUTORS[0]}"))
    raw.unlink()
    measurement = coverage.Coverage(
        branch=False,
        data_file=str(raw),
        config_file=False,
    )
    measurement.start()
    runpy.run_path(str(module), init_globals={"CHOOSE_LEFT": True})
    measurement.stop()
    measurement.save()

    # When/Then: statement-only data cannot enter the branch coverage union
    with pytest.raises(
        coverage_artifacts.CoverageArtifactError, match="lacks branches"
    ):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


def test_validator_rejects_corrupt_junit_report(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a required JUnit file is malformed XML
    artifacts, _module = coverage_artifact_tree
    next(artifacts.rglob(f"junit-{CONTRIBUTORS[0]}.xml")).write_text(
        "<testsuite>", encoding="utf-8"
    )

    # When/Then: unreadable execution evidence fails the boundary
    with pytest.raises(
        coverage_artifacts.CoverageArtifactError, match="unreadable JUnit"
    ):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


@pytest.mark.parametrize(("tests", "skipped"), [(0, 0), (1, 1)])
def test_validator_requires_executed_unskipped_windows_gui_tests(
    coverage_artifact_tree: tuple[Path, Path],
    tmp_path: Path,
    tests: int,
    skipped: int,
) -> None:
    # Given: Windows GUI JUnit evidence that did not execute cleanly
    artifacts, _module = coverage_artifact_tree
    junit = next(artifacts.rglob("junit-windows-gui-3.12.xml"))
    ET.ElementTree(
        ET.Element("testsuite", tests=str(tests), skipped=str(skipped))
    ).write(
        junit,
        encoding="utf-8",
        xml_declaration=True,
    )

    # When/Then: native GUI coverage cannot be represented by skips or zero tests
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match="Windows GUI"):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


@pytest.mark.parametrize("contributor", [CONTRIBUTORS[0], "windows-gui-3.12"])
@pytest.mark.parametrize("outcome", ["failures", "errors"])
def test_validator_rejects_unsuccessful_junit_for_every_contributor(
    coverage_artifact_tree: tuple[Path, Path],
    tmp_path: Path,
    contributor: str,
    outcome: str,
) -> None:
    # Given: a required contributor reports a failed or errored test
    artifacts, _module = coverage_artifact_tree
    junit = next(artifacts.rglob(f"junit-{contributor}.xml"))
    root = ET.parse(junit).getroot()
    root.set(outcome, "1")
    ET.ElementTree(root).write(junit, encoding="utf-8", xml_declaration=True)

    # When/Then: unsuccessful execution evidence cannot enter the union
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match=outcome):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


@pytest.mark.parametrize("field", ["tests", "skipped", "failures", "errors"])
@pytest.mark.parametrize("value", ["invalid", "-1"])
def test_validator_rejects_malformed_or_negative_junit_counts(
    coverage_artifact_tree: tuple[Path, Path],
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    # Given: a JUnit count is not a nonnegative integer
    artifacts, _module = coverage_artifact_tree
    junit = next(artifacts.rglob(f"junit-{CONTRIBUTORS[0]}.xml"))
    root = ET.parse(junit).getroot()
    root.set(field, value)
    ET.ElementTree(root).write(junit, encoding="utf-8", xml_declaration=True)

    # When/Then: malformed numeric data becomes the typed artifact error
    with pytest.raises(coverage_artifacts.CoverageArtifactError, match=field):
        coverage_artifacts.validate_and_stage(artifacts, tmp_path / "combine")


def test_cli_stages_a_complete_artifact_set(
    coverage_artifact_tree: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a complete set of contributor artifacts
    artifacts, _module = coverage_artifact_tree
    output = tmp_path / "combine"

    # When: the validator is used through its CLI boundary
    return_code = coverage_artifacts.main((str(artifacts), str(output)))

    # Then: all ten raw inputs are ready for coverage combine
    assert return_code == 0
    assert len(tuple(output.glob(".coverage.*"))) == 10


def test_cli_reports_invalid_artifacts(
    coverage_artifact_tree: tuple[Path, Path],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given: an incomplete set passed to the CLI boundary
    artifacts, _module = coverage_artifact_tree
    next(artifacts.rglob(f".coverage.{CONTRIBUTORS[0]}")).unlink()

    # When: validation runs through the CLI
    return_code = coverage_artifacts.main((str(artifacts), str(tmp_path / "combine")))

    # Then: CI receives a nonzero status and an actionable boundary error
    assert return_code == 1
    assert "missing" in capsys.readouterr().err
