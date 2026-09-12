from __future__ import annotations

import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import assert_never

from PIL import Image

from phatch.core.execution_ports import Recovery, RecoveryAttempt
from phatch.core.execution_types import (
    ExecutionDecision,
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileResult,
    IssueSeverity,
    IssueStage,
    ReportFile,
)
from phatch.lib.image_codecs import codec_capabilities, codec_for_extension
from phatch.services.action_schema import ActionDocument
from phatch.services.output_transaction import (
    AtomicOutputTransaction,
    NoMetadataProvider,
    OutputRequest,
    PillowValidator,
)
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobFailure,
    ImageJobSuccess,
    execute_image_jobs,
    source_frame_pixel_counts,
)
from phatch.services.parallel_save_spec import (
    SaveJobSpec,
    structural_parallel_constraint,
)
from phatch.services.preflight import PreflightResult


@dataclass(frozen=True, slots=True)
class CopyPreparedImage:
    source: Path

    def __call__(self, destination: Path) -> None:
        shutil.copyfile(self.source, destination)


def parallel_constraint(document: ActionDocument) -> str | None:
    return structural_parallel_constraint(document)


def build_image_jobs(
    spec: SaveJobSpec,
    preflight: PreflightResult,
) -> tuple[ImageJob, ...]:
    capabilities = codec_capabilities()
    jobs: list[ImageJob] = []
    for index, (source, destination) in enumerate(
        zip(preflight.inputs, preflight.outputs, strict=True)
    ):
        codec = codec_for_extension(destination.suffix, capabilities)
        if codec is None or not codec.can_write:
            continue
        descriptor, stage_name = tempfile.mkstemp(
            prefix=f".{destination.name}.worker-",
            suffix=destination.suffix,
        )
        os.close(descriptor)
        stage = Path(stage_name)
        stage.unlink()
        with Image.open(source) as image:
            frame_count = int(getattr(image, "n_frames", 1))
            retains_animation = frame_count > 1 and codec.format_name in Image.SAVE_ALL
            frame_pixel_counts = source_frame_pixel_counts(image, retains_animation)
        pixel_count = frame_pixel_counts[0]
        jobs.append(
            ImageJob(
                index,
                source,
                destination,
                stage,
                codec.format_name,
                pixel_count,
                spec.jpeg_quality if codec.format_name == "JPEG" else None,
                spec.png_optimize if codec.format_name == "PNG" else False,
                spec.tiff_compression,
                frame_count=frame_count,
                frame_pixel_counts=frame_pixel_counts,
                retains_animation=retains_animation,
                resolution=spec.resolution,
                preserve_metadata=spec.preserve_metadata,
            )
        )
    return tuple(jobs)


def execute_parallel_save(
    jobs: tuple[ImageJob, ...],
    max_workers: int,
    recovery: Recovery | None = None,
) -> tuple[ExecutionResult, ImageJobBatchResult]:
    started = time.monotonic()
    if len({job.destination.resolve() for job in jobs}) != len(jobs):
        issue = ExecutionIssue(
            IssueStage.ACTION_VALIDATION,
            IssueSeverity.ERROR,
            "Multiple image jobs resolve to the same output path.",
        )
        return ExecutionResult(
            ExecutionOutcome.FAILED, issues=(issue,)
        ), ImageJobBatchResult((), (), os.getpid(), max_workers)
    attempts = tuple(
        recovery.begin(job.source) if recovery is not None else None for job in jobs
    )
    completed_attempts: set[int] = set()
    try:
        batch = execute_image_jobs(jobs, max_workers)
        files: list[FileResult] = []
        issues: list[ExecutionIssue] = []
        for index, (result, attempt) in enumerate(
            zip(batch.results, attempts, strict=True)
        ):
            match result:
                case ImageJobSuccess() as success:
                    report = ReportFile(
                        success.source,
                        success.destination,
                        success.width,
                        success.height,
                        success.mode,
                    )
                    try:
                        _commit(success, report, attempt)
                    except OSError as error:
                        issue = ExecutionIssue(
                            IssueStage.ACTION_EXECUTION,
                            IssueSeverity.ERROR,
                            str(error),
                            success.source,
                            "Save",
                        )
                        if attempt is not None:
                            attempt.fail((issue,))
                            completed_attempts.add(index)
                        issues.append(issue)
                        files.append(FileResult(success.source, ExecutionDecision.SKIP))
                    else:
                        if attempt is not None:
                            completed_attempts.add(index)
                        files.append(
                            FileResult(
                                success.source,
                                ExecutionDecision.CONTINUE,
                                (report,),
                            )
                        )
                case ImageJobFailure() as failure:
                    issue = ExecutionIssue(
                        IssueStage.ACTION_EXECUTION,
                        IssueSeverity.ERROR,
                        failure.reason,
                        failure.source,
                        "Save",
                    )
                    if attempt is not None:
                        attempt.fail((issue,))
                        completed_attempts.add(index)
                    issues.append(issue)
                    files.append(FileResult(failure.source, ExecutionDecision.SKIP))
                case unreachable:
                    assert_never(unreachable)
        return (
            ExecutionResult(
                ExecutionOutcome.COMPLETED,
                tuple(files),
                tuple(issues),
                time.monotonic() - started,
            ),
            batch,
        )
    finally:
        for index, attempt in enumerate(attempts):
            if attempt is not None and index not in completed_attempts:
                attempt.abort()
        for job in jobs:
            job.stage.unlink(missing_ok=True)


def _commit(
    success: ImageJobSuccess,
    report: ReportFile,
    attempt: RecoveryAttempt | None,
) -> None:
    success.destination.parent.mkdir(parents=True, exist_ok=True)
    transaction = (
        attempt.transaction if attempt is not None else AtomicOutputTransaction()
    )
    transaction.execute(
        OutputRequest(
            success.destination,
            CopyPreparedImage(success.stage),
            NoMetadataProvider(),
            PillowValidator(
                success.format_name,
                (success.width, success.height),
            ),
        )
    )
    if attempt is not None:
        attempt.finish((report,), ())
