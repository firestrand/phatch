from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Final

from PIL import Image, UnidentifiedImageError

from phatch.lib import metadata, safe
from phatch.services.preview_types import (
    PreviewAdmissionError,
    PreviewErrorCode,
    PreviewLimits,
    PreviewRequest,
    PreviewSize,
    PreviewSource,
)

_SOURCE_VARIABLES: Final = (
    "compression",
    "day",
    "desktop",
    "dpi",
    "filename",
    "filesize",
    "folder",
    "folderindex",
    "foldername",
    "format",
    "height",
    "hour",
    "index",
    "minute",
    "mode",
    "month",
    "monthname",
    "orientation",
    "path",
    "root",
    "second",
    "size",
    "subfolder",
    "transparency",
    "type",
    "weekday",
    "weekdayname",
    "width",
    "year",
)
_METADATA_PREFIXES: Final = ("Exif_", "File_", "Iptc_", "Pexif_", "Pil_", "Zexif_")


def validate_preview_transition(
    before: PreviewSize,
    after: PreviewSize,
    max_live_bytes: int | None = None,
) -> int:
    limits = PreviewLimits(
        max_live_bytes=max_live_bytes
        if max_live_bytes is not None
        else PreviewLimits().max_live_bytes
    )
    for size in (before, after):
        if size.width <= 0 or size.height <= 0 or size.pixels > limits.max_pixels:
            raise PreviewAdmissionError(
                PreviewErrorCode.PIXEL_LIMIT,
                f"image exceeds {limits.max_pixels} pixel limit",
            )
    estimated = 4 * before.pixels + 4 * after.pixels + limits.frame_overhead_bytes
    if estimated > limits.max_live_bytes:
        raise PreviewAdmissionError(
            PreviewErrorCode.MEMORY_LIMIT,
            f"estimated live buffers exceed {limits.max_live_bytes} byte limit",
        )
    return estimated


def inspect_preview_source(path: Path) -> PreviewSource:
    try:
        canonical = path.resolve(strict=True)
        with Image.open(canonical) as image:
            size = PreviewSize(*image.size)
            mode = image.mode
            format_name = image.format
        validate_preview_transition(size, size)
        with Image.open(canonical) as image:
            image.verify()
        digest = sha256()
        with canonical.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        file_info = metadata.InfoExtract(
            str(canonical), vars=list(metadata.InfoFile.possible_vars)
        ).dump()
    except PreviewAdmissionError:
        raise
    except (OSError, UnidentifiedImageError, SyntaxError, ValueError) as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.CORRUPT_SOURCE, f"source image is unreadable: {path}"
        ) from error
    logical_file_info = tuple(sorted(file_info.items()))
    return PreviewSource(
        canonical,
        digest.hexdigest(),
        size,
        mode,
        format_name,
        logical_file_info,
    )


def validate_preview_expressions(
    request: PreviewRequest, source: PreviewSource
) -> tuple[str, ...]:
    required: list[str] = list(_SOURCE_VARIABLES)
    for spec in request.document.actions:
        for field in spec.fields:
            discovered: list[str] = []
            safe.extend_vars(discovered, field.value)
            for name in discovered:
                if (
                    name not in safe.SAFE["all"]
                    and name not in required
                    and not metadata.InfoTest.provides(name)
                    and not name.startswith(_METADATA_PREFIXES)
                ):
                    raise PreviewAdmissionError(
                        PreviewErrorCode.UNSAFE_EXPRESSION,
                        f"expression name is unavailable: {name}",
                        spec.action_id,
                        field.field_id,
                    )
                if name not in safe.SAFE["all"] and name not in required:
                    required.append(name)
            try:
                safe.assert_safe_expr(
                    field.value,
                    _locals=dict.fromkeys(required, 1),
                    validate=lambda names, globals_, locals_: [
                        name
                        for name in names
                        if name not in globals_
                        and name not in locals_
                        and name not in safe.SAFE["all"]
                    ],
                    preprocess=safe.format_expr,
                )
            except (SyntaxError, TypeError, ValueError, safe.UnsafeError) as error:
                raise PreviewAdmissionError(
                    PreviewErrorCode.UNSAFE_EXPRESSION,
                    "field contains an unsafe expression",
                    spec.action_id,
                    field.field_id,
                ) from error
    return tuple(required)
