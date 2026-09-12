from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from phatch.core import api
from phatch.core.execution_types import (
    ExecutionIssue,
    IssueSeverity,
    IssueStage,
    RecoveryConfiguration,
    RecoveryReason,
    RecoveryReevaluation,
    ReportFile,
)
from phatch.services.recovery import RecoveryJournal, RecoverySession
from tests.unit.core.test_execution_characterization_batch import batch_settings


def test_execution_fingerprint_ignores_runtime_configuration_paths(tmp_path):
    from phatch.services.recovery_fingerprint import execution_fingerprint

    first = batch_settings(no_save=True, overwrite=True)
    second = batch_settings(no_save=True, overwrite=True)
    first["USER_CACHE_PATH"] = str(tmp_path / "first")
    second["USER_CACHE_PATH"] = str(tmp_path / "second")

    assert execution_fingerprint((), first, (), False) == execution_fingerprint(
        (), second, (), False
    )
from tests.unit.core.test_legacy_execution_public_api import (
    Action,
    _configure_real_execution,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class MutatingSourceAction(Action):
    def __init__(self, source: Path, output: Path) -> None:
        super().__init__("mutating-save", True)
        self.source = source
        self.output = output
        self.calls = 0

    def dump(self) -> dict[str, str]:
        return {"label": self.label}

    def apply(self, photo, settings, cache):
        self.calls += 1
        Image.new("RGB", (4, 3), "blue").save(self.source, format="PNG")
        photo.save(str(self.output), "PNG", False)
        return photo


class RepeatOutputAction(Action):
    def __init__(self, output: Path) -> None:
        super().__init__("repeat-save", True)
        self.output = output
        self.calls = 0

    def dump(self) -> dict[str, str]:
        return {"label": self.label}

    def apply(self, photo, settings, cache):
        self.calls += 1
        repeat_index = int(photo.info["repeatindex"])
        photo.save(str(self.output / f"{repeat_index}.png"), "PNG", False)
        return photo


def test_completed_record_keeps_pre_action_source_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    Image.new("RGB", (4, 3), "red").save(source, format="PNG")
    original_hash = _sha256(source)
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    first = MutatingSourceAction(source, output)

    api.apply_actions_to_photos_with_recovery(
        [first], batch_settings(no_save=True, overwrite=True), recovery, [str(source)]
    )

    record = RecoveryJournal(recovery.journal_path).records()[-1]
    assert record["input"]["sha256"] == original_hash
    resumed = MutatingSourceAction(source, output)
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        batch_settings(no_save=True, overwrite=True),
        recovery,
        [str(source)],
    )
    assert resumed.calls == 1


def test_repeat_change_invalidates_execution_fingerprint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_real_execution(monkeypatch)
    source = tmp_path / "source.png"
    output = tmp_path / "outputs"
    output.mkdir()
    Image.new("RGB", (4, 3), "red").save(source, format="PNG")
    recovery = RecoveryConfiguration((tmp_path / "batch.jsonl").resolve())
    first_settings = batch_settings(no_save=True, overwrite=True)
    first_settings["repeat"] = 1

    api.apply_actions_to_photos_with_recovery(
        [RepeatOutputAction(output)],
        first_settings,
        recovery,
        [str(source)],
    )
    resumed = RepeatOutputAction(output)
    resumed_settings = batch_settings(no_save=True, overwrite=True)
    resumed_settings["repeat"] = 2
    api.apply_actions_to_photos_with_recovery(
        [resumed],
        resumed_settings,
        recovery,
        [str(source)],
    )

    assert resumed.calls == 2
    assert (output / "0.png").is_file()
    assert (output / "1.png").is_file()


@pytest.mark.parametrize("invalid", ["empty_outputs", "error_issue"])
def test_invalid_completed_records_are_not_resumable(
    tmp_path: Path, invalid: str
) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    session = RecoverySession(journal, "actions")
    reports = () if invalid == "empty_outputs" else (ReportFile(source, output),)
    issues = (
        ()
        if invalid == "empty_outputs"
        else (
            ExecutionIssue(
                IssueStage.ACTION_EXECUTION,
                IssueSeverity.ERROR,
                "incomplete metadata",
                source,
            ),
        )
    )
    session.record_completed(source, reports, issues)

    assert session.completed_reports(source) == RecoveryReevaluation(
        RecoveryReason.PREVIOUSLY_FAILED
    )


def test_persisted_invalid_completed_record_is_not_resumable(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    output = tmp_path / "output.png"
    source.write_bytes(b"source")
    output.write_bytes(b"output")
    journal = RecoveryJournal(tmp_path / "batch.jsonl")
    session = RecoverySession(journal, "actions")
    session.record_completed(source, (ReportFile(source, output),), ())
    raw = json.loads(journal.path.read_text())
    raw["outputs"] = []
    journal.path.write_text(json.dumps(raw) + "\n")

    assert session.completed_reports(source) == RecoveryReevaluation(
        RecoveryReason.PREVIOUSLY_FAILED
    )
