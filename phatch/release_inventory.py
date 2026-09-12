from __future__ import annotations

import zipfile
from dataclasses import dataclass
from email.message import Message
from email.parser import BytesParser
from importlib import metadata
from pathlib import Path
from typing import Final

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

BASE_EXTRA: Final = ("",)


@dataclass(frozen=True, slots=True)
class PackageRecord:
    name: str
    version: str
    license_expression: str


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


def _license(expression: str | None, legacy: str | None) -> str:
    return expression or legacy or "NOASSERTION"


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
        ),
        tuple(distribution.requires or ()),
    )


def package_records(
    metadata_wheel: Path, selected_extras: tuple[str, ...] = ()
) -> tuple[PackageRecord, ...]:
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
