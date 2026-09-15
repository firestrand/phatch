from __future__ import annotations

import os
from pathlib import Path

from phatch.core.execution_ports import Recovery, RecoveryAttempt
from phatch.core.execution_types import (
    CancellationState,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    RollbackState,
)
from phatch.services.execution_file_outcomes import output_records
from phatch.services.parallel_image_jobs import ImageJob


class ParallelRecoveryBoundary:
    __slots__ = ("_attempts", "_completed", "_results", "interrupted", "jobs")

    def __init__(self, jobs: tuple[ImageJob, ...]) -> None:
        self.jobs = jobs
        self._attempts: dict[int, RecoveryAttempt] = {}
        self._completed: set[int] = set()
        self._results: dict[int, FileResult] = {}
        self.interrupted = False

    def prepare(self, recovery: Recovery | None) -> tuple[ImageJob, ...]:
        if recovery is None:
            return self.jobs
        runnable: list[ImageJob] = []
        for position, job in enumerate(self.jobs):
            try:
                recovered = recovery.completed_reports(job.source)
                if isinstance(recovered, tuple):
                    self._results[position] = FileResult(
                        job.source,
                        FileOutcome.SKIPPED,
                        outputs=output_records(recovered, job.source),
                    )
                    continue
                self._attempts[position] = recovery.begin(job.source)
                runnable.append(job)
            except (OSError, KeyboardInterrupt) as error:
                self.record_boundary_failure(position, error)
                if isinstance(error, KeyboardInterrupt):
                    self.cancel_unresolved()
                    self.interrupted = True
                    break
        return tuple(runnable)

    def attempt(self, job: ImageJob) -> RecoveryAttempt | None:
        return self._attempts.get(self._position(job))

    def complete(self, job: ImageJob) -> None:
        self._completed.add(self._position(job))

    def set_result(self, job: ImageJob, result: FileResult) -> None:
        self._results[self._position(job)] = result

    def fail(self, job: ImageJob, issue: ExecutionIssue) -> None:
        position = self._position(job)
        attempt = self._attempts.get(position)
        recovery_issues: tuple[ExecutionIssue, ...] = ()
        if attempt is not None:
            try:
                attempt.fail((issue,))
                self._completed.add(position)
            except (OSError, KeyboardInterrupt) as error:
                recovery_issues = (self._issue(job.source, error),)
                if isinstance(error, KeyboardInterrupt):
                    self.cancel_after(position)
                    self.interrupted = True
        self._results[position] = FileResult(
            job.source,
            FileOutcome.FAILED,
            issues=(issue, *recovery_issues),
            cancellation=(
                CancellationState.REQUESTED
                if self.interrupted
                else CancellationState.NOT_REQUESTED
            ),
        )

    def record_boundary_failure(
        self,
        position: int,
        error: OSError | KeyboardInterrupt,
        *,
        outputs=(),
        rollback: RollbackState = RollbackState.NOT_REQUIRED,
    ) -> None:
        existing = self._results.get(position)
        if isinstance(error, KeyboardInterrupt) and existing is None:
            self._results[position] = FileResult(
                self.jobs[position].source,
                FileOutcome.CANCELLED,
                outputs=outputs,
                cancellation=CancellationState.REQUESTED,
                rollback=rollback,
            )
            return
        issue = self._issue(self.jobs[position].source, error)
        self._results[position] = FileResult(
            self.jobs[position].source,
            FileOutcome.FAILED,
            issues=(*(existing.issues if existing is not None else ()), issue),
            outputs=existing.outputs if existing is not None else outputs,
            cancellation=(
                CancellationState.REQUESTED
                if isinstance(error, KeyboardInterrupt)
                or (
                    existing is not None
                    and existing.cancellation is CancellationState.REQUESTED
                )
                else CancellationState.NOT_REQUESTED
            ),
            rollback=existing.rollback if existing is not None else rollback,
        )

    def cancel(self, job: ImageJob) -> None:
        position = self._position(job)
        self._results[position] = FileResult(
            job.source,
            FileOutcome.CANCELLED,
            cancellation=CancellationState.REQUESTED,
        )

    def cancel_after(self, position: int) -> None:
        for queued in range(position + 1, len(self.jobs)):
            if queued not in self._results:
                self.cancel(self.jobs[queued])

    def cancel_unresolved(self) -> None:
        for position, job in enumerate(self.jobs):
            if position not in self._results:
                self.cancel(job)

    def cleanup(self) -> None:
        for position, attempt in self._attempts.items():
            if position in self._completed:
                continue
            try:
                attempt.abort()
            except (OSError, KeyboardInterrupt) as error:
                self.record_boundary_failure(position, error)
        for position, job in enumerate(self.jobs):
            try:
                job.stage.unlink(missing_ok=True)
            except (OSError, KeyboardInterrupt) as error:
                self.record_boundary_failure(position, error)
                try:
                    os.unlink(job.stage)
                except (OSError, KeyboardInterrupt) as fallback_error:
                    self.record_boundary_failure(position, fallback_error)

    def result(self, elapsed_seconds: float) -> ExecutionResult:
        files = tuple(self._results[position] for position in range(len(self.jobs)))
        issues = tuple(issue for result in files for issue in result.issues)
        outcome = (
            ExecutionOutcome.CANCELLED
            if any(
                result.cancellation is CancellationState.REQUESTED for result in files
            )
            else ExecutionOutcome.COMPLETED
        )
        return ExecutionResult(
            outcome,
            tuple(job.source for job in self.jobs),
            files,
            issues,
            elapsed_seconds,
        )

    def _position(self, job: ImageJob) -> int:
        return self.jobs.index(job)

    @staticmethod
    def _issue(source: Path, error: OSError | KeyboardInterrupt) -> ExecutionIssue:
        return ExecutionIssue(
            IssueStage.RECOVERY,
            IssueSeverity.ERROR,
            str(error) if str(error) else "Execution interrupted during recovery.",
            source,
            "Save",
        )
