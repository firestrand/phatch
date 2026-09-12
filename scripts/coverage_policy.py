from __future__ import annotations

import json
import math
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Final, NoReturn

from scripts.coverage_git import (
    GitBoundaryError,
    changed_python_modules,
    derive_changed_python_modules,
)

CoverageReport = Mapping[str, object]

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
SERIALIZED_PERCENT_TOLERANCE: Final = 5e-8


class CoverageThresholdError(ValueError):
    pass


class CoverageBoundaryError(ValueError):
    def __init__(self, missing: tuple[str, ...], extra: tuple[str, ...]) -> None:
        self.missing = missing
        self.extra = extra
        super().__init__(
            f"changed-module boundary mismatch: missing={missing!r} extra={extra!r}"
        )


class CoverageReportError(TypeError):
    pass


@dataclass(frozen=True, slots=True)
class MetricSpec:
    label: str
    covered_key: str
    total_key: str
    percent_key: str | None = None


@dataclass(frozen=True, slots=True)
class CoverageMetric:
    covered: int
    total: int
    percent: float

    def is_below(self, threshold: float) -> bool:
        threshold_ratio = Fraction(str(threshold))
        return (
            100 * self.covered * threshold_ratio.denominator
            < self.total * threshold_ratio.numerator
        )

    @classmethod
    def parse(
        cls,
        values: Mapping[str, object],
        spec: MetricSpec,
        *,
        allow_empty: bool,
    ) -> CoverageMetric:
        covered = _parse_count(values, spec.covered_key, spec.label)
        total = _parse_count(values, spec.total_key, spec.label)
        if covered > total:
            raise CoverageReportError(f"{spec.label} covered count exceeds total")
        if total == 0:
            if not allow_empty:
                raise CoverageReportError(f"{spec.label} total must be positive")
            expected_percent = 100.0
        else:
            expected_percent = 100.0 * covered / total
        percent = (
            expected_percent
            if spec.percent_key is None
            else _parse_percent(values, spec.percent_key, spec.label)
        )
        if not math.isclose(
            percent,
            expected_percent,
            rel_tol=0.0,
            abs_tol=SERIALIZED_PERCENT_TOLERANCE,
        ):
            raise CoverageReportError(f"{spec.label} percentage contradicts counts")
        return cls(covered=covered, total=total, percent=percent)


LINE_TOTAL: Final = MetricSpec("aggregate line", "covered_lines", "num_statements")
BRANCH_TOTAL: Final = MetricSpec("aggregate branch", "covered_branches", "num_branches")
LINE_MODULE: Final = MetricSpec(
    "module line",
    "covered_lines",
    "num_statements",
    "percent_statements_covered",
)
BRANCH_MODULE: Final = MetricSpec(
    "module branch",
    "covered_branches",
    "num_branches",
    "percent_branches_covered",
)


def _required(values: Mapping[str, object], key: str, context: str) -> object:
    try:
        return values[key]
    except KeyError as error:
        raise CoverageReportError(f"{context} is missing {key}") from error


def _parse_count(values: Mapping[str, object], key: str, context: str) -> int:
    value = _required(values, key, context)
    if type(value) is not int or value < 0:
        raise CoverageReportError(f"{context} {key} must be a non-negative integer")
    return value


def _parse_percent(values: Mapping[str, object], key: str, context: str) -> float:
    value = _required(values, key, context)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CoverageReportError(f"{context} {key} must be numeric")
    percent = float(value)
    if not math.isfinite(percent) or not 0.0 <= percent <= 100.0:
        raise CoverageReportError(f"{context} {key} must be finite and within 0..100")
    return percent


def _mapping(
    values: Mapping[str, object], key: str, context: str
) -> Mapping[str, object]:
    value = _required(values, key, context)
    if not isinstance(value, Mapping):
        raise CoverageReportError(f"{context} {key} must be a mapping")
    return value


def _reject_non_finite_constant(token: str) -> NoReturn:
    raise CoverageReportError(f"coverage report contains non-finite token {token}")


def validate_changed_module_boundary(
    configured: Sequence[str],
    derived: Sequence[str],
) -> None:
    configured_modules = set(changed_python_modules(configured))
    derived_modules = set(derived)
    missing = tuple(sorted(derived_modules - configured_modules))
    extra = tuple(sorted(configured_modules - derived_modules))
    if missing or extra:
        raise CoverageBoundaryError(missing, extra)


def validate_changed_module_coverage(
    report: CoverageReport,
    changed_modules: Sequence[str],
    threshold: float,
) -> None:
    files = _mapping(report, "files", "coverage report")
    threshold_percent = _parse_percent(
        {"threshold": threshold}, "threshold", "changed-module"
    )
    for module in changed_modules:
        module_report = _mapping(files, module, "coverage files")
        summary = _mapping(module_report, "summary", f"coverage report for {module}")
        for spec in (LINE_MODULE, BRANCH_MODULE):
            metric = CoverageMetric.parse(summary, spec, allow_empty=True)
            if metric.is_below(threshold_percent):
                raise CoverageThresholdError(
                    f"{module} {spec.label.removeprefix('module ')} coverage "
                    f"{metric.percent:.2f}% is below {threshold_percent:.2f}%"
                )


def check_coverage(report_path: Path, base_ref: str | None = None) -> int:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        ratchet = tomllib.load(pyproject_file)["tool"]["phatch"]["coverage-ratchet"]
    try:
        with report_path.open("rb") as report_file:
            report = json.load(report_file, parse_constant=_reject_non_finite_constant)
        if not isinstance(report, Mapping):
            raise CoverageReportError("coverage report must be a mapping")
        totals = _mapping(report, "totals", "coverage report")
        line = CoverageMetric.parse(totals, LINE_TOTAL, allow_empty=False)
        branch = CoverageMetric.parse(totals, BRANCH_TOTAL, allow_empty=False)
        line_ratchet = _parse_percent(ratchet, "line", "coverage ratchet")
        branch_ratchet = _parse_percent(ratchet, "branch", "coverage ratchet")
        changed_ratchet = _parse_percent(ratchet, "changed", "coverage ratchet")
        print(
            f"coverage ratchet: line={line.percent:.2f}% branch={branch.percent:.2f}%"
        )
        if line.is_below(line_ratchet) or branch.is_below(branch_ratchet):
            return 1
        changed_modules = derive_changed_python_modules(base_ref)
        validate_changed_module_coverage(report, changed_modules, changed_ratchet)
    except (
        CoverageBoundaryError,
        CoverageReportError,
        CoverageThresholdError,
        GitBoundaryError,
        KeyError,
    ) as error:
        print(f"changed-module coverage: {error}")
        return 1
    return 0
