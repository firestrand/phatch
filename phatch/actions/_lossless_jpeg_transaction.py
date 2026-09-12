from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from phatch.lib.process import Command, ProcessRunner


@dataclass(frozen=True, slots=True)
class LosslessJpegRequest:
    source: Path
    destination: Path
    preserve_timestamp: bool


@dataclass(frozen=True, slots=True)
class LosslessProcessPaths:
    source: Path
    output: Path


@dataclass(frozen=True, slots=True)
class InvalidJpegOutputError(OSError):
    path: Path
    actual_format: str | None

    def __str__(self) -> str:
        return f"external JPEG tool produced {self.actual_format or 'unknown'} data"


CommandBuilder = Callable[[LosslessProcessPaths], Command]


def _copy_to_final_staging(source: Path, destination: Path) -> Path:
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as target, source.open("rb") as output:
            shutil.copyfileobj(output, target)
            target.flush()
            os.fsync(target.fileno())
    except OSError:
        staged.unlink(missing_ok=True)
        raise
    return staged


def run_lossless_jpeg(
    request: LosslessJpegRequest,
    runner: ProcessRunner,
    command_builder: CommandBuilder,
) -> None:
    source_stat = request.source.stat()
    staged_final: Path | None = None
    try:
        with tempfile.TemporaryDirectory(
            prefix="phatch-lossless-jpeg-", dir=request.destination.parent
        ) as directory:
            private = Path(directory)
            paths = LosslessProcessPaths(private / "source.jpg", private / "output.jpg")
            shutil.copy2(request.source, paths.source)
            runner.run(command_builder(paths))
            with Image.open(paths.output) as output:
                if output.format != "JPEG":
                    raise InvalidJpegOutputError(paths.output, output.format)
                output.load()
            staged_final = _copy_to_final_staging(paths.output, request.destination)
            if request.preserve_timestamp:
                os.utime(
                    staged_final,
                    ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
                )
        os.replace(staged_final, request.destination)
        staged_final = None
    finally:
        if staged_final is not None and staged_final.exists():
            staged_final.unlink()
