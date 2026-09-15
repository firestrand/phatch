from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import assert_never

from phatch.lib.capabilities import Capability
from phatch.lib.external_capability_probes import BLENDER_LEGACY, IMAGEMAGICK_6
from phatch.lib.reverse_translation import _t
from phatch.services.action_schema import normalize_identifier
from phatch.services.preview_policy import (
    PolicyKind,
    PreviewPolicyViolation,
    policy_for,
)

_CAPABILITY_BY_ACTION = {
    "blender": BLENDER_LEGACY,
    "imagemagick": IMAGEMAGICK_6,
}


@dataclass(frozen=True, slots=True)
class ActionAvailability:
    available: bool
    availability_reason: str
    preview_supported: bool
    preview_reason: str


def describe_action_availability(
    label: str,
    capabilities: Mapping[str, Capability],
) -> ActionAvailability:
    action_id = normalize_identifier(label)
    capability_id = _CAPABILITY_BY_ACTION.get(action_id)
    capability = capabilities.get(str(capability_id)) if capability_id else None
    available = capability is None or capability.available
    availability_reason = _t("Available" if capability is None else capability.reason)
    try:
        policy = policy_for(action_id)
    except PreviewPolicyViolation:
        return ActionAvailability(
            available,
            availability_reason,
            False,
            _t("Preview unavailable for unrecognized actions"),
        )
    match policy.kind:
        case PolicyKind.ELIGIBLE:
            if policy.reads:
                reason = _t("Preview supported; requires an image resource")
            else:
                reason = _t("Preview supported")
            return ActionAvailability(available, availability_reason, True, reason)
        case PolicyKind.BLOCKED:
            reason = policy.reason
            if reason is None:
                raise PreviewPolicyViolation(
                    policy.action_id, "action is blocked from preview"
                )
            return ActionAvailability(
                available,
                availability_reason,
                False,
                _t(f"Preview blocked: {reason.message}"),
            )
        case PolicyKind.TERMINAL_SAVE:
            reason = policy.reason
            if reason is None:
                raise PreviewPolicyViolation(
                    policy.action_id, "terminal action requires a preview reason"
                )
            return ActionAvailability(
                available,
                availability_reason,
                True,
                _t(reason.message),
            )
        case unreachable:
            assert_never(unreachable)
