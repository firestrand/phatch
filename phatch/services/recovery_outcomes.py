from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from phatch.core.execution_types import OutputRecord, ReportFile, RollbackState
from phatch.services.output_publication import (
    PublicationResult,
    PublicationSucceeded,
    PublishedOutput,
)


@dataclass(frozen=True, slots=True)
class RecoveryFinishSucceeded:
    outputs: tuple[OutputRecord, ...]


@dataclass(frozen=True, slots=True)
class RecoveryFinishFailed:
    cause: OSError | KeyboardInterrupt
    outputs: tuple[OutputRecord, ...]
    rollback: RollbackState
    cleanup_errors: tuple[OSError | KeyboardInterrupt, ...] = ()


RecoveryFinishResult: TypeAlias = RecoveryFinishSucceeded | RecoveryFinishFailed


def recovery_finish_result(
    publication: PublicationResult,
    reports: tuple[ReportFile, ...],
) -> RecoveryFinishResult:
    if isinstance(publication, PublicationSucceeded):
        return RecoveryFinishSucceeded(_records(reports, publication.outputs))
    records = _records(reports, publication.outputs)
    rollback = (
        RollbackState.FAILED
        if publication.rollback_error is not None
        or any(record.survived for record in records)
        else RollbackState.COMPLETED
        if records
        else RollbackState.NOT_REQUIRED
    )
    return RecoveryFinishFailed(
        publication.cause, records, rollback, publication.cleanup_errors
    )


def _records(
    reports: tuple[ReportFile, ...],
    published: tuple[PublishedOutput, ...],
) -> tuple[OutputRecord, ...]:
    states = {output.identity.path.resolve(): output.survived for output in published}
    return tuple(
        OutputRecord(
            report,
            states[report.path.resolve()]
            if report.path.resolve() in states
            else _report_exists(report.path),
        )
        for report in reports
    )


def _report_exists(path: Path) -> bool:
    return path.is_file()
