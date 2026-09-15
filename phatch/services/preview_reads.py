from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Final, assert_never

from phatch.core.file_references import FileReferenceError, parse_file_reference
from phatch.resources.provider import ResourceNotFoundError
from phatch.services.action_schema_types import ActionDocument, ActionField, ActionSpec
from phatch.services.preview_policy import (
    PREVIEW_POLICIES,
    AdapterKind,
    PolicyKind,
    PreviewPolicy,
)
from phatch.services.preview_types import (
    PackagedPreviewRead,
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewRequest,
    ResolvedPreviewRead,
    SelectedPreviewRead,
)

_RESOURCE_DIRECTORIES: Final[Mapping[tuple[str, str], tuple[str, ...]]] = {
    ("background", "mark"): ("images",),
    ("highlight", "highlight"): ("data/highlights",),
    ("mask", "mask"): ("data/masks",),
    ("perspective", "projection"): ("data/perspective",),
    ("text", "font"): ("data/fonts",),
    ("watermark", "mark"): ("images", "data/actionlists/watermark.png"),
}


@dataclass(frozen=True, slots=True)
class ExternalPreviewRead:
    action_id: str
    field_id: str
    path: Path


def external_preview_reads(
    document: ActionDocument,
    dependencies: PreviewDependencies,
) -> tuple[ExternalPreviewRead, ...]:
    reads: list[ExternalPreviewRead] = []
    for spec in document.actions:
        policy = PREVIEW_POLICIES.get(spec.action_id)
        if (
            policy is None
            or policy.kind is not PolicyKind.ELIGIBLE
            or not _is_enabled(spec)
        ):
            continue
        values = {field.field_id: field.value for field in spec.fields}
        for field_id in _active_read_fields(policy, values):
            value = values.get(field_id)
            if value is None or _packaged_read(
                0,
                spec.action_id,
                field_id,
                value,
                dependencies,
            ):
                continue
            try:
                parsed = parse_file_reference(value, dependencies.platform)
                if not isinstance(parsed, Path) or not parsed.is_absolute():
                    continue
                path = parsed.resolve(strict=False)
            except (FileReferenceError, OSError):
                continue
            candidate = ExternalPreviewRead(spec.action_id, field_id, path)
            if candidate not in reads:
                reads.append(candidate)
    return tuple(reads)


def resolve_preview_reads(
    request: PreviewRequest,
    policies: tuple[PreviewPolicy, ...],
    dependencies: PreviewDependencies,
) -> tuple[tuple[ResolvedPreviewRead, ...], tuple[ActionSpec, ...]]:
    selected = _selected_paths(request.selected_files)
    enabled_specs = tuple(
        spec for spec in request.document.actions if _is_enabled(spec)
    )
    reads: list[ResolvedPreviewRead] = []
    bound_specs: list[ActionSpec] = []
    for action_index, (spec, policy) in enumerate(
        zip(enabled_specs, policies, strict=True)
    ):
        if policy.kind is PolicyKind.TERMINAL_SAVE:
            continue
        values = {field.field_id: field.value for field in spec.fields}
        active_ids = _active_read_fields(policy, values)
        controlled_ids = {requirement.field_id for requirement in policy.reads}.union(
            adapter.field_id for adapter in policy.adapters
        )
        replacements: dict[str, str] = {}
        for field_id in active_ids:
            if field_id not in values:
                raise PreviewAdmissionError(
                    PreviewErrorCode.INVALID_FIELD,
                    "required read field is missing",
                    spec.action_id,
                    field_id,
                )
            resolved = _resolve_read(
                action_index,
                spec.action_id,
                field_id,
                values[field_id],
                selected,
                dependencies,
            )
            if resolved not in reads:
                reads.append(resolved)
            match resolved:
                case PackagedPreviewRead(resource=resource):
                    if not _is_packaged_catalog(policy, field_id):
                        replacements[field_id] = f"package:{resource.value}"
                case SelectedPreviewRead(path=path):
                    replacements[field_id] = str(path)
                case unreachable:
                    assert_never(unreachable)
        bound_specs.append(
            ActionSpec(
                spec.action_id,
                tuple(
                    ActionField(
                        field.field_id,
                        replacements.get(field.field_id, field.value),
                    )
                    for field in spec.fields
                    if field.field_id not in controlled_ids
                    or field.field_id in active_ids
                ),
            )
        )
    return tuple(reads), tuple(bound_specs)


def _active_read_fields(
    policy: PreviewPolicy, values: Mapping[str, str]
) -> tuple[str, ...]:
    active: list[str] = []
    for requirement in policy.reads:
        condition = requirement.condition
        if condition is None or values.get(condition.field_id) == condition.equals:
            active.append(requirement.field_id)
    for adapter in policy.adapters:
        if (
            policy.action_id == "background"
            and adapter.field_id == "mark"
            and values.get("fill") != "Image"
        ):
            continue
        if adapter.field_id in values and adapter.field_id not in active:
            active.append(adapter.field_id)
    return tuple(active)


def _is_packaged_catalog(policy: PreviewPolicy, field_id: str) -> bool:
    return any(
        adapter.field_id == field_id and adapter.kind is AdapterKind.PACKAGED_CATALOG
        for adapter in policy.adapters
    )


def _selected_paths(paths: Sequence[Path]) -> frozenset[Path]:
    try:
        return frozenset(path.resolve(strict=True) for path in paths)
    except OSError as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.READ_NOT_FOUND, "a declared selected file is missing"
        ) from error


def _resolve_read(
    action_index: int,
    action_id: str,
    field_id: str,
    value: str,
    selected: frozenset[Path],
    dependencies: PreviewDependencies,
) -> ResolvedPreviewRead:
    packaged = _packaged_read(action_index, action_id, field_id, value, dependencies)
    if packaged is not None:
        return packaged
    try:
        parsed = parse_file_reference(value, dependencies.platform)
        if not isinstance(parsed, Path) or not parsed.is_absolute():
            raise FileReferenceError(value, "selected path must be absolute")
        canonical = parsed.resolve(strict=False)
    except (FileReferenceError, OSError) as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.UNDECLARED_READ,
            "read must name a packaged resource or declared selected file",
            action_id,
            field_id,
        ) from error
    if canonical not in selected:
        raise PreviewAdmissionError(
            PreviewErrorCode.UNDECLARED_READ,
            "selected file was not declared by the request",
            action_id,
            field_id,
        )
    if not canonical.is_file():
        raise PreviewAdmissionError(
            PreviewErrorCode.READ_NOT_FOUND,
            "declared selected file is missing",
            action_id,
            field_id,
        )
    return SelectedPreviewRead(
        action_index,
        field_id,
        canonical,
        _hash_file(canonical),
    )


def _packaged_read(
    action_index: int,
    action_id: str,
    field_id: str,
    value: str,
    dependencies: PreviewDependencies,
) -> PackagedPreviewRead | None:
    directories = _RESOURCE_DIRECTORIES.get((action_id, field_id), ())
    for directory in directories:
        try:
            resources = dependencies.resources.walk_files(directory)
        except ResourceNotFoundError:
            resources = ()
        for resource in resources:
            alias = resource.name.rsplit(".", 1)[0]
            if _resource_key(alias) == _resource_key(value):
                return PackagedPreviewRead(action_index, field_id, resource)
    return None


def _is_enabled(spec: ActionSpec) -> bool:
    value = next(
        (field.value for field in spec.fields if field.field_id == "enabled"), "yes"
    )
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def _hash_file(path: Path) -> str:
    digest = sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.READ_NOT_FOUND,
            "declared selected file is missing",
        ) from error
    return digest.hexdigest()


def _resource_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())
