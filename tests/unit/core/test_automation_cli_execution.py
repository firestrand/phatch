import io
import json
from pathlib import Path

import pytest
from PIL import Image

from phatch.services import automation_cli
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

    stdout = io.StringIO()
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
