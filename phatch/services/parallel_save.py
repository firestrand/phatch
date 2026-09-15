from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path
from typing import assert_never

from phatch.core.execution_ports import Recovery
from phatch.core.execution_types import (
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ReportFile,
    RollbackState,
)
from phatch.services.action_schema import ActionDocument
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobCancelled,
    ImageJobFailure,
    ImageJobSuccess,
    execute_image_jobs,
)
from phatch.services.parallel_recovery_boundary import ParallelRecoveryBoundary
from phatch.services.parallel_save_publication import commit_image
from phatch.services.parallel_save_spec import structural_parallel_constraint
from phatch.services.recovery_outcomes import (
    RecoveryFinishFailed,
    RecoveryFinishSucceeded,
)

from .parallel_save_jobs import ImageJobConstruction as ImageJobConstruction
from .parallel_save_jobs import build_image_jobs as build_image_jobs


def parallel_constraint(document: ActionDocument) -> str | None:
    return structural_parallel_constraint(document)


def execute_parallel_save(
    jobs: tuple[ImageJob, ...],
    max_workers: int,
    recovery: Recovery | None = None,
) -> tuple[ExecutionResult, ImageJobBatchResult]:
    started = time.monotonic()
    sources = tuple(job.source for job in jobs)
    if len({job.destination.resolve() for job in jobs}) != len(jobs):
        issue = ExecutionIssue(
            IssueStage.ACTION_VALIDATION,
            IssueSeverity.ERROR,
            "Multiple image jobs resolve to the same output path.",
        )
        files = tuple(
            FileResult(job.source, FileOutcome.FAILED, issues=(issue,)) for job in jobs
        )
        return (
            ExecutionResult(
                ExecutionOutcome.FAILED,
                sources,
                files,
                (issue,),
                time.monotonic() - started,
            ),
            _empty_batch(max_workers),
        )
    boundary = ParallelRecoveryBoundary(jobs)
    runnable = boundary.prepare(recovery)
    if boundary.interrupted:
        batch = _empty_batch(max_workers)
    else:
        try:
            batch = execute_image_jobs(runnable, max_workers)
        except KeyboardInterrupt:
            batch = _empty_batch(max_workers)
            for job in runnable:
                boundary.cancel(job)
            boundary.interrupted = True
    if not boundary.interrupted:
        for result in batch.results:
            match result:
                case ImageJobSuccess() as success:
                    report = ReportFile(
                        success.source,
                        success.destination,
                        success.width,
                        success.height,
                        success.mode,
                    )
                    job = next(job for job in jobs if job.index == success.index)
                    try:
                        finish = commit_image(success, report, boundary.attempt(job))
                    except (OSError, KeyboardInterrupt) as error:
                        output = observed_output(success, report)
                        boundary.record_boundary_failure(
                            jobs.index(job),
                            error,
                            outputs=(output,),
                            rollback=(
                                RollbackState.FAILED
                                if output.survived
                                else RollbackState.COMPLETED
                            ),
                        )
                        if isinstance(error, KeyboardInterrupt):
                            boundary.cancel_after(jobs.index(job))
                            boundary.interrupted = True
                            break
                        continue
                    match finish:
                        case RecoveryFinishFailed() as failure:
                            errors = (failure.cause, *failure.cleanup_errors)
                            for error in errors:
                                boundary.record_boundary_failure(
                                    jobs.index(job),
                                    error,
                                    outputs=failure.outputs,
                                    rollback=failure.rollback,
                                )
                            interrupted = any(
                                isinstance(error, KeyboardInterrupt) for error in errors
                            )
                            if interrupted:
                                boundary.cancel_after(jobs.index(job))
                                boundary.interrupted = True
                                break
                            boundary.complete(job)
                        case RecoveryFinishSucceeded(outputs=outputs):
                            boundary.complete(job)
                            boundary.set_result(
                                job,
                                FileResult(
                                    success.source,
                                    FileOutcome.PROCESSED,
                                    outputs=outputs,
                                ),
                            )
                        case unreachable:
                            assert_never(unreachable)
                case ImageJobFailure() as failure:
                    job = next(job for job in jobs if job.index == failure.index)
                    boundary.fail(
                        job,
                        ExecutionIssue(
                            IssueStage.ACTION_EXECUTION,
                            IssueSeverity.ERROR,
                            failure.reason,
                            failure.source,
                            "Save",
                        ),
                    )
                    if boundary.interrupted:
                        break
                case ImageJobCancelled() as cancelled:
                    boundary.cancel(
                        next(job for job in jobs if job.index == cancelled.index)
                    )
                case unreachable:
                    assert_never(unreachable)
    boundary.cleanup()
    return boundary.result(time.monotonic() - started), batch


def _empty_batch(max_workers: int) -> ImageJobBatchResult:
    return ImageJobBatchResult((), (), os.getpid(), max_workers)


def observed_output(success: ImageJobSuccess, report: ReportFile) -> OutputRecord:
    survived = success.destination.is_file() and _digest(
        success.destination
    ) == _digest(success.stage)
    return OutputRecord(report, survived)


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
