from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from phatch.core.execution_types import DiscoveredFile
from phatch.core.pil import IMAGE_READ_EXTENSIONS
from phatch.lib.capabilities import Capability
from phatch.lib.image_codecs import codec_capability
from phatch.services.action_schema import (
    ActionDocument,
    ActionSchemaCatalog,
    ActionSpec,
    validate_document_fields,
)
from phatch.services.file_discovery import (
    FileDiscovery,
    InvalidDiscoveryPathError,
    LocalDiscoveryFileSystem,
)

_ACTION_CAPABILITIES: Final = {
    "imagemagick": ("imagemagick-6",),
    "blender": ("blender-2.45-2.49",),
    "save_tags": ("legacy-metadata",),
}
_OUTPUT_ACTIONS: Final = frozenset(
    {"save", "copy", "rename", "save_tags", "lossless_jpeg"}
)
_IMAGE_EXTENSIONS: Final = tuple(IMAGE_READ_EXTENSIONS)


@dataclass(frozen=True, slots=True)
class PreflightRequest:
    document: ActionDocument
    paths: tuple[Path, ...]
    capabilities: tuple[Capability, ...]
    recursive: bool = False
    catalog: ActionSchemaCatalog | None = None


@dataclass(frozen=True, slots=True)
class PreflightResult:
    inputs: tuple[Path, ...]
    outputs: tuple[Path, ...]
    conflicts: tuple[Path, ...]
    unavailable_capabilities: tuple[Capability, ...]
    unsafe_operations: tuple[str, ...]
    invalid_fields: tuple[str, ...]
    estimated_work: int


class PreflightValidationError(ValueError):
    pass


class PreflightService:
    __slots__ = ()

    def build(self, request: PreflightRequest) -> PreflightResult:
        discovered = _discover(request.paths, request.recursive)
        inputs = tuple(item.path for item in discovered)
        actions = tuple(
            action for action in request.document.actions if _is_enabled(action)
        )
        outputs = tuple(
            _planned_output(source, action)
            for source in discovered
            for action in actions
            if action.action_id in _OUTPUT_ACTIONS
        )
        required = {
            identifier
            for action in actions
            for identifier in _required_capabilities(action)
        }
        unavailable = tuple(
            capability
            for capability in request.capabilities
            if str(capability.identifier) in required and not capability.available
        )
        unavailable_codecs = tuple(
            capability
            for capability in (
                codec_capability(output.suffix)
                for source in discovered
                for action in actions
                if action.action_id == "save"
                for output in (_planned_output(source, action),)
            )
            if not capability.available
        )
        unsafe = tuple(
            operation
            for operation in (_unsafe_operation(action) for action in actions)
            if operation is not None
        )
        duplicate_outputs = {path for path in outputs if outputs.count(path) > 1}
        invalid_fields = (
            ()
            if request.catalog is None
            else validate_document_fields(request.document, request.catalog)
        )
        return PreflightResult(
            inputs,
            outputs,
            tuple(
                path for path in outputs if path.exists() or path in duplicate_outputs
            ),
            tuple(dict.fromkeys((*unavailable, *unavailable_codecs))),
            unsafe,
            invalid_fields,
            len(inputs) * len(actions),
        )


def _discover(paths: tuple[Path, ...], recursive: bool) -> tuple[DiscoveredFile, ...]:
    discovery = FileDiscovery(LocalDiscoveryFileSystem())
    try:
        discovered = tuple(
            discovery.discover(
                tuple(str(path) for path in paths),
                _IMAGE_EXTENSIONS,
                recursive=recursive,
            )
        )
    except InvalidDiscoveryPathError as error:
        raise PreflightValidationError(str(error)) from error
    if not discovered:
        raise PreflightValidationError("No input images were found.")
    return discovered


def _planned_output(source_file: DiscoveredFile, action: ActionSpec) -> Path:
    source = source_file.path
    fields = {field.field_id: field.value for field in action.fields}
    folder_value = fields.get("in", str(Path.home() / "phatch"))
    folder_value = folder_value.replace("<folder>", str(source.parent))
    subfolder = ""
    if source_file.source_root is not None:
        relative_parent = source.parent.relative_to(source_file.source_root)
        subfolder = "" if relative_parent == Path(".") else str(relative_parent)
    folder_value = folder_value.replace("<subfolder>", subfolder)
    filename_value = fields.get("file_name", "<filename>")
    type_value = fields.get("as", source.suffix.lstrip("."))
    filename = filename_value.replace("<filename>", source.stem)
    suffix = type_value.replace("<type>", source.suffix.lstrip("."))
    if suffix and not suffix.startswith("."):
        suffix = f".{suffix}"
    if Path(filename).suffix.casefold() != suffix.casefold():
        filename = f"{filename}{suffix}"
    return (Path(folder_value) / filename).resolve()


def _is_enabled(action: ActionSpec) -> bool:
    fields = {field.field_id: field.value for field in action.fields}
    return fields.get("enabled", "yes").strip().casefold() not in {
        "0",
        "false",
        "no",
        "off",
    }


def _required_capabilities(action: ActionSpec) -> tuple[str, ...]:
    if action.action_id != "lossless_jpeg":
        return _ACTION_CAPABILITIES.get(action.action_id, ())
    fields = {field.field_id: field.value for field in action.fields}
    utility = fields.get("utility", "Exiftran (with exif support)")
    return ("jpegtran",) if utility.startswith("Jpegtran") else ("exiftran",)


def _unsafe_operation(action: ActionSpec) -> str | None:
    if action.action_id == "geek":
        return "geek"
    fields = {field.field_id: field.value for field in action.fields}
    if action.action_id == "save" and (
        ".." in Path(fields.get("file_name", "")).parts
        or Path(fields.get("file_name", "")).name != fields.get("file_name", "")
    ):
        return "save_path_escape"
    if any(
        "__" in field.value or field.value.lstrip().startswith("=")
        for field in action.fields
    ):
        return f"unsafe_expression:{action.action_id}"
    return None
