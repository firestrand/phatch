import json
from pathlib import Path

import pytest

from scripts import coverage_policy, verify

CHANGED_MODULES = (
    "phatch/app.py",
    "phatch/actions/_action_lifecycle.py",
    "phatch/actions/autocontrast.py",
    "phatch/actions/background.py",
    "phatch/actions/border.py",
    "phatch/actions/brightness.py",
    "phatch/actions/canvas.py",
    "phatch/actions/color_to_alpha.py",
    "phatch/actions/colorize.py",
    "phatch/actions/common.py",
    "phatch/actions/contour.py",
    "phatch/actions/contrast.py",
    "phatch/actions/convert_mode.py",
    "phatch/actions/copy.py",
    "phatch/actions/crop.py",
    "phatch/actions/desaturate.py",
    "phatch/actions/effect.py",
    "phatch/actions/equalize.py",
    "phatch/actions/fit.py",
    "phatch/actions/geotag.py",
    "phatch/actions/grid.py",
    "phatch/actions/highlight.py",
    "phatch/actions/invert.py",
    "phatch/actions/mask.py",
    "phatch/actions/maximum.py",
    "phatch/actions/median.py",
    "phatch/actions/minimum.py",
    "phatch/actions/mirror.py",
    "phatch/actions/offset.py",
    "phatch/actions/perspective.py",
    "phatch/actions/posterize.py",
    "phatch/actions/rank.py",
    "phatch/actions/reflection.py",
    "phatch/actions/rename.py",
    "phatch/actions/rotate.py",
    "phatch/actions/round.py",
    "phatch/actions/saturation.py",
    "phatch/actions/save.py",
    "phatch/actions/save_metadata.py",
    "phatch/actions/scale.py",
    "phatch/actions/shadow.py",
    "phatch/actions/sketch.py",
    "phatch/actions/solarize.py",
    "phatch/actions/tamogen.py",
    "phatch/actions/text.py",
    "phatch/actions/time_shift.py",
    "phatch/actions/transpose.py",
    "phatch/actions/warm_up.py",
    "phatch/actions/watermark.py",
    "phatch/actions/geek.py",
    "phatch/actions/_blender_action.py",
    "phatch/actions/_blender_argv.py",
    "phatch/actions/_blender_options.py",
    "phatch/actions/_imagemagick_action.py",
    "phatch/actions/_imagemagick_argv.py",
    "phatch/actions/_lossless_jpeg_options.py",
    "phatch/actions/_lossless_jpeg_transaction.py",
    "phatch/actions/blender.py",
    "phatch/actions/imagemagick.py",
    "phatch/actions/lossless_jpeg.py",
    "phatch/console/console.py",
    "phatch/core/api.py",
    "phatch/core/action_registry.py",
    "phatch/core/plugin_context.py",
    "phatch/core/cli.py",
    "phatch/core/config.py",
    "phatch/core/execution_ports.py",
    "phatch/core/execution_types.py",
    "phatch/core/file_references.py",
    "phatch/core/filesystem.py",
    "phatch/core/models.py",
    "phatch/core/pil.py",
    "phatch/core/preview.py",
    "phatch/core/resource_config.py",
    "phatch/core/settings.py",
    "phatch/core/user_paths.py",
    "phatch/core/windows_names.py",
    "phatch/entrypoints.py",
    "phatch/external_tools.py",
    "phatch/lib/capabilities.py",
    "phatch/lib/capability_probes.py",
    "phatch/lib/external_capability_probes.py",
    "phatch/lib/executables.py",
    "phatch/lib/image_process.py",
    "phatch/lib/image_codecs.py",
    "phatch/lib/imtools.py",
    "phatch/lib/metadata.py",
    "phatch/lib/openImage.py",
    "phatch/lib/process.py",
    "phatch/lib/reverse_translation.py",
    "phatch/lib/subprocess_runner.py",
    "phatch/lib/system.py",
    "phatch/lib/windows/locate.py",
    "phatch/lib/windows/register.py",
    "phatch/lib/windows/shortcut.py",
    "phatch/other/EXIF.py",
    "phatch/phatch.py",
    "phatch/pyWx/dialog_service.py",
    "phatch/pyWx/controller.py",
    "phatch/pyWx/documentation.py",
    "phatch/pyWx/frame_dependencies.py",
    "phatch/resources/__init__.py",
    "phatch/resources/inventory.py",
    "phatch/resources/provider.py",
    "phatch/services/__init__.py",
    "phatch/services/action_list.py",
    "phatch/services/action_schema.py",
    "phatch/services/action_schema_types.py",
    "phatch/services/action_validation.py",
    "phatch/services/automation_cli.py",
    "phatch/services/automation_execution.py",
    "phatch/services/automation_report.py",
    "phatch/services/execution.py",
    "phatch/services/execution_runner.py",
    "phatch/services/image_output.py",
    "phatch/services/file_discovery.py",
    "phatch/services/legacy_actions.py",
    "phatch/services/legacy_execution.py",
    "phatch/services/legacy_recovery.py",
    "phatch/services/legacy_interaction.py",
    "phatch/services/legacy_photos.py",
    "phatch/services/legacy_types.py",
    "phatch/services/output_rollback.py",
    "phatch/services/output_transaction.py",
    "phatch/services/parallel_image_jobs.py",
    "phatch/services/parallel_image_pool.py",
    "phatch/services/parallel_save.py",
    "phatch/services/parallel_save_spec.py",
    "phatch/services/parallel_worker_bootstrap.py",
    "phatch/services/preflight.py",
    "phatch/services/recovery.py",
    "phatch/services/recovery_fingerprint.py",
    "phatch/services/recovery_journal.py",
    "phatch/services/structured_report.py",
    "phatch/windows/droplet.py",
    "phatch/windows/droplet_menu.py",
    "scripts/__init__.py",
    "scripts/artifact_scan.py",
    "scripts/coverage_artifacts.py",
    "scripts/coverage_git.py",
    "scripts/coverage_policy.py",
    "scripts/distribution_smoke.py",
    "scripts/portable_smoke.py",
    "scripts/windows_window_probe.py",
    "scripts/portable_state.py",
    "scripts/release_manifest.py",
    "phatch/release_inventory.py",
    "scripts/verify.py",
)


