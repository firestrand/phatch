from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityProbeContractError,
    CapabilityReasonCode,
    CapabilityRegistry,
    CapabilityStatus,
    CapabilityValidationError,
    DuplicateCapabilityError,
    UnknownCapabilityError,
)


def capability(identifier: CapabilityId) -> Capability:
    return Capability(
        identifier=identifier,
        status=CapabilityStatus.AVAILABLE,
        reason_code=CapabilityReasonCode.AVAILABLE,
        reason="ready",
    )


def test_capability_is_an_immutable_typed_record() -> None:
    record = capability(CapabilityId("renderer"))

    assert record.available
    with pytest.raises(FrozenInstanceError):
        record.__setattr__("reason", "changed")


def test_registry_is_lazy_and_reprobes_without_caching() -> None:
    identifier = CapabilityId("renderer")
    calls = 0

    def probe() -> Capability:
        nonlocal calls
        calls += 1
        return capability(identifier)

    registry = CapabilityRegistry(((identifier, probe),))

    assert calls == 0
    assert registry.probe(identifier).available
    assert registry.probe_all() == (capability(identifier),)
    assert calls == 2


def test_registry_rejects_duplicate_unknown_and_mismatched_capabilities() -> None:
    identifier = CapabilityId("renderer")

    def probe() -> Capability:
        return capability(identifier)

    with pytest.raises(DuplicateCapabilityError) as duplicate:
        CapabilityRegistry(((identifier, probe), (identifier, probe)))
    assert str(duplicate.value) == "duplicate capability: renderer"
    with pytest.raises(UnknownCapabilityError) as unknown:
        CapabilityRegistry(()).probe(identifier)
    assert str(unknown.value) == "unknown capability: renderer"
    with pytest.raises(CapabilityProbeContractError) as mismatch:
        CapabilityRegistry(
            ((identifier, lambda: capability(CapabilityId("other"))),)
        ).probe(identifier)
    assert str(mismatch.value) == "probe for renderer returned other"


@pytest.mark.parametrize(
    ("status", "reason_code", "expected"),
    [
        (CapabilityStatus.AVAILABLE, CapabilityReasonCode.AVAILABLE, True),
        (
            CapabilityStatus.UNAVAILABLE,
            CapabilityReasonCode.MISSING_PACKAGE,
            False,
        ),
        (
            CapabilityStatus.MISCONFIGURED,
            CapabilityReasonCode.BROKEN_IMPORT,
            False,
        ),
    ],
)
def test_available_property_reflects_status(
    status: CapabilityStatus,
    reason_code: CapabilityReasonCode,
    expected: bool,
) -> None:
    record = Capability(
        identifier=CapabilityId("tool"),
        status=status,
        reason_code=reason_code,
        reason="state",
    )

    assert record.available is expected


@pytest.mark.parametrize(
    "record",
    [
        lambda: Capability(
            CapabilityId(""),
            CapabilityStatus.UNAVAILABLE,
            CapabilityReasonCode.MISSING_PACKAGE,
            "missing",
        ),
        lambda: Capability(
            CapabilityId("tool"),
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.MISSING_PACKAGE,
            "mismatch",
        ),
        lambda: Capability(
            CapabilityId("tool"),
            CapabilityStatus.UNAVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            "mismatch",
        ),
    ],
)
def test_capability_rejects_incoherent_records(record) -> None:
    with pytest.raises(CapabilityValidationError):
        record()


@pytest.mark.parametrize(
    ("status", "reason_code"),
    [
        (CapabilityStatus.UNAVAILABLE, CapabilityReasonCode.BROKEN_IMPORT),
        (CapabilityStatus.UNAVAILABLE, CapabilityReasonCode.UNSUPPORTED_VERSION),
        (CapabilityStatus.MISCONFIGURED, CapabilityReasonCode.MISSING_PACKAGE),
        (CapabilityStatus.MISCONFIGURED, CapabilityReasonCode.MISSING_EXECUTABLE),
        (CapabilityStatus.MISCONFIGURED, CapabilityReasonCode.UNSUPPORTED_PLATFORM),
    ],
)
def test_capability_rejects_nonavailable_reason_mismatches(
    status: CapabilityStatus,
    reason_code: CapabilityReasonCode,
) -> None:
    with pytest.raises(CapabilityValidationError, match="status and reason code"):
        Capability(CapabilityId("tool"), status, reason_code, "mismatch")
