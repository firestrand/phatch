from __future__ import annotations

from types import SimpleNamespace

import pytest

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.pyWx import action_availability
from phatch.pyWx.action_availability import describe_action_availability


def test_available_previewable_action_has_supported_badge() -> None:
    result = describe_action_availability("Scale", {})

    assert result.available
    assert result.preview_supported


def test_blocked_action_keeps_availability_distinct_from_preview_policy() -> None:
    result = describe_action_availability("Geek", {})

    assert result.available
    assert not result.preview_supported
    assert "arbitrary process" in result.preview_reason


def test_missing_external_capability_is_unavailable_and_preview_blocked() -> None:
    capability = Capability(
        CapabilityId("imagemagick-6"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "install ImageMagick 6",
    )

    result = describe_action_availability("Imagemagick", {"imagemagick-6": capability})

    assert not result.available
    assert result.availability_reason == "install ImageMagick 6"
    assert not result.preview_supported


def test_available_external_capability_retains_probe_reason() -> None:
    capability = Capability(
        CapabilityId("blender-2.45-2.49"),
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        "Blender 2.49 available",
    )

    result = describe_action_availability("Blender", {"blender-2.45-2.49": capability})

    assert result.available
    assert result.availability_reason == "Blender 2.49 available"
    assert not result.preview_supported


def test_declared_read_is_requirement_not_unavailability() -> None:
    result = describe_action_availability("Watermark", {})

    assert result.available
    assert result.preview_supported
    assert "requires an image resource" in result.preview_reason


def test_unknown_action_does_not_construct_plugin() -> None:
    result = describe_action_availability("User Action", {})

    assert result.available
    assert not result.preview_supported
    assert "unrecognized" in result.preview_reason


def test_terminal_save_badge_explains_preview_omission() -> None:
    result = describe_action_availability("Save", {})

    assert result.available
    assert result.preview_supported
    assert "omitted" in result.preview_reason


def test_unknown_preview_policy_kind_fails_exhaustively(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        action_availability,
        "policy_for",
        lambda _action_id: SimpleNamespace(kind="future-policy"),
    )

    with pytest.raises(AssertionError, match="future-policy"):
        describe_action_availability("Scale", {})


@pytest.mark.parametrize("kind", ["blocked", "terminal_save"])
def test_preview_policy_without_required_reason_is_rejected(
    kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        action_availability,
        "policy_for",
        lambda action_id: SimpleNamespace(
            action_id=action_id,
            kind=action_availability.PolicyKind(kind),
            reason=None,
        ),
    )

    with pytest.raises(action_availability.PreviewPolicyViolation):
        describe_action_availability("Scale", {})
