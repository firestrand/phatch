from __future__ import annotations

import re
from dataclasses import dataclass

from phatch.lib.image_codecs import codec_capabilities, codec_for_extension
from phatch.services.action_schema import ActionDocument, ActionSpec
from phatch.services.preflight import PreflightResult

_VARIABLE = re.compile(r"<([^>]+)>")
_PARALLEL_VARIABLES = frozenset({"filename", "folder", "subfolder", "type"})
_ZERO_FILE_SIZES = frozenset({"0", "0b", "0kb", "0mb"})


@dataclass(frozen=True, slots=True)
class ParallelSaveSettings:
    max_workers: int
    overwrite_existing: bool
    resume: bool
    no_save: bool
    repeat: int


@dataclass(frozen=True, slots=True)
class SaveJobSpec:
    jpeg_quality: int
    png_optimize: bool
    tiff_compression: str
    resolution: int
    preserve_metadata: bool


@dataclass(frozen=True, slots=True)
class ParallelSaveUnsupported:
    reason: str


def select_parallel_save(
    document: ActionDocument,
    preflight: PreflightResult,
    settings: ParallelSaveSettings,
) -> SaveJobSpec | ParallelSaveUnsupported:
    constraint = structural_parallel_constraint(document)
    if constraint is not None:
        return ParallelSaveUnsupported(constraint)
    if not settings.overwrite_existing:
        return ParallelSaveUnsupported("--keep requires the legacy serial Save path")
    if settings.resume:
        return ParallelSaveUnsupported("--resume requires the legacy serial Save path")
    if settings.no_save:
        return ParallelSaveUnsupported("--no-save requires the legacy serial Save path")
    if settings.repeat != 1:
        return ParallelSaveUnsupported("repeated execution requires the serial path")

    save_action = next(
        action
        for action in document.actions
        if _enabled(action) and action.action_id == "save"
    )
    fields = {field.field_id: field.value for field in save_action.fields}
    if _boolean_field(fields.get("metadata", "yes")):
        return ParallelSaveUnsupported(
            "Save Metadata=yes requires the legacy serial Save path"
        )
    resolution_value = fields.get("resolution", "<dpi>")
    try:
        resolution = int(resolution_value)
    except ValueError:
        return ParallelSaveUnsupported(
            "dynamic Save Resolution requires the legacy serial Save path"
        )

    capabilities = codec_capabilities()
    formats = {
        codec.format_name
        for output in preflight.outputs
        if (codec := codec_for_extension(output.suffix, capabilities)) is not None
    }
    maximum = fields.get("jpeg_size_maximum", "0 kb")
    if "JPEG" in formats and _normalized_size(maximum) not in _ZERO_FILE_SIZES:
        return ParallelSaveUnsupported(
            "JPEG Size Maximum requires the legacy serial Save path"
        )
    compression = fields.get("tiff_compression", "<compression>")
    if "TIFF" in formats and compression.casefold() not in {"none", "raw"}:
        return ParallelSaveUnsupported(
            "TIFF compression requires the legacy serial Save path"
        )
    return SaveJobSpec(
        jpeg_quality=int(fields.get("jpeg_quality", "85")),
        png_optimize=_boolean_field(fields.get("png_optimize", "no")),
        tiff_compression=compression,
        resolution=resolution,
        preserve_metadata=False,
    )


def structural_parallel_constraint(document: ActionDocument) -> str | None:
    enabled = tuple(action for action in document.actions if _enabled(action))
    if len(enabled) != 1 or enabled[0].action_id != "save":
        return "parallel execution requires exactly one enabled Save action"
    variables = {
        match.group(1)
        for field in enabled[0].fields
        for match in _VARIABLE.finditer(field.value)
    }
    unsupported = variables.difference(_PARALLEL_VARIABLES)
    if unsupported:
        return "parallel Save does not support dynamic variables: " + ", ".join(
            sorted(unsupported)
        )
    return None


def _enabled(action: ActionSpec) -> bool:
    fields = {field.field_id: field.value for field in action.fields}
    return not _boolean_field(fields.get("enabled", "yes"), false_values=True)


def _boolean_field(value: str, *, false_values: bool = False) -> bool:
    normalized = value.strip().casefold()
    if false_values:
        return normalized in {"0", "false", "no", "off"}
    return normalized in {"1", "true", "yes", "on"}


def _normalized_size(value: str) -> str:
    return value.replace(" ", "").casefold()
