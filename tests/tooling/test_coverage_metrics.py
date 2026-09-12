import json
import math
import tomllib
from pathlib import Path

import pytest

from scripts import coverage_policy

MODULE = "scripts/zero.py"


def metric_summary() -> dict[str, int | float]:
    return {
        "covered_lines": 10,
        "num_statements": 10,
        "percent_statements_covered": 100.0,
        "covered_branches": 4,
        "num_branches": 4,
        "percent_branches_covered": 100.0,
    }


def coverage_report() -> dict[str, object]:
    return {
        "files": {MODULE: {"summary": metric_summary()}},
        "totals": {
            "covered_lines": 10,
            "num_statements": 10,
            "covered_branches": 4,
            "num_branches": 4,
        },
    }


def module_summary(report: dict[str, object]) -> dict[str, object]:
    files = report["files"]
    assert isinstance(files, dict)
    module = files[MODULE]
    assert isinstance(module, dict)
    summary = module["summary"]
    assert isinstance(summary, dict)
    return summary


def configure_policy(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        """
[tool.phatch.coverage-ratchet]
line = 90.0
branch = 90.0
changed = 90.0
changed-modules = ["scripts/zero.py"]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(coverage_policy, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        coverage_policy,
        "derive_changed_python_modules",
        lambda base_ref: (MODULE,),
    )
    return tmp_path / "coverage.json"


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_json_non_finite_tokens_fail_closed(
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    payload = json.dumps(coverage_report()).replace(
        '"percent_statements_covered": 100.0',
        f'"percent_statements_covered": {token}',
        1,
    )
    report_path.write_text(payload, encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize(
    "percent_key",
    ["percent_statements_covered", "percent_branches_covered"],
)
@pytest.mark.parametrize(
    "value",
    [True, "NaN", "Infinity", "-Infinity", -0.01, 100.01, math.nan, math.inf],
)
def test_module_percentages_reject_invalid_values(
    percent_key: str, value: object
) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[percent_key] = value

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


@pytest.mark.parametrize(
    "key", ["covered_lines", "num_statements", "covered_branches", "num_branches"]
)
@pytest.mark.parametrize("value", [True, "10", -1, 1.5])
def test_module_counts_reject_invalid_values(key: str, value: object) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[key] = value

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


@pytest.mark.parametrize(
    ("covered_key", "covered"), [("covered_lines", 11), ("covered_branches", 5)]
)
def test_module_counts_reject_covered_above_total(
    covered_key: str, covered: int
) -> None:
    report = coverage_report()
    module_summary(report)[covered_key] = covered

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


@pytest.mark.parametrize(
    "missing_key",
    [
        "covered_lines",
        "num_statements",
        "percent_statements_covered",
        "covered_branches",
        "num_branches",
        "percent_branches_covered",
    ],
)
def test_module_metrics_require_every_numeric_key(missing_key: str) -> None:
    report = coverage_report()
    del module_summary(report)[missing_key]

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


@pytest.mark.parametrize(
    ("covered_key", "total_key", "percent_key", "covered", "percent"),
    [
        ("covered_lines", "num_statements", "percent_statements_covered", 1, 100.0),
        ("covered_lines", "num_statements", "percent_statements_covered", 0, 0.0),
        ("covered_branches", "num_branches", "percent_branches_covered", 1, 100.0),
        ("covered_branches", "num_branches", "percent_branches_covered", 0, 0.0),
    ],
)
def test_module_zero_denominators_require_consistent_zero_metrics(
    covered_key: str,
    total_key: str,
    percent_key: str,
    covered: int,
    percent: float,
) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[covered_key] = covered
    summary[total_key] = 0
    summary[percent_key] = percent

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


def test_zero_statement_zero_branch_module_is_vacuously_covered() -> None:
    report = coverage_report()
    files = report["files"]
    assert isinstance(files, dict)
    module = files[MODULE]
    assert isinstance(module, dict)
    module["summary"] = {
        "covered_lines": 0,
        "num_statements": 0,
        "percent_statements_covered": 100.0,
        "covered_branches": 0,
        "num_branches": 0,
        "percent_branches_covered": 100.0,
    }

    coverage_policy.validate_changed_module_boundary((MODULE,), (MODULE,))
    coverage_policy.validate_changed_module_coverage(report, (MODULE,), 90.0)


def test_module_percentage_must_match_nonzero_counts() -> None:
    report = coverage_report()
    module_summary(report)["percent_statements_covered"] = 99.0

    with pytest.raises(coverage_policy.CoverageReportError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 0.0)


@pytest.mark.parametrize(
    "spec", [coverage_policy.LINE_MODULE, coverage_policy.BRANCH_MODULE]
)
def test_module_metric_exactly_at_threshold_passes(
    spec: coverage_policy.MetricSpec,
) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[spec.covered_key] = 9
    summary[spec.total_key] = 10
    assert spec.percent_key is not None
    summary[spec.percent_key] = 90.0

    coverage_policy.validate_changed_module_coverage(report, (MODULE,), 90.0)


@pytest.mark.parametrize(
    "spec", [coverage_policy.LINE_MODULE, coverage_policy.BRANCH_MODULE]
)
def test_module_metric_one_count_below_threshold_fails(
    spec: coverage_policy.MetricSpec,
) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[spec.covered_key] = 899_999_999
    summary[spec.total_key] = 1_000_000_000
    assert spec.percent_key is not None
    summary[spec.percent_key] = 89.9999999

    with pytest.raises(coverage_policy.CoverageThresholdError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 90.0)


@pytest.mark.parametrize(
    "spec", [coverage_policy.LINE_MODULE, coverage_policy.BRANCH_MODULE]
)
def test_module_metric_rounded_to_threshold_still_fails(
    spec: coverage_policy.MetricSpec,
) -> None:
    report = coverage_report()
    summary = module_summary(report)
    summary[spec.covered_key] = 1_799_999_999
    summary[spec.total_key] = 2_000_000_000
    assert spec.percent_key is not None
    summary[spec.percent_key] = 90.0

    with pytest.raises(coverage_policy.CoverageThresholdError):
        coverage_policy.validate_changed_module_coverage(report, (MODULE,), 90.0)


def test_ruff_positive_boundary_includes_coverage_policy() -> None:
    with (Path(__file__).parents[2] / "pyproject.toml").open("rb") as config_file:
        ruff_include = tomllib.load(config_file)["tool"]["ruff"]["include"]

    assert "scripts/coverage_policy.py" in ruff_include
