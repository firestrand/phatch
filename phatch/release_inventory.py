from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from email.message import Message
from email.parser import BytesParser
from hashlib import sha256
from importlib import import_module, metadata
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from packaging.requirements import Requirement

BASE_EXTRA: Final = ("",)
REQUIRED_RUNTIME_MODULES: Final = (
    "phatch.core.execution_results",
    "phatch.pyWx.action_availability",
    "phatch.pyWx.controller_history",
    "phatch.pyWx.execution_results",
    "phatch.pyWx.preview_panel",
    "phatch.pyWx.preview_runner",
    "phatch.services.editor_history",
    "phatch.services.field_presentation",
    "phatch.services.field_presentation_audit",
    "phatch.services.field_presentation_data",
    "phatch.services.field_presentation_help",
    "phatch.services.field_presentation_types",
    "phatch.services.parallel_save_jobs",
    "phatch.services.preview",
    "phatch.services.preview_actions",
    "phatch.services.preview_dimensions",
    "phatch.services.preview_inspection",
    "phatch.services.preview_policy",
    "phatch.services.preview_process",
    "phatch.services.preview_reads",
    "phatch.services.preview_types",
    "phatch.services.preview_worker",
    "phatch.services.report_privacy",
)
REQUIRED_RUNTIME_RESOURCES: Final = (
    "data/actionlists/crop_scale.phatch",
    "data/actionlists/metadata_preserving_export.phatch",
    "data/actionlists/resize.phatch",
    "data/actionlists/watermark.phatch",
    "data/actionlists/watermark.png",
    "data/actionlists/web_size_export.phatch",
)
EXPECTED_RESOURCE_COUNTS: Final = (
    ("action-lists", 25),
    ("blender", 105),
    ("documentation", 360),
    ("fonts", 2),
    ("highlights", 22),
    ("images", 38),
    ("locales", 50),
    ("masks", 40),
    ("perspective", 15),
)


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    version: str
    license_expression: str
    license_text: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeResourceRecord:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class RuntimeInventory:
    modules: tuple[str, ...]
    resources: tuple[RuntimeResourceRecord, ...]
    resource_counts: tuple[tuple[str, int], ...]


class WheelMetadataError(ValueError):
    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    def __str__(self) -> str:
        return self.detail


class MissingRuntimeDistributionError(RuntimeError):
    name: str

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(name)

    def __str__(self) -> str:
        return f"selected runtime dependency is not installed: {self.name}"


class RuntimeInventoryError(RuntimeError):
    detail: str

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)

    def __str__(self) -> str:
        return self.detail


def _license(expression: str | None, legacy: str | None) -> str:
    if expression:
        return expression
    if not legacy:
        return "NOASSERTION"
    value = legacy.strip()
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+-]*", value):
        return value
    label = value.partition("(")[0].strip()
    identifier = re.sub(r"[^A-Za-z0-9.-]+", "-", label).strip("-.")
    return f"LicenseRef-{identifier}" if identifier else "NOASSERTION"


def _license_text(expression: str | None, legacy: str | None) -> str | None:
    if expression or not legacy:
        return None
    normalized = _license(expression, legacy)
    return legacy.strip() if normalized.startswith("LicenseRef-") else None


def _selected(requirement: Requirement, extras: tuple[str, ...]) -> bool:
    marker = requirement.marker
    return marker is None or any(marker.evaluate({"extra": extra}) for extra in extras)


def _wheel_message(path: Path) -> Message:
    try:
        with zipfile.ZipFile(path) as wheel:
            candidates = tuple(
                name
                for name in wheel.namelist()
                if name.endswith(".dist-info/METADATA")
            )
            if len(candidates) != 1:
                raise WheelMetadataError(
                    f"expected exactly one wheel METADATA record: {path}"
                )
            return BytesParser().parsebytes(wheel.read(candidates[0]))
    except zipfile.BadZipFile as error:
        raise WheelMetadataError(f"invalid metadata wheel: {path}") from error


def _installed_record(name: str) -> tuple[PackageRecord, tuple[str, ...]]:
    try:
        distribution = metadata.distribution(name)
    except metadata.PackageNotFoundError as error:
        raise MissingRuntimeDistributionError(name) from error
    return (
        PackageRecord(
            distribution.metadata["Name"] or name,
            distribution.version,
            _license(
                distribution.metadata["License-Expression"],
                distribution.metadata["License"],
            ),
            _license_text(
                distribution.metadata["License-Expression"],
                distribution.metadata["License"],
            ),
        ),
        tuple(distribution.requires or ()),
    )


def package_records(
    metadata_wheel: Path, selected_extras: tuple[str, ...] = ()
) -> tuple[PackageRecord, ...]:
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    message = _wheel_message(metadata_wheel)
    root_name = message.get("Name")
    root_version = message.get("Version")
    if root_name is None or root_version is None:
        raise WheelMetadataError("wheel METADATA is missing Name or Version")
    records = [
        PackageRecord(
            root_name,
            root_version,
            _license(message.get("License-Expression"), message.get("License")),
            _license_text(
                message.get("License-Expression"), message.get("License")
            ),
        )
    ]
    represented = {canonicalize_name(root_name)}
    pending = [
        requirement
        for text in message.get_all("Requires-Dist", ())
        if _selected(requirement := Requirement(text), (*BASE_EXTRA, *selected_extras))
    ]
    while pending:
        requirement = pending.pop(0)
        normalized = canonicalize_name(requirement.name)
        if normalized in represented:
            continue
        record, requirements = _installed_record(requirement.name)
        represented.add(normalized)
        records.append(record)
        pending.extend(
            transitive
            for text in requirements
            if _selected(transitive := Requirement(text), ("",))
        )
    return tuple(records)


def collect_runtime_inventory() -> RuntimeInventory:
    from phatch.resources.inventory import RESOURCE_CLASSES
    from phatch.resources.provider import ResourceProvider

    for module_name in REQUIRED_RUNTIME_MODULES:
        try:
            import_module(module_name)
        except ImportError as error:
            raise RuntimeInventoryError(
                f"runtime module import failed: {module_name}: {error}"
            ) from error

    provider = ResourceProvider()
    resources = tuple(
        RuntimeResourceRecord(path, len(payload), sha256(payload).hexdigest())
        for path in REQUIRED_RUNTIME_RESOURCES
        for payload in (provider.read_bytes(path),)
    )
    resource_counts = tuple(
        (resource_class.value, len(provider.walk_files(root)))
        for resource_class, root in RESOURCE_CLASSES.items()
    )
    if resource_counts != EXPECTED_RESOURCE_COUNTS:
        raise RuntimeInventoryError(
            f"runtime resource counts differ: {resource_counts!r}"
        )
    return RuntimeInventory(REQUIRED_RUNTIME_MODULES, resources, resource_counts)
