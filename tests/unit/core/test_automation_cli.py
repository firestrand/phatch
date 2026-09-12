import io
import json
from pathlib import Path

from PIL import Image

from phatch.core.action_registry import ActionRegistryBuildFailure
from phatch.core.execution_types import ExecutionIssue, IssueSeverity, IssueStage
from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.services import automation_cli
from phatch.services.structured_report import ExitCode


def test_malformed_schema_fails_before_registry_construction(
    tmp_path: Path, monkeypatch
) -> None:
    action_list = tmp_path / "bad.phatch"
    action_list.write_text('{"schema_version":3,"actions":[],"bad":true}')
    constructed = []
    monkeypatch.setattr(
        automation_cli,
        "_build_registry",
        lambda: constructed.append(True),
    )
    stdout = io.StringIO()
    stderr = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--dry-run", "--report-format", "json", str(action_list)),
        stdout,
        stderr,
    )

    assert result == ExitCode.VALIDATION_FAILURE
    assert constructed == []
    assert json.loads(stdout.getvalue())["outcome"] == "validation_failure"
    assert "unknown document key" in stderr.getvalue()


def test_json_failure_keeps_diagnostic_out_of_stdout(tmp_path: Path) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--dry-run", "--report-format", "json", str(tmp_path / "missing")),
        stdout,
        stderr,
    )

    payload = json.loads(stdout.getvalue())
    assert result == ExitCode.VALIDATION_FAILURE
    assert payload["kind"] == "error"
    assert "No such file" not in stdout.getvalue().splitlines()[0].split("{")[0]
    assert "No such file" in stderr.getvalue()


def test_automation_request_detection_covers_structured_flags() -> None:
    assert automation_cli.is_automation_request(("--dry-run",)) is True
    assert automation_cli.is_automation_request(("image.png",)) is False


def test_report_format_scanning_defaults_and_accepts_both_option_forms() -> None:
    assert automation_cli.report_format_from_arguments(("image.png",)) == "text"
    assert (
        automation_cli.report_format_from_arguments(("--report-format", "json"))
        == "json"
    )
    assert automation_cli.report_format_from_arguments(("--report-format=json",)) == (
        "json"
    )


def test_capabilities_and_missing_action_list_reports(monkeypatch) -> None:
    monkeypatch.setattr(automation_cli, "_capabilities", lambda: ())
    stdout = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--capabilities", "--report-format", "json"), stdout, io.StringIO()
    )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["kind"] == "capabilities"

    stderr = io.StringIO()
    result = automation_cli.run_automation_cli(("--dry-run",), io.StringIO(), stderr)
    assert result == ExitCode.VALIDATION_FAILURE
    assert "No action list" in stderr.getvalue()


def test_registry_build_failure_is_processing_failure(
    tmp_path: Path, monkeypatch
) -> None:
    action_list = tmp_path / "empty.phatch"
    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "border", "fields": {}}]}',
        encoding="utf-8",
    )
    issue = ExecutionIssue(
        IssueStage.PLUGIN_IMPORT,
        IssueSeverity.ERROR,
        "registry failed",
    )
    monkeypatch.setattr(
        automation_cli,
        "_build_registry",
        lambda: ActionRegistryBuildFailure((issue,)),
    )
    stderr = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--dry-run", str(action_list)), io.StringIO(), stderr
    )

    assert result == ExitCode.PROCESSING_FAILURE
    assert "registry failed" in stderr.getvalue()


def test_dry_run_reports_success_unsafe_and_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    action_list = tmp_path / "action.phatch"
    action_list.write_text(
        '{"schema_version": 3, "description": "", "actions": []}',
        encoding="utf-8",
    )
    stdout = io.StringIO()
    image = tmp_path / "input.png"
    Image.new("RGB", (1, 1)).save(image)

    result = automation_cli.run_automation_cli(
        ("--dry-run", "--report-format", "json", str(action_list), str(image)),
        stdout,
        io.StringIO(),
    )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["kind"] == "preflight"

    unavailable = Capability(
        CapabilityId("imagemagick-6"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "missing",
    )
    monkeypatch.setattr(automation_cli, "_capabilities", lambda: (unavailable,))
    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "imagemagick", "fields": {}}]}',
        encoding="utf-8",
    )
    result = automation_cli.run_automation_cli(
        ("--dry-run", str(action_list), str(image)), io.StringIO(), io.StringIO()
    )
    assert result == ExitCode.UNAVAILABLE_CAPABILITY

    result = automation_cli.run_automation_cli(
        (str(action_list), str(image)), io.StringIO(), io.StringIO()
    )
    assert result == ExitCode.UNAVAILABLE_CAPABILITY

    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "geek", "fields": {}}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(automation_cli, "_capabilities", lambda: ())
    result = automation_cli.run_automation_cli(
        ("--dry-run", str(action_list), str(image)), io.StringIO(), io.StringIO()
    )
    assert result == ExitCode.VALIDATION_FAILURE

    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "unknown", "fields": {}}]}',
        encoding="utf-8",
    )
    result = automation_cli.run_automation_cli(
        ("--dry-run", str(action_list), str(image)), io.StringIO(), io.StringIO()
    )
    assert result == ExitCode.VALIDATION_FAILURE


def test_live_no_save_execution_reports_success(tmp_path: Path) -> None:
    action_list = tmp_path / "empty.phatch"
    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "border", "fields": {}}]}',
        encoding="utf-8",
    )
    image = tmp_path / "input.png"
    Image.new("RGB", (1, 1)).save(image)
    stdout = io.StringIO()

    result = automation_cli.run_automation_cli(
        ("--no-save", "--report-format", "json", str(action_list), str(image)),
        stdout,
        io.StringIO(),
    )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["outcome"] == "success"

    stdout = io.StringIO()
    result = automation_cli.run_automation_cli(
        (
            "--no-save",
            "--resume",
            str(tmp_path / "journal.jsonl"),
            str(action_list),
            str(image),
        ),
        stdout,
        io.StringIO(),
    )

    assert result == ExitCode.SUCCESS
    assert "Outcome: success" in stdout.getvalue()


def test_live_non_save_reports_parallel_constraint(tmp_path: Path) -> None:
    # Given
    action_list = tmp_path / "border.phatch"
    action_list.write_text(
        '{"schema_version": 3, "description": "", '
        '"actions": [{"id": "border", "fields": {}}]}',
        encoding="utf-8",
    )
    image = tmp_path / "input.png"
    Image.new("RGB", (1, 1)).save(image)
    stderr = io.StringIO()

    # When
    result = automation_cli.run_automation_cli(
        (
            "--no-save",
            "--verbose",
            "--max-workers",
            "2",
            str(action_list),
            str(image),
        ),
        io.StringIO(),
        stderr,
    )

    # Then
    assert result == ExitCode.SUCCESS
    assert "parallel_constraint=" in stderr.getvalue()
