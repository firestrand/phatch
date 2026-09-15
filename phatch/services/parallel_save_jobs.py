from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from phatch.core.execution_types import (
    ExecutionIssue,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
)
from phatch.lib.image_codecs import codec_capabilities, codec_for_extension
from phatch.services.parallel_image_jobs import ImageJob, source_frame_pixel_counts
from phatch.services.parallel_save_spec import SaveJobSpec
from phatch.services.preflight import PreflightResult


@dataclass(frozen=True, slots=True)
class ImageJobConstruction:
    planned_sources: tuple[Path, ...]
    jobs: tuple[ImageJob, ...]
    failures: tuple[FileResult, ...]

    def reconcile(self, result: ExecutionResult) -> ExecutionResult:
        files_by_source = {
            file.source: file for file in (*result.files, *self.failures)
        }
        files = tuple(files_by_source[source] for source in self.planned_sources)
        failure_issues = tuple(
            issue for failure in self.failures for issue in failure.issues
        )
        return ExecutionResult(
            result.outcome,
            self.planned_sources,
            files,
            (*result.issues, *failure_issues),
            result.elapsed_seconds,
        )


def build_image_jobs(
    spec: SaveJobSpec,
    preflight: PreflightResult,
) -> ImageJobConstruction:
    capabilities = codec_capabilities()
    jobs: list[ImageJob] = []
    failures: list[FileResult] = []
    for index, (source, destination) in enumerate(
        zip(preflight.inputs, preflight.outputs, strict=True)
    ):
        codec = codec_for_extension(destination.suffix, capabilities)
        if codec is None or not codec.can_write:
            issue = ExecutionIssue(
                IssueStage.ACTION_VALIDATION,
                IssueSeverity.ERROR,
                "Output codec for extension "
                f"'{destination.suffix}' is unavailable or cannot write.",
                source,
                "Save",
            )
            failures.append(FileResult(source, FileOutcome.FAILED, issues=(issue,)))
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
        jobs.append(
            ImageJob(
                index,
                source,
                destination,
                stage,
                codec.format_name,
                frame_pixel_counts[0],
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
    return ImageJobConstruction(preflight.inputs, tuple(jobs), tuple(failures))
