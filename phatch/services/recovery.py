from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from phatch.core.execution_types import (
    ExecutionIssue,
    RecoveryConfiguration,
    RecoveryReason,
    RecoveryReevaluation,
    ReportFile,
    RollbackState,
)
from phatch.services.output_publication import (
    OutputIdentity,
    PublicationFailed,
    publication_outputs,
)
from phatch.services.output_rollback import (
    OriginalDestination,
    remove_backups,
    restore_originals,
)
from phatch.services.output_transaction import (
    DeferredOutputTransaction,
)
from phatch.services.recovery_identity import (
    action_list_digest as action_list_digest,
)
from phatch.services.recovery_identity import (
    file_identity as file_identity,
)
from phatch.services.recovery_identity import (
    identity_data as _identity_data,
)
from phatch.services.recovery_identity import (
    output_identity as _output_identity,
)
from phatch.services.recovery_identity import (
    output_matches as _output_matches,
)
from phatch.services.recovery_identity import (
    source_matches_output as _source_matches_output,
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
from phatch.services.recovery_outcomes import (
    RecoveryFinishFailed,
    RecoveryFinishResult,
    RecoveryFinishSucceeded,
    recovery_finish_result,
)

__all__ = [
    "JournalCorruptionError",
    "JournalWriteError",
    "RecoveryJournal",
]

RecoveryConfig = RecoveryConfiguration


@dataclass(frozen=True, slots=True)
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
    ) -> RecoveryFinishResult:
        prepared = self.transaction.identities()
        if issues or (not prepared and not reports):
            self.transaction.discard()
            self.session._append(self.input_identity, [], JournalState.FAILED, issues)
            return RecoveryFinishSucceeded(())
        reports = _prepared_reports(self.input_identity, prepared, reports)
        outputs = [_identity_data(identity) for identity in prepared]
        prepared_paths = {identity["path"] for identity in outputs}
        outputs.extend(
            _output_identity(report.path)
            for report in reports
            if str(report.path.resolve()) not in prepared_paths
        )
        try:
            self.session._append(
                self.input_identity, outputs, JournalState.PREPARED, ()
            )
        except (OSError, KeyboardInterrupt) as error:
            cleanup_errors: tuple[OSError | KeyboardInterrupt, ...] = ()
            try:
                self.transaction.discard()
            except (OSError, KeyboardInterrupt) as cleanup_error:
                cleanup_errors = (cleanup_error,)
            return recovery_finish_result(
                PublicationFailed(
                    error,
                    publication_outputs(prepared),
                    None,
                    cleanup_errors,
                ),
                reports,
            )
        publication = self.transaction.publish_all()
        result = recovery_finish_result(publication, reports)
        if isinstance(result, RecoveryFinishFailed):
            return result
        try:
            self.session._append(
                self.input_identity, outputs, JournalState.COMPLETED, ()
            )
        except (OSError, KeyboardInterrupt) as error:
            return RecoveryFinishFailed(
                error, result.outputs, RollbackState.NOT_REQUIRED
            )
        return result

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


def _prepared_reports(
    source: FileIdentityData,
    prepared: tuple[OutputIdentity, ...],
    reports: tuple[ReportFile, ...],
) -> tuple[ReportFile, ...]:
    known_paths = {report.path.resolve() for report in reports}
    return (
        *reports,
        *(
            ReportFile(Path(source["path"]), identity.path)
            for identity in prepared
            if identity.path.resolve() not in known_paths
        ),
    )


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
