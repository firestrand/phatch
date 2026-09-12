from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from phatch.core.execution_types import (
    RecoveryReason,
    RecoveryReevaluation,
    ReportFile,
)
from phatch.services.recovery import (
    JournalCorruptionError,
    JournalWriteError,
    RecoveryConfig,
    RecoveryJournal,
    RecoverySession,
    action_list_digest,
    file_identity,
)


def test_journal_appends_durable_utc_completed_record_and_recovers_reports(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    session = RecoverySession(journal, "actions-v1")

    session.record_completed(source, (ReportFile(source, output),), ())

    raw = json.loads(journal.path.read_text().splitlines()[0])
    assert datetime.fromisoformat(raw["timestamp"]).tzinfo is UTC
    recovered = session.completed_reports(source)
    assert recovered is not None
    assert isinstance(recovered, tuple)
    assert recovered[0].path == output


def test_journal_ignores_only_a_truncated_final_record(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    session = RecoverySession(journal, "actions-v1")
    session.record_completed(source, (ReportFile(source, output),), ())
    with journal.path.open("ab") as stream:
        stream.write(b'{"timestamp":"truncated')

    assert RecoverySession(journal, "actions-v1").completed_reports(source)


def test_journal_rejects_corrupt_interior_record(tmp_path: Path) -> None:
    path = tmp_path / "batch.jsonl"
    path.write_bytes(b"not-json\n{}\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("input", RecoveryReason.INPUT_CHANGED),
        ("actions", RecoveryReason.ACTIONS_CHANGED),
        ("missing", RecoveryReason.OUTPUT_CHANGED),
        ("corrupt", RecoveryReason.OUTPUT_CHANGED),
    ],
)
def test_resume_never_skips_stale_or_unverified_output(
    tmp_path: Path, change: str, reason: RecoveryReason
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    RecoverySession(journal, "actions-v1").record_completed(
        source, (ReportFile(source, output),), ()
    )

    if change == "input":
        source.write_bytes(b"changed source")
    elif change == "missing":
        output.unlink()
    elif change == "corrupt":
        output.write_bytes(b"changed output")
    digest = "actions-v2" if change == "actions" else "actions-v1"

    result = RecoverySession(journal, digest).completed_reports(source)
    assert result == RecoveryReevaluation(reason)


def test_action_digest_and_file_identity_are_content_sensitive(tmp_path: Path) -> None:
    path = tmp_path / "input"
    path.write_bytes(b"one")
    first = file_identity(path)
    path.write_bytes(b"two")

    assert first != file_identity(path)
    assert action_list_digest(({"label": "A", "value": 1},)) != action_list_digest(
        ({"label": "A", "value": 2},)
    )


def test_recovery_config_requires_absolute_journal_path(tmp_path: Path) -> None:
    assert RecoveryConfig(tmp_path / "batch.jsonl").journal_path.is_absolute()
    with pytest.raises(ValueError):
        RecoveryConfig(Path("relative.jsonl"))


def test_failed_journal_flush_rolls_back_record(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    real_fsync = os.fsync
    calls = 0

    def fail_once(descriptor: int) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("flush failed")
        real_fsync(descriptor)

    monkeypatch.setattr("phatch.services.recovery_journal.os.fsync", fail_once)

    with pytest.raises(OSError, match="flush failed"):
        RecoverySession(journal, "actions").record_completed(
            source, (ReportFile(source, output),), ()
        )

    assert journal.records() == ()


def test_append_repairs_truncated_tail_before_new_record(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    session = RecoverySession(journal, "actions")
    session.record_completed(source, (ReportFile(source, output),), ())
    with journal.path.open("ab") as stream:
        stream.write(b"truncated")

    session.record_failed(source, ())

    assert len(journal.records()) == 2
    assert session.completed_reports(source) == RecoveryReevaluation(
        RecoveryReason.PREVIOUSLY_FAILED
    )


def test_journal_write_error_names_incomplete_path(tmp_path: Path) -> None:
    path = tmp_path / "batch.jsonl"
    assert str(JournalWriteError(path)) == f"incomplete recovery journal write: {path}"


def valid_record(tmp_path: Path) -> dict[str, object]:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "source.jsonl")
    RecoverySession(journal, "actions").record_completed(
        source, (ReportFile(source, output),), ()
    )
    return json.loads(journal.path.read_text())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("version", 2),
        ("timestamp", "2026-01-01T00:00:00"),
        ("input", []),
        ("outputs", {}),
        ("issues", {}),
        ("issues", [3]),
        ("action_digest", 3),
        ("state", 3),
        ("state", "unknown"),
    ],
)
def test_journal_rejects_invalid_top_level_record_shapes(
    tmp_path: Path, field: str, value: object
) -> None:
    record = valid_record(tmp_path)
    record[field] = value
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(record) + "\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()


@pytest.mark.parametrize("field", ["path", "size", "modified_ns", "sha256"])
def test_journal_rejects_invalid_input_identity(tmp_path: Path, field: str) -> None:
    record = valid_record(tmp_path)
    input_data = record["input"]
    assert isinstance(input_data, dict)
    input_data[field] = None
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(record) + "\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()


@pytest.mark.parametrize(
    "value",
    [
        None,
        {"path": None, "size": 1, "sha256": "x", "modified_ns": 1},
    ],
)
def test_journal_rejects_invalid_output_identity(tmp_path: Path, value: object) -> None:
    record = valid_record(tmp_path)
    record["outputs"] = [value]
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(record) + "\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()


def test_journal_rejects_backup_outside_output_directory(tmp_path: Path) -> None:
    record = valid_record(tmp_path)
    outputs = record["outputs"]
    assert isinstance(outputs, list)
    output = outputs[0]
    assert isinstance(output, dict)
    output["original_exists"] = True
    output["backup_path"] = str(tmp_path.parent / ".output.png.hostile.bak")
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(record) + "\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()


@pytest.mark.parametrize(
    ("original_exists", "backup_value"),
    [
        ("yes", None),
        (None, 7),
        (True, None),
        (False, ".output.png.existing.bak"),
    ],
)
def test_journal_rejects_inconsistent_output_backup_metadata(
    tmp_path: Path,
    original_exists: bool | str | None,
    backup_value: int | str | None,
) -> None:
    record = valid_record(tmp_path)
    outputs = record["outputs"]
    assert isinstance(outputs, list)
    output = outputs[0]
    assert isinstance(output, dict)
    output["original_exists"] = original_exists
    output["backup_path"] = (
        str(tmp_path / backup_value) if isinstance(backup_value, str) else backup_value
    )
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(record) + "\n")

    with pytest.raises(JournalCorruptionError):
        RecoveryJournal(path).records()
