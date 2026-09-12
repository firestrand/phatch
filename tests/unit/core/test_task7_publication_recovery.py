from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.execution_types import RecoveryConfiguration
from phatch.services.recovery import JournalWriteError, RecoveryJournal
from tests.unit.core.test_execution_characterization_batch import batch_settings
from tests.unit.core.test_legacy_execution_public_api import (
    Action,
    _configure_real_execution,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TransactionalOutputsAction(Action):
    def __init__(self, outputs: tuple[Path, ...]) -> None:
        super().__init__("transactional-outputs", True)
        self.outputs = outputs
        self.calls = 0
        self.photo = None

    def dump(self) -> dict[str, str | int]:
        return {"label": self.label, "outputs": len(self.outputs)}

    def apply(self, photo, settings, cache):
        self.calls += 1
        self.photo = photo
        for output in self.outputs:
            photo.save(str(output), "PNG", False)
        return photo


def test_intent_journal_failure_prevents_publication_and_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    destination = tmp_path / "output.png"
    Image.new("RGB", (3, 2), "blue").save(source, format="PNG")
    destination.write_bytes(b"OLD_DESTINATION")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    action = TransactionalOutputsAction((destination,))

    def fail_append(self, record):
        raise JournalWriteError(self.path)

    monkeypatch.setattr(RecoveryJournal, "append", fail_append)

    with pytest.raises(JournalWriteError):
        api.apply_actions_to_photos_with_recovery(
            [action],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source)],
        )

    assert destination.read_bytes() == b"OLD_DESTINATION"
    assert action.photo is not None
    assert action.photo.report_files == []


def test_crash_after_replace_recovers_prepared_output_without_reapplying(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    destination = tmp_path / "output.png"
    Image.new("RGB", (3, 2), "blue").save(source, format="PNG")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    action = TransactionalOutputsAction((destination,))
    original_append = RecoveryJournal.append

    def crash_on_completed(self, record):
        if record["state"] == "completed":
            raise KeyboardInterrupt
        original_append(self, record)

    monkeypatch.setattr(RecoveryJournal, "append", crash_on_completed)
    with pytest.raises(KeyboardInterrupt):
        api.apply_actions_to_photos_with_recovery(
            [action],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source)],
        )

    published_hash = _sha256(destination)
    published_inode = destination.stat().st_ino
    records_before = RecoveryJournal(recovery.journal_path).records()
    assert [record["state"] for record in records_before] == ["prepared"]
    monkeypatch.setattr(RecoveryJournal, "append", original_append)
    resumed = TransactionalOutputsAction((destination,))
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )

    assert resumed.calls == 0
    assert _sha256(destination) == published_hash
    assert destination.stat().st_ino == published_inode
    records_after = RecoveryJournal(recovery.journal_path).records()
    assert [record["state"] for record in records_after] == [
        "prepared",
        "completed",
    ]


def test_partial_multioutput_publication_remains_recoverable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    outputs = (tmp_path / "first.png", tmp_path / "second.png")
    Image.new("RGB", (3, 2), "blue").save(source, format="PNG")
    outputs[0].write_bytes(b"ORIGINAL_FIRST")
    outputs[1].write_bytes(b"ORIGINAL_SECOND")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    original_replace = os.replace
    replaces = 0

    def fail_second_replace(source_path, destination_path):
        nonlocal replaces
        replaces += 1
        if replaces == 2:
            raise PermissionError(13, "second output locked", destination_path)
        original_replace(source_path, destination_path)

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", fail_second_replace
    )
    with pytest.raises(PermissionError):
        api.apply_actions_to_photos_with_recovery(
            [TransactionalOutputsAction(outputs)],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source)],
        )
    records = RecoveryJournal(recovery.journal_path).records()
    assert len(records) == 1
    assert records[0]["state"] == "prepared"
    assert len(records[0]["outputs"]) == 2
    assert outputs[0].read_bytes() == b"ORIGINAL_FIRST"
    assert outputs[1].read_bytes() == b"ORIGINAL_SECOND"

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", original_replace
    )
    resumed = TransactionalOutputsAction(outputs)
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )

    assert resumed.calls == 1
    assert all(output.is_file() for output in outputs)


def test_failed_multioutput_publication_removes_new_destination(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    outputs = (tmp_path / "first.png", tmp_path / "second.png")
    Image.new("RGB", (3, 2), "blue").save(source, format="PNG")
    outputs[1].write_bytes(b"ORIGINAL_SECOND")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    original_replace = os.replace
    replaces = 0

    def fail_second_replace(source_path, destination_path):
        nonlocal replaces
        replaces += 1
        if replaces == 2:
            raise PermissionError(13, "second output locked", destination_path)
        original_replace(source_path, destination_path)

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", fail_second_replace
    )

    with pytest.raises(PermissionError):
        api.apply_actions_to_photos_with_recovery(
            [TransactionalOutputsAction(outputs)],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source)],
        )

    records = RecoveryJournal(recovery.journal_path).records()
    assert [record["state"] for record in records] == ["prepared"]
    assert not outputs[0].exists()
    assert outputs[1].read_bytes() == b"ORIGINAL_SECOND"


def test_restart_reconciles_interrupted_multioutput_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    outputs = (tmp_path / "first.png", tmp_path / "second.png")
    Image.new("RGB", (3, 2), "blue").save(source, format="PNG")
    outputs[0].write_bytes(b"ORIGINAL_FIRST")
    outputs[1].write_bytes(b"ORIGINAL_SECOND")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    original_replace = os.replace
    replaces = 0

    def interrupt_second_replace(source_path, destination_path):
        nonlocal replaces
        replaces += 1
        if replaces == 2:
            raise KeyboardInterrupt
        original_replace(source_path, destination_path)

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", interrupt_second_replace
    )
    with pytest.raises(KeyboardInterrupt):
        api.apply_actions_to_photos_with_recovery(
            [TransactionalOutputsAction(outputs)],
            batch_settings(no_save=True, overwrite=True),
            recovery,
            [str(source)],
        )

    assert [
        record["state"] for record in RecoveryJournal(recovery.journal_path).records()
    ] == ["prepared"]
    assert len(tuple(tmp_path.glob(".*.bak"))) == 2

    monkeypatch.setattr(
        "phatch.services.output_transaction.os.replace", original_replace
    )
    resumed = TransactionalOutputsAction(outputs)
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )

    assert resumed.calls == 1
    assert all(output.is_file() for output in outputs)
    assert not tuple(tmp_path.glob(".*.bak"))
