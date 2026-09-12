from __future__ import annotations

import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import coverage
from coverage.exceptions import CoverageException

NON_GUI_CONTRIBUTORS: Final = tuple(
    f"non-gui-{os_name}-{python_version}"
    for os_name in ("ubuntu-latest", "macos-latest", "windows-latest")
    for python_version in ("3.11", "3.12", "3.13")
)
WINDOWS_GUI_CONTRIBUTOR: Final = "windows-gui-3.12"
REQUIRED_CONTRIBUTORS: Final = (*NON_GUI_CONTRIBUTORS, WINDOWS_GUI_CONTRIBUTOR)


@dataclass(frozen=True, slots=True)
class CoverageArtifactError(Exception):
    detail: str

    def __str__(self) -> str:
        return self.detail


@dataclass(frozen=True, slots=True)
class ArtifactPair:
    contributor: str
    raw_coverage: Path
    junit: Path


@dataclass(frozen=True, slots=True)
class JUnitCounts:
    tests: int
    skipped: int
    failures: int
    errors: int


def _unique_named_files(root: Path, pattern: str) -> dict[str, Path]:
    paths = tuple(root.rglob(pattern))
    counts = Counter(path.name for path in paths)
    duplicates = tuple(sorted(name for name, count in counts.items() if count > 1))
    if duplicates:
        raise CoverageArtifactError(f"duplicate artifact files: {duplicates!r}")
    return {path.name: path for path in paths}


def _artifact_pairs(root: Path) -> tuple[ArtifactPair, ...]:
    raw_files = _unique_named_files(root, ".coverage.*")
    junit_files = _unique_named_files(root, "junit-*.xml")
    expected_raw = {f".coverage.{name}" for name in REQUIRED_CONTRIBUTORS}
    expected_junit = {f"junit-{name}.xml" for name in REQUIRED_CONTRIBUTORS}
    missing = tuple(
        sorted(
            (expected_raw - raw_files.keys()) | (expected_junit - junit_files.keys())
        )
    )
    extra = tuple(
        sorted(
            (raw_files.keys() - expected_raw) | (junit_files.keys() - expected_junit)
        )
    )
    if missing or extra:
        raise CoverageArtifactError(
            f"coverage artifact boundary mismatch: missing={missing!r} extra={extra!r}"
        )
    return tuple(
        ArtifactPair(
            contributor=name,
            raw_coverage=raw_files[f".coverage.{name}"],
            junit=junit_files[f"junit-{name}.xml"],
        )
        for name in REQUIRED_CONTRIBUTORS
    )


def _validate_coverage(pair: ArtifactPair) -> None:
    measurement = coverage.Coverage(
        data_file=str(pair.raw_coverage),
        config_file=False,
    )
    try:
        measurement.load()
        data = measurement.get_data()
        if not data.has_arcs() or not data.measured_files():
            raise CoverageArtifactError(
                f"coverage data is empty or lacks branches: {pair.raw_coverage}"
            )
    except (CoverageException, OSError) as error:
        raise CoverageArtifactError(
            f"unreadable coverage data: {pair.raw_coverage}"
        ) from error


def _parse_junit_count(suite: ET.Element, field: str, path: Path) -> int:
    serialized = suite.get(field, "0")
    try:
        value = int(serialized)
    except ValueError as error:
        raise CoverageArtifactError(
            f"JUnit {field} must be a nonnegative integer: {path}"
        ) from error
    if value < 0:
        raise CoverageArtifactError(
            f"JUnit {field} must be a nonnegative integer: {path}"
        )
    return value


def _junit_counts(path: Path) -> JUnitCounts:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as error:
        raise CoverageArtifactError(f"unreadable JUnit report: {path}") from error
    suites = (root,) if root.tag == "testsuite" else tuple(root.findall("testsuite"))
    return JUnitCounts(
        tests=sum(_parse_junit_count(suite, "tests", path) for suite in suites),
        skipped=sum(_parse_junit_count(suite, "skipped", path) for suite in suites),
        failures=sum(_parse_junit_count(suite, "failures", path) for suite in suites),
        errors=sum(_parse_junit_count(suite, "errors", path) for suite in suites),
    )


def validate_and_stage(root: Path, output_dir: Path) -> tuple[Path, ...]:
    pairs = _artifact_pairs(root)
    for pair in pairs:
        _validate_coverage(pair)
        counts = _junit_counts(pair.junit)
        if counts.failures != 0 or counts.errors != 0:
            raise CoverageArtifactError(
                f"unsuccessful JUnit report for {pair.contributor}: "
                f"failures={counts.failures} errors={counts.errors}"
            )
        if pair.contributor == WINDOWS_GUI_CONTRIBUTOR and (
            counts.tests == 0 or counts.skipped != 0
        ):
            raise CoverageArtifactError(
                "Windows GUI contributor must execute tests with zero skips: "
                f"tests={counts.tests} skipped={counts.skipped}"
            )
    output_dir.mkdir(parents=True)
    staged = tuple(output_dir / pair.raw_coverage.name for pair in pairs)
    for pair, destination in zip(pairs, staged, strict=True):
        shutil.copy2(pair.raw_coverage, destination)
    return staged


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and stage required CI coverage contributors."
    )
    parser.add_argument("artifact_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(arguments)
    try:
        validate_and_stage(options.artifact_root, options.output_dir)
    except CoverageArtifactError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
