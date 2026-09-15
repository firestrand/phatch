import io
import json
from pathlib import Path

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.services import automation_cli
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import ExitCode


def test_missing_action_list_redacts_requested_roots_in_both_channels() -> None:
    action_list = Path(
        "/Volumes/private-client/config/token=abc/missing config Ω.phatch"
    )
    input_path = Path("/Volumes/private-client/input/photo.jpg")
    stdout = io.StringIO()
    stderr = io.StringIO()

    result = automation_cli.run_automation_cli(
        (
            "--dry-run",
            "--report-format",
            "json",
            str(action_list),
            str(input_path),
        ),
        stdout,
        stderr,
    )

    payload = json.loads(stdout.getvalue())
    combined = stdout.getvalue() + stderr.getvalue()
    assert result == ExitCode.VALIDATION_FAILURE
    assert payload["kind"] == "error"
    assert "<action-list>/missing config Ω.phatch" in payload["issues"][0]
    assert stderr.getvalue().strip() == payload["issues"][0]
    assert "/Volumes/private-client" not in combined
    assert "token=abc" not in combined


def test_unavailable_preflight_redacts_requested_paths_and_compound_text(
    monkeypatch,
) -> None:
    action_list = Path("/Volumes/private-client/config/actions.phatch")
    input_path = Path("/Volumes/private-client/input/photo.jpg")
    output_path = Path("/srv/private-client/output/photo.jpg")
    unavailable = Capability(
        CapabilityId("tool"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "missing",
    )
    preflight = PreflightResult(
        (input_path,),
        (output_path,),
        (),
        (unavailable,),
        (
            f"config={action_list}; input={input_path}; "
            "output=/srv/private-client/output; token=abc",
        ),
        (),
        1,
    )
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda _path, **_kwargs: (
            '{"schema_version": 3, "description": "", "actions": []}'
        ),
    )
    monkeypatch.setattr(automation_cli, "_capabilities", lambda: (unavailable,))
    monkeypatch.setattr(
        automation_cli.PreflightService,
        "build",
        lambda _service, _request: preflight,
    )
    stdout = io.StringIO()

    result = automation_cli.run_automation_cli(
        (
            "--dry-run",
            "--report-format=json",
            str(action_list),
            str(input_path),
        ),
        stdout,
        io.StringIO(),
    )

    serialized = stdout.getvalue()
    payload = json.loads(serialized)
    assert result == ExitCode.UNAVAILABLE_CAPABILITY
    assert payload["inputs"] == ["<input>/photo.jpg"]
    assert payload["planned_outputs"] == ["<output>/photo.jpg"]
    assert payload["unsafe_operations"] == [
        "config=<action-list>/actions.phatch; input=<input>/photo.jpg; "
        "output=<output>; token=<redacted>"
    ]
    assert "/Volumes/private-client" not in serialized
    assert "/srv/private-client" not in serialized
    assert "token=abc" not in serialized
