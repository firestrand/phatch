from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import NewType, Protocol

CapabilityId = NewType("CapabilityId", str)


class CapabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"


class CapabilityReasonCode(StrEnum):
    AVAILABLE = "available"
    MISSING_EXECUTABLE = "missing_executable"
    MISSING_PACKAGE = "missing_package"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    BROKEN_IMPORT = "broken_import"
    INCOMPATIBLE_API = "incompatible_api"
    UNSUPPORTED_VERSION = "unsupported_version"
    PROBE_FAILED = "probe_failed"


@dataclass(frozen=True, slots=True)
class CapabilityValidationError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class Capability:
    identifier: CapabilityId
    status: CapabilityStatus
    reason_code: CapabilityReasonCode
    reason: str
    executable: Path | None = None
    version: str | None = None

    def __post_init__(self) -> None:
        if not self.identifier or not self.reason:
            raise CapabilityValidationError(
                "capability ID and reason must not be empty"
            )
        reasons_by_status = {
            CapabilityStatus.AVAILABLE: {CapabilityReasonCode.AVAILABLE},
            CapabilityStatus.UNAVAILABLE: {
                CapabilityReasonCode.MISSING_EXECUTABLE,
                CapabilityReasonCode.MISSING_PACKAGE,
                CapabilityReasonCode.UNSUPPORTED_PLATFORM,
            },
            CapabilityStatus.MISCONFIGURED: {
                CapabilityReasonCode.BROKEN_IMPORT,
                CapabilityReasonCode.INCOMPATIBLE_API,
                CapabilityReasonCode.UNSUPPORTED_VERSION,
                CapabilityReasonCode.PROBE_FAILED,
            },
        }
        if self.reason_code not in reasons_by_status[self.status]:
            raise CapabilityValidationError(
                "capability status and reason code must describe the same state"
            )

    @property
    def available(self) -> bool:
        return self.status is CapabilityStatus.AVAILABLE


class CapabilityProbe(Protocol):
    def __call__(self) -> Capability: ...


@dataclass(frozen=True, slots=True)
class DuplicateCapabilityError(ValueError):
    identifier: CapabilityId

    def __str__(self) -> str:
        return f"duplicate capability: {self.identifier}"


@dataclass(frozen=True, slots=True)
class UnknownCapabilityError(LookupError):
    identifier: CapabilityId

    def __str__(self) -> str:
        return f"unknown capability: {self.identifier}"


@dataclass(frozen=True, slots=True)
class CapabilityProbeContractError(RuntimeError):
    expected: CapabilityId
    actual: CapabilityId

    def __str__(self) -> str:
        return f"probe for {self.expected} returned {self.actual}"


@dataclass(frozen=True, slots=True)
class CapabilityRegistry:
    probes: tuple[tuple[CapabilityId, CapabilityProbe], ...]

    def __post_init__(self) -> None:
        identifiers: set[CapabilityId] = set()
        for identifier, _probe in self.probes:
            if identifier in identifiers:
                raise DuplicateCapabilityError(identifier)
            identifiers.add(identifier)

    def probe(self, identifier: CapabilityId) -> Capability:
        for registered_id, probe in self.probes:
            if registered_id == identifier:
                result = probe()
                if result.identifier != identifier:
                    raise CapabilityProbeContractError(identifier, result.identifier)
                return result
        raise UnknownCapabilityError(identifier)

    def probe_all(self) -> tuple[Capability, ...]:
        return tuple(self.probe(identifier) for identifier, _probe in self.probes)
