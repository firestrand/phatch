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
    write_capabilities,
    write_failure,
    write_preflight,
)
from phatch.services.preflight import PreflightResult
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

    write_capabilities((capability(),), "json", json_output)
    write_capabilities((capability(),), "text", text_output)

    assert json.loads(json_output.getvalue())["capabilities"][0]["version"] == "1"
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

    write_preflight(result, AutomationOutcome.SUCCESS, "json", json_output)
    write_preflight(result, AutomationOutcome.SUCCESS, "text", text_output)

    assert json.loads(json_output.getvalue())["estimated_work"] == 1
    assert "Planned outputs: 1" in text_output.getvalue()


def test_failure_reports_write_diagnostics_and_optional_json() -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    code = write_failure(
        AutomationOutcome.VALIDATION_FAILURE,
        "bad",
        "json",
        stdout,
        stderr,
    )

    assert code is ExitCode.VALIDATION_FAILURE
    assert json.loads(stdout.getvalue())["issues"] == ["bad"]
    assert stderr.getvalue() == "bad\n"

    text_stdout = io.StringIO()
    write_failure(
        AutomationOutcome.PROCESSING_FAILURE,
        "failed",
        "text",
        text_stdout,
        io.StringIO(),
    )
    assert text_stdout.getvalue() == ""