@pytest.fixture(autouse=True)
def stable_changed_module_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coverage_policy,
        "derive_changed_python_modules",
        lambda base_ref: CHANGED_MODULES,
    )


def write_coverage_report(
    path: Path,
    aggregate: tuple[float, float],
    changed: tuple[float, float] = (100.0, 100.0),
) -> None:
    metric_total = 10_000
    line, branch = aggregate
    changed_line, changed_branch = changed
    path.write_text(
        json.dumps(
            {
                "files": {
                    module: {
                        "summary": {
                            "covered_lines": round(changed_line * 100),
                            "num_statements": metric_total,
                            "percent_statements_covered": changed_line,
                            "covered_branches": round(changed_branch * 100),
                            "num_branches": metric_total,
                            "percent_branches_covered": changed_branch,
                        }
                    }
                    for module in CHANGED_MODULES
                },
                "totals": {
                    "covered_lines": round(line * 100),
                    "num_statements": metric_total,
                    "covered_branches": round(branch * 100),
                    "num_branches": metric_total,
                },
            }
        ),
        encoding="utf-8",
    )


def test_coverage_ratchet_accepts_final_target(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    write_coverage_report(report_path, aggregate=(90.0, 90.0))

    assert coverage_policy.check_coverage(report_path) == 0


def test_coverage_ratchet_rejects_branch_regression(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    write_coverage_report(report_path, aggregate=(100.0, 89.99))

    assert coverage_policy.check_coverage(report_path) == 1


def test_coverage_ratchet_rejects_line_regression(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    write_coverage_report(report_path, aggregate=(89.99, 100.0))

    assert coverage_policy.check_coverage(report_path) == 1


def test_coverage_ratchet_rejects_changed_module_branch_regression(
    tmp_path: Path,
) -> None:
    report_path = tmp_path / "coverage.json"
    write_coverage_report(
        report_path,
        aggregate=(90.0, 90.0),
        changed=(100.0, 89.99),
    )

    assert coverage_policy.check_coverage(report_path) == 1


def test_changed_python_modules_are_sorted_and_scoped_to_production_tools() -> None:
    paths = (
        "tests/tooling/test_verify.py",
        "scripts/verify.py",
        "README.md",
        "phatch/lib/metadata.py",
        "phatch/pyWx/gui.py",
        "scripts/__init__.py",
    )

    assert coverage_policy.changed_python_modules(paths) == (
        "phatch/lib/metadata.py",
        "phatch/pyWx/gui.py",
        "scripts/__init__.py",
        "scripts/verify.py",
    )


@pytest.mark.parametrize(
    ("line_percent", "branch_percent", "expected_message"),
    [
        (89.99, 95.0, "line coverage 89.99% is below 90.00%"),
        (95.0, 89.99, "branch coverage 89.99% is below 90.00%"),
    ],
)
def test_changed_module_policy_enforces_each_metric(
    line_percent: float,
    branch_percent: float,
    expected_message: str,
) -> None:
    report = {
        "files": {
            "scripts/verify.py": {
                "summary": {
                    "covered_lines": round(line_percent * 100),
                    "num_statements": 10_000,
                    "percent_statements_covered": line_percent,
                    "covered_branches": round(branch_percent * 100),
                    "num_branches": 10_000,
                    "percent_branches_covered": branch_percent,
                }
            }
        }
    }

    with pytest.raises(coverage_policy.CoverageThresholdError, match=expected_message):
        coverage_policy.validate_changed_module_coverage(
            report,
            ("scripts/verify.py",),
            threshold=90.0,
        )


def test_changed_module_policy_accepts_both_metrics_at_threshold() -> None:
    report = {
        "files": {
            "scripts/verify.py": {
                "summary": {
                    "covered_lines": 90,
                    "num_statements": 100,
                    "percent_statements_covered": 90.0,
                    "covered_branches": 90,
                    "num_branches": 100,
                    "percent_branches_covered": 90.0,
                }
            }
        }
    }

    coverage_policy.validate_changed_module_coverage(
        report,
        ("scripts/verify.py",),
        threshold=90.0,
    )


@pytest.mark.parametrize(
    "report",
    [
        {"files": []},
        {"files": {"scripts/verify.py": []}},
        {"files": {"scripts/verify.py": {"summary": []}}},
    ],
)
def test_changed_module_policy_rejects_malformed_report_shapes(report) -> None:
    with pytest.raises(TypeError, match="must be a mapping"):
        coverage_policy.validate_changed_module_coverage(
            report,
            ("scripts/verify.py",),
            threshold=90.0,
        )


def test_main_checks_requested_coverage_report(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    write_coverage_report(report_path, aggregate=(100.0, 100.0))

    assert verify.main(["--check-coverage", str(report_path)]) == 0


def test_malformed_coverage_report_fails_clearly(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    report_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        coverage_policy.check_coverage(report_path)
