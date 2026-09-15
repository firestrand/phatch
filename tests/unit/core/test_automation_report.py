import io
import json
from pathlib import Path

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.services.automation_report import (
    ReportDestination,
    write_capabilities,
    write_failure,
    write_preflight,
)
from phatch.services.preflight import PreflightResult
from phatch.services.report_privacy import ReportPrivacyContext, SensitiveRoot
from phatch.services.structured_report import AutomationOutcome, ExitCode


def capability() -> Capability:
    return Capability(
        CapabilityId("tool"),
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        "ready",
        version="1",
        executable=Path("/tool"),
    )


def test_capability_reports_support_json_and_text() -> None:
    json_output = io.StringIO()
    text_output = io.StringIO()

    write_capabilities(
        (capability(),), ReportDestination("json", json_output, io.StringIO())
    )
    write_capabilities(
        (capability(),), ReportDestination("text", text_output, io.StringIO())
    )

    payload = json.loads(json_output.getvalue())
    assert payload["report_version"] == 2
    assert payload["capabilities"][0]["version"] == "1"
    assert "tool: available" in text_output.getvalue()


def test_preflight_reports_support_json_and_text() -> None:
    result = PreflightResult(
        (Path("in.png"),),
        (Path("out.png"),),
        (),
        (),
        (),
        (),
        1,
    )
    json_output = io.StringIO()
    text_output = io.StringIO()

    write_preflight(
        result,
        AutomationOutcome.SUCCESS,
        ReportDestination("json", json_output, io.StringIO()),
    )
    write_preflight(
        result,
        AutomationOutcome.SUCCESS,
        ReportDestination("text", text_output, io.StringIO()),
    )

    payload = json.loads(json_output.getvalue())
    assert payload["report_version"] == 2
    assert payload["estimated_work"] == 1
    assert "Planned outputs: 1" in text_output.getvalue()


def test_failure_reports_write_diagnostics_and_optional_json() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = write_failure(
        AutomationOutcome.VALIDATION_FAILURE,
        "bad",
        ReportDestination("json", stdout, stderr),
    )

    assert code is ExitCode.VALIDATION_FAILURE
    payload = json.loads(stdout.getvalue())
    assert payload["report_version"] == 2
    assert payload["issues"] == ["bad"]
    assert stderr.getvalue() == "bad\n"

    text_stdout = io.StringIO()
    write_failure(
        AutomationOutcome.PROCESSING_FAILURE,
        "failed",
        ReportDestination("text", text_stdout, io.StringIO()),
    )
    assert text_stdout.getvalue() == ""


def test_report_writers_redact_paths_and_diagnostics() -> None:
    private_root = Path("/private/report")
    privacy = ReportPrivacyContext((SensitiveRoot(private_root, "<input>"),))
    preflight = PreflightResult(
        (private_root / "in.png",),
        (private_root / "out.png",),
        (),
        (),
        (f"Authorization: Bearer preflight-secret at {private_root}",),
        ("GPS=51.0",),
        1,
    )
    stdout = io.StringIO()

    write_preflight(
        preflight,
        AutomationOutcome.SUCCESS,
        ReportDestination("json", stdout, io.StringIO(), privacy),
    )

    payload = json.loads(stdout.getvalue())
    assert payload["inputs"] == ["<input>/in.png"]
    assert payload["planned_outputs"] == ["<input>/out.png"]
    assert "preflight-secret" not in stdout.getvalue()
    assert "51.0" not in stdout.getvalue()

    failure_stdout = io.StringIO()
    failure_stderr = io.StringIO()
    write_failure(
        AutomationOutcome.PROCESSING_FAILURE,
        f"token=secret at {private_root}/in.png",
        ReportDestination("json", failure_stdout, failure_stderr, privacy),
    )
    combined = failure_stdout.getvalue() + failure_stderr.getvalue()
    assert "secret" not in combined
    assert str(private_root) not in combined


def test_capability_report_redacts_reason_and_executable() -> None:
    private_root = Path("/private/tools")
    privacy = ReportPrivacyContext((SensitiveRoot(private_root, "<tools>"),))
    seeded = Capability(
        CapabilityId("tool"),
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        f"token=secret from {private_root}",
        executable=private_root / "bin/tool",
    )
    stdout = io.StringIO()

    write_capabilities(
        (seeded,), ReportDestination("json", stdout, io.StringIO(), privacy)
    )

    serialized = stdout.getvalue()
    assert "secret" not in serialized
    assert str(private_root) not in serialized
    assert json.loads(serialized)["capabilities"][0]["executable"] == (
        "<tools>/bin/tool"
    )
