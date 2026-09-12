from __future__ import annotations

import os
from dataclasses import dataclass
from operator import methodcaller
from pathlib import Path
from typing import TypeAlias

from PIL import Image, ImageOps, UnidentifiedImageError

from phatch.lib.image_codecs import register_optional_heif

DEFAULT_MAX_PIXELS = 64_000_000
DEFAULT_MEMORY_BUDGET_BYTES = 512 * 1024 * 1024
ESTIMATED_BYTES_PER_PIXEL = 8
ESTIMATED_FRAME_OVERHEAD_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class ImageJob:
    index: int
    source: Path
    destination: Path
    stage: Path
    format_name: str
    pixel_count: int
    quality: int | None = None
    optimize: bool = False
    compression: str = "none"
    max_pixels: int = DEFAULT_MAX_PIXELS
    frame_count: int = 1
    frame_pixel_counts: tuple[int, ...] = ()
    retains_animation: bool = False
    resolution: int = 72
    preserve_metadata: bool = False
    memory_budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES

    @property
    def estimated_memory_bytes(self) -> int:
        frame_pixels = self.frame_pixel_counts or (self.pixel_count,) * self.frame_count
        decoded_pixels = (
            sum(frame_pixels) if self.retains_animation else frame_pixels[0]
        )
        return decoded_pixels * ESTIMATED_BYTES_PER_PIXEL + (
            self.frame_count * ESTIMATED_FRAME_OVERHEAD_BYTES
        )


@dataclass(frozen=True, slots=True)
class ImageJobSuccess:
    index: int
    source: Path
    destination: Path
    stage: Path
    width: int
    height: int
    mode: str
    format_name: str
    worker_pid: int


@dataclass(frozen=True, slots=True)
class ImageJobFailure:
    index: int
    source: Path
    destination: Path
    stage: Path
    reason: str
    worker_pid: int


ImageJobResult: TypeAlias = ImageJobSuccess | ImageJobFailure
ImageSaveOption: TypeAlias = (
    bool | int | str | bytes | tuple[int, int] | list[Image.Image] | list[int]
)


@dataclass(frozen=True, slots=True)
class ImageJobBatchResult:
    results: tuple[ImageJobResult, ...]
    worker_pids: tuple[int, ...]
    coordinator_pid: int
    max_workers: int


def execute_image_jobs(
    jobs: tuple[ImageJob, ...],
    max_workers: int,
    memory_budget_bytes: int = DEFAULT_MEMORY_BUDGET_BYTES,
) -> ImageJobBatchResult:
    from phatch.services.parallel_image_pool import execute_process_image_jobs

    return execute_process_image_jobs(jobs, max_workers, memory_budget_bytes)


def _execute_image_job(job: ImageJob) -> ImageJobResult:
    worker_pid = os.getpid()
    if job.pixel_count > job.max_pixels:
        return ImageJobFailure(
            job.index,
            job.source,
            job.destination,
            job.stage,
            f"image exceeds {job.max_pixels} pixel limit",
            worker_pid,
        )
    try:
        with Image.open(job.source) as source:
            frame_count = int(getattr(source, "n_frames", 1))
            frame_pixels = source_frame_pixel_counts(source, job.retains_animation)
            if max(frame_pixels) > job.max_pixels:
                return ImageJobFailure(
                    job.index,
                    job.source,
                    job.destination,
                    job.stage,
                    f"image exceeds {job.max_pixels} pixel limit",
                    worker_pid,
                )
            decoded_pixels = (
                sum(frame_pixels) if job.retains_animation else frame_pixels[0]
            )
            estimated_memory = (
                decoded_pixels * ESTIMATED_BYTES_PER_PIXEL
                + frame_count * ESTIMATED_FRAME_OVERHEAD_BYTES
            )
            if estimated_memory > job.memory_budget_bytes:
                return ImageJobFailure(
                    job.index,
                    job.source,
                    job.destination,
                    job.stage,
                    "decoded memory exceeds memory budget of "
                    f"{job.memory_budget_bytes} bytes",
                    worker_pid,
                )
            options = _save_options(source, job)
            frames = [_frame_for_job(source, job)]
            try:
                if job.retains_animation:
                    for frame_index in range(1, int(getattr(source, "n_frames", 1))):
                        source.seek(frame_index)
                        frames.append(_frame_for_job(source, job))
                    options["save_all"] = True
                    options["append_images"] = frames[1:]
                    options["duration"] = [
                        int(frame.info.get("duration", 0)) for frame in frames
                    ]
                first = frames[0]
                save = methodcaller(
                    "save", job.stage, format=job.format_name, **options
                )
                save(first)
                with Image.open(job.stage) as encoded:
                    encoded_mode = encoded.mode
                return ImageJobSuccess(
                    job.index,
                    job.source,
                    job.destination,
                    job.stage,
                    first.width,
                    first.height,
                    encoded_mode,
                    job.format_name,
                    worker_pid,
                )
            finally:
                for frame in frames:
                    frame.close()
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError) as error:
        job.stage.unlink(missing_ok=True)
        return ImageJobFailure(
            job.index,
            job.source,
            job.destination,
            job.stage,
            str(error),
            worker_pid,
        )


def source_frame_pixel_counts(
    source: Image.Image, retains_animation: bool
) -> tuple[int, ...]:
    if not retains_animation:
        return (source.width * source.height,)
    frame_count = int(getattr(source, "n_frames", 1))
    pixels: list[int] = []
    for frame_index in range(frame_count):
        source.seek(frame_index)
        pixels.append(source.width * source.height)
    source.seek(0)
    return tuple(pixels)


def _frame_for_format(image: Image.Image, format_name: str) -> Image.Image:
    if format_name == "JPEG" and image.mode not in ("L", "RGB", "CMYK"):
        return image.convert("RGB")
    if format_name == "GIF" and image.mode != "P":
        return image.convert("P", palette=Image.Palette.ADAPTIVE)
    return image


def _frame_for_job(image: Image.Image, job: ImageJob) -> Image.Image:
    prepared = image.copy() if job.preserve_metadata else ImageOps.exif_transpose(image)
    if not job.preserve_metadata:
        prepared.info.pop("icc_profile", None)
        prepared.info.pop("exif", None)
    return _frame_for_format(prepared, job.format_name)


def _save_options(source: Image.Image, job: ImageJob) -> dict[str, ImageSaveOption]:
    options: dict[str, ImageSaveOption] = {"dpi": (job.resolution, job.resolution)}
    if job.quality is not None and job.format_name in {
        "AVIF",
        "HEIF",
        "JPEG",
        "WEBP",
    }:
        options["quality"] = job.quality
    if job.format_name == "PNG" and job.optimize:
        options["optimize"] = True
    if job.format_name == "TIFF" and job.compression not in {"none", "raw"}:
        options["compression"] = job.compression
    metadata_keys = ("icc_profile", "exif") if job.preserve_metadata else ()
    for key in (*metadata_keys, "transparency", "loop", "duration"):
        if key in source.info:
            options[key] = source.info[key]
    return options


def _initialize_worker(registry: Path | None) -> None:
    register_optional_heif()
    Image.init()
    if registry is not None:
        (registry / str(os.getpid())).touch()
