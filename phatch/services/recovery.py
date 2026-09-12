from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from phatch.core.execution_types import (
    ExecutionIssue,
    RecoveryConfiguration,
    RecoveryReason,
    RecoveryReevaluation,
    ReportFile,
)
from phatch.services.output_rollback import (
    OriginalDestination,
    remove_backups,
    restore_originals,
)
from phatch.services.output_transaction import (
    DeferredOutputTransaction,
    OutputIdentity,
)
from phatch.services.recovery_journal import (
    FileIdentityData,
    JournalCorruptionError,
    JournalState,
    JournalWriteError,
    OutputIdentityData,
    RecoveryJournal,
    record_data,
)

__all__ = [
    "JournalCorruptionError",
    "JournalWriteError",
    "RecoveryJournal",
]

RecoveryConfig = RecoveryConfiguration


@dataclass(slots=True)
class RecoveryAttempt:
    session: RecoverySession
    input_identity: FileIdentityData
    transaction: DeferredOutputTransaction = field(
        default_factory=DeferredOutputTransaction
    )

    def finish(
        self,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> None:
        prepared = self.transaction.identities()
        if issues or (not prepared and not reports):
            self.transaction.discard()
            self.session._append(self.input_identity, [], JournalState.FAILED, issues)
            return
        outputs = [_identity_data(identity) for identity in prepared]
        prepared_paths = {identity["path"] for identity in outputs}
        outputs.extend(
            _output_identity(report.path)
            for report in reports
            if str(report.path.resolve()) not in prepared_paths
        )
        intent_written = False
        try:
            self.session._append(
                self.input_identity, outputs, JournalState.PREPARED, ()
            )
            intent_written = True
        finally:
            if not intent_written:
                self.transaction.discard()
        self.transaction.publish_all()
        self.session._append(self.input_identity, outputs, JournalState.COMPLETED, ())

    def fail(self, issues: tuple[ExecutionIssue, ...]) -> None:
        self.transaction.discard()
        self.session._append(self.input_identity, [], JournalState.FAILED, issues)

    def abort(self) -> None:
        self.transaction.discard()


@dataclass(frozen=True, slots=True)
class RecoverySession:
    journal: RecoveryJournal
    action_digest: str

    def completed_reports(
        self, source: Path
    ) -> tuple[ReportFile, ...] | RecoveryReevaluation | None:
        identity = file_identity(source)
        for record in reversed(self.journal.records()):
            if record["input"]["path"] != identity["path"]:
                continue
            if record["input"] != identity and not _source_matches_output(
                identity, record["outputs"]
            ):
                return RecoveryReevaluation(RecoveryReason.INPUT_CHANGED)
            if record["action_digest"] != self.action_digest:
                return RecoveryReevaluation(RecoveryReason.ACTIONS_CHANGED)
            state = JournalState(record["state"])
            if state is JournalState.FAILED:
                return RecoveryReevaluation(RecoveryReason.PREVIOUSLY_FAILED)
            if not record["outputs"] or record["issues"]:
                return RecoveryReevaluation(RecoveryReason.PREVIOUSLY_FAILED)
            outputs_match = all(_output_matches(output) for output in record["outputs"])
            if state is JournalState.PREPARED and not outputs_match:
                restore_originals(_recorded_originals(record["outputs"]))
                return RecoveryReevaluation(RecoveryReason.OUTPUT_CHANGED)
            if not outputs_match:
                return RecoveryReevaluation(RecoveryReason.OUTPUT_CHANGED)
            if state is JournalState.PREPARED:
                remove_backups(_recorded_originals(record["outputs"]))
                self.journal.append(
                    record_data(
                        record["input"],
                        record["action_digest"],
                        record["outputs"],
                        JournalState.COMPLETED,
                        [],
                    )
                )
            return tuple(
                ReportFile(source, Path(output["path"])) for output in record["outputs"]
            )
        return None

    def begin(self, source: Path) -> RecoveryAttempt:
        return RecoveryAttempt(self, file_identity(source))

    def record_completed(
        self,
        source: Path,
        reports: tuple[ReportFile, ...],
        issues: tuple[ExecutionIssue, ...],
    ) -> None:
        identity = file_identity(source)
        if not reports or issues:
            self._append(identity, [], JournalState.FAILED, issues)
            return
        outputs = [_output_identity(report.path) for report in reports]
        self._append(identity, outputs, JournalState.COMPLETED, ())

    def record_failed(self, source: Path, issues: tuple[ExecutionIssue, ...]) -> None:
        self._append(file_identity(source), [], JournalState.FAILED, issues)

    def _append(
        self,
        identity: FileIdentityData,
        outputs: list[OutputIdentityData],
        state: JournalState,
        issues: tuple[ExecutionIssue, ...],
    ) -> None:
        self.journal.append(
            record_data(
                identity,
                self.action_digest,
                outputs,
                state,
                [issue.message for issue in issues],
            )
        )


def file_identity(path: Path) -> FileIdentityData:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": _sha256(path),
    }


def action_list_digest(actions: tuple[dict[str, str | int], ...]) -> str:
    payload = json.dumps(actions, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def _identity_data(identity: OutputIdentity) -> OutputIdentityData:
    original = identity.original
    return {
        "path": str(identity.path.resolve()),
        "size": identity.size,
        "sha256": identity.sha256,
        "modified_ns": identity.modified_ns,
        "original_exists": original.existed if original is not None else None,
        "backup_path": (
            str(original.backup.resolve())
            if original is not None and original.backup is not None
            else None
        ),
    }


def _output_identity(path: Path) -> OutputIdentityData:
    return {
        "path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": _sha256(path),
        "modified_ns": path.stat().st_mtime_ns,
        "original_exists": None,
        "backup_path": None,
    }


def _recorded_originals(
    outputs: list[OutputIdentityData],
) -> tuple[OriginalDestination, ...]:
    originals: dict[Path, OriginalDestination] = {}
    for output in outputs:
        existed = output["original_exists"]
        if existed is None:
            continue
        destination = Path(output["path"])
        backup_path = output["backup_path"]
        originals[destination] = OriginalDestination(
            destination,
            existed,
            Path(backup_path) if backup_path is not None else None,
        )
    return tuple(originals.values())


def _output_matches(identity: OutputIdentityData) -> bool:
    path = Path(identity["path"])
    return (
        path.is_file()
        and path.stat().st_size == identity["size"]
        and path.stat().st_mtime_ns == identity["modified_ns"]
        and _sha256(path) == identity["sha256"]
    )


def _source_matches_output(
    source: FileIdentityData, outputs: list[OutputIdentityData]
) -> bool:
    return any(
        output["path"] == source["path"]
        and output["size"] == source["size"]
        and output["modified_ns"] == source["modified_ns"]
        and output["sha256"] == source["sha256"]
        for output in outputs
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
