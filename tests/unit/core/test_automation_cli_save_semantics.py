import io
import json
from pathlib import Path

import pytest
from PIL import Image

from phatch.services.automation_cli import run_automation_cli
from phatch.services.recovery_journal import RecoveryJournal
from phatch.services.structured_report import ExitCode


def _write_save_action(path: Path, output: Path, **fields: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "Save semantics",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "png",
                            **fields,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_one_worker_preserves_legacy_dynamic_resolution(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    action_list = tmp_path / "save.phatch"
    output = tmp_path / "output"
    Image.new("RGB", (8, 6), "blue").save(source, dpi=(96, 96))
    _write_save_action(action_list, output)
    stderr = io.StringIO()

    # When
    exit_status = run_automation_cli(
        (
            "--verbose",
            "--max-workers",
            "1",
            "--report-format=json",
            str(action_list),
            str(source),
        ),
        io.StringIO(),
        stderr,
    )

    # Then
    assert exit_status == ExitCode.SUCCESS
    assert "execution_mode=serial" in stderr.getvalue()
    with Image.open(output / "source.png") as saved:
        assert saved.info["dpi"] == pytest.approx((96, 96), abs=0.1)


def test_keep_does_not_overwrite_existing_output(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    action_list = tmp_path / "save.phatch"
    output = tmp_path / "output"
    output.mkdir()
    destination = output / source.name
    Image.new("RGB", (8, 6), "blue").save(source)
    Image.new("RGB", (8, 6), "red").save(destination)
    original = destination.read_bytes()
    _write_save_action(action_list, output, metadata="no", resolution="72")
    stderr = io.StringIO()

    # When
    exit_status = run_automation_cli(
        (
            "--keep",
            "--verbose",
            "--max-workers",
            "2",
            "--report-format=json",
            str(action_list),
            str(source),
        ),
        io.StringIO(),
        stderr,
    )

    # Then
    assert exit_status == ExitCode.SUCCESS
    assert destination.read_bytes() == original
    assert "--keep requires" in stderr.getvalue()


def test_resume_does_not_rewrite_or_double_journal(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "source.png"
    action_list = tmp_path / "save.phatch"
    output = tmp_path / "output"
    journal = tmp_path / "journal.jsonl"
    Image.new("RGB", (8, 6), "blue").save(source)
    _write_save_action(action_list, output, metadata="no", resolution="72")
    arguments = (
        "--resume",
        str(journal),
        "--max-workers",
        "2",
        "--report-format=json",
        str(action_list),
        str(source),
    )
    first_status = run_automation_cli(arguments, io.StringIO(), io.StringIO())
    destination = output / source.name
    first_inode = destination.stat().st_ino
    first_records = RecoveryJournal(journal).records()

    # When
    second_status = run_automation_cli(arguments, io.StringIO(), io.StringIO())

    # Then
    assert first_status == ExitCode.SUCCESS
    assert second_status == ExitCode.SUCCESS
    assert destination.stat().st_ino == first_inode
    assert RecoveryJournal(journal).records() == first_records
