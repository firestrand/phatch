import argparse
import io
import json
from pathlib import Path

import pytest
from PIL import Image

from phatch.core import config
from phatch.services import automation_cli
from phatch.services.action_schema import ActionDocument
from phatch.services.automation_execution import (
    AutomationExecutionRequest,
    execute_automation,
)
from phatch.services.completion import collect_completion_events
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import ExitCode


def test_live_save_uses_user_worker_setting_and_coordinator_recovery(
    tmp_path: Path,
) -> None:
    output = tmp_path / "output"
    journal = tmp_path / "journal.jsonl"
    action_list = tmp_path / "save.phatch"
    action_list.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "parallel save",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "png",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    image = tmp_path / "input.png"
    Image.new("RGB", (16, 12), "navy").save(image)
    stdout = io.StringIO()
    stderr = io.StringIO()
    receipts = []

    with collect_completion_events(receipts.append):
        result = automation_cli.run_automation_cli(
            (
                "--verbose",
                "--max-workers",
                "1",
                "--resume",
                str(journal),
                "--report-format=json",
                str(action_list),
                str(image),
            ),
            stdout,
            stderr,
        )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["outcome"] == "success"
    assert "execution_mode=serial requested_workers=1" in stderr.getvalue()
    assert (output / "input.png").is_file()
    assert journal.is_file()
    assert len(receipts) == 1
    assert receipts[0].owner == "automation"

    stdout = io.StringIO()
    with collect_completion_events(receipts.append):
        result = automation_cli.run_automation_cli(
            (
                "--max-workers",
                "1",
                "--report-format=json",
                str(action_list),
                str(image),
            ),
            stdout,
            io.StringIO(),
        )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["outcome"] == "success"
    assert len(receipts) == 2
    assert receipts[0].request_id != receipts[1].request_id


@pytest.mark.parametrize(
    ("verbosity", "reports_execution"),
    [(("--verbose",), True), ((), False)],
)
def test_live_save_reports_parallel_worker_execution(
    tmp_path: Path,
    verbosity: tuple[str, ...],
    reports_execution: bool,
) -> None:
    output = tmp_path / "output"
    action_list = tmp_path / "save.phatch"
    action_list.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "parallel save",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "png",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    images = (tmp_path / "first.png", tmp_path / "second.png")
    for image in images:
        Image.new("RGB", (64, 64), "navy").save(image)
    stdout = io.StringIO()
    stderr = io.StringIO()
    receipts = []

    with collect_completion_events(receipts.append):
        result = automation_cli.run_automation_cli(
            (
                *verbosity,
                "--max-workers",
                "2",
                "--report-format=json",
                str(action_list),
                *(str(image) for image in images),
            ),
            stdout,
            stderr,
        )

    assert result == ExitCode.SUCCESS
    assert json.loads(stdout.getvalue())["outcome"] == "success"
    assert (
        "execution_mode=process requested_workers=2" in stderr.getvalue()
    ) is reports_execution
    assert {path.name for path in output.iterdir()} == {"first.png", "second.png"}
    assert len(receipts) == 1
    assert receipts[0].owner == "automation"


def test_execution_failure_redacts_preflight_roots_in_both_channels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    source = Path("/Volumes/private-client/input/photo.jpg")
    output = Path("/srv/client-export/photo.jpg")
    diagnostic = f"cannot open {source}; output={output}; token=abc"
    request = AutomationExecutionRequest(
        (),
        (source,),
        ActionDocument.from_values("", ()),
        PreflightResult((source,), (output,), (), (), (), (), 1),
        argparse.Namespace(report_format="json"),
    )
    monkeypatch.setattr(
        config,
        "verify_app_user_paths",
        lambda: (_ for _ in ()).throw(OSError(diagnostic)),
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    receipts = []

    # When
    with collect_completion_events(receipts.append):
        result = execute_automation(request, stdout, stderr)

    # Then
    payload = json.loads(stdout.getvalue())
    combined = stdout.getvalue() + stderr.getvalue()
    assert result == ExitCode.PROCESSING_FAILURE
    assert payload["issues"] == [
        "cannot open <input>/photo.jpg; output=<output>/photo.jpg; token=<redacted>"
    ]
    assert stderr.getvalue().strip() == payload["issues"][0]
    assert "/Volumes/private-client" not in combined
    assert "/srv/client-export" not in combined
    assert "token=abc" not in combined
    assert len(receipts) == 1
    assert receipts[0].owner == "automation"
