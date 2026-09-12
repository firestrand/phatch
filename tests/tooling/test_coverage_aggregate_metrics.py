import json
from pathlib import Path

import pytest

from scripts import coverage_policy

MODULE = "scripts/zero.py"


def coverage_report() -> dict[str, object]:
    return {
        "files": {
            MODULE: {
                "summary": {
                    "covered_lines": 10,
                    "num_statements": 10,
                    "percent_statements_covered": 100.0,
                    "covered_branches": 4,
                    "num_branches": 4,
                    "percent_branches_covered": 100.0,
                }
            }
        },
        "totals": {
            "covered_lines": 10,
            "num_statements": 10,
            "covered_branches": 4,
            "num_branches": 4,
        },
    }


def aggregate_totals(report: dict[str, object]) -> dict[str, object]:
    totals = report["totals"]
    assert isinstance(totals, dict)
    return totals


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
def test_aggregate_json_non_finite_tokens_fail_closed(
    token: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    payload = json.dumps(coverage_report()).replace(
        '"totals": {"covered_lines": 10',
        f'"totals": {{"covered_lines": {token}',
    )
    report_path.write_text(payload, encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize(
    "key", ["covered_lines", "num_statements", "covered_branches", "num_branches"]
)
@pytest.mark.parametrize("value", [True, "10", "NaN", "Infinity", "-Infinity", -1, 1.5])
def test_aggregate_counts_fail_closed(
    key: str,
    value: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    aggregate_totals(report)[key] = value
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize(
    ("covered_key", "covered"), [("covered_lines", 11), ("covered_branches", 5)]
)
def test_aggregate_counts_reject_covered_above_total(
    covered_key: str,
    covered: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    aggregate_totals(report)[covered_key] = covered
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize(
    "missing_key",
    ["covered_lines", "num_statements", "covered_branches", "num_branches"],
)
def test_aggregate_metrics_require_numeric_keys(
    missing_key: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    del aggregate_totals(report)[missing_key]
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


def test_consistent_zero_aggregate_denominator_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    totals = aggregate_totals(report)
    totals["covered_lines"] = 0
    totals["num_statements"] = 0
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize(
    "spec", [coverage_policy.LINE_TOTAL, coverage_policy.BRANCH_TOTAL]
)
def test_aggregate_metric_exactly_at_threshold_passes(
    spec: coverage_policy.MetricSpec,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    totals = aggregate_totals(report)
    totals[spec.covered_key] = 9
    totals[spec.total_key] = 10
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 0


@pytest.mark.parametrize(
    "spec", [coverage_policy.LINE_TOTAL, coverage_policy.BRANCH_TOTAL]
)
def test_aggregate_metric_one_count_below_threshold_fails(
    spec: coverage_policy.MetricSpec,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report = coverage_report()
    totals = aggregate_totals(report)
    totals[spec.covered_key] = 899_999_999
    totals[spec.total_key] = 1_000_000_000
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize("ratchet_key", ["line", "branch", "changed"])
@pytest.mark.parametrize("toml_value", ["true", '"90"', "-1.0", "100.01", "nan", "inf"])
def test_repository_ratchets_reject_invalid_percentages(
    ratchet_key: str,
    toml_value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report_path.write_text(json.dumps(coverage_report()), encoding="utf-8")
    config_path = tmp_path / "pyproject.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            f"{ratchet_key} = 90.0", f"{ratchet_key} = {toml_value}"
        ),
        encoding="utf-8",
    )

    assert coverage_policy.check_coverage(report_path) == 1


@pytest.mark.parametrize("missing_key", ["line", "branch", "changed"])
def test_repository_ratchets_require_every_numeric_key(
    missing_key: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = configure_policy(tmp_path, monkeypatch)
    report_path.write_text(json.dumps(coverage_report()), encoding="utf-8")
    config_path = tmp_path / "pyproject.toml"
    configuration = config_path.read_text(encoding="utf-8")
    retained_lines = [
        line
        for line in configuration.splitlines()
        if not line.startswith(f"{missing_key} =")
    ]
    config_path.write_text("\n".join(retained_lines), encoding="utf-8")

    assert coverage_policy.check_coverage(report_path) == 1
