from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum, unique
from types import MappingProxyType
from typing import Final, assert_never


@unique
class PolicyKind(StrEnum):
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"
    TERMINAL_SAVE = "terminal_save"


@unique
class ReadKind(StrEnum):
    PACKAGED_OR_SELECTED_FILE = "packaged_or_selected_file"


@unique
class AdapterKind(StrEnum):
    FILE_REFERENCE = "file_reference"
    PACKAGED_CATALOG = "packaged_catalog"


@dataclass(frozen=True, slots=True)
class ReadCondition:
    field_id: str
    equals: str


@dataclass(frozen=True, slots=True)
class ReadRequirement:
    field_id: str
    kind: ReadKind
    condition: ReadCondition | None = None


@dataclass(frozen=True, slots=True)
class AdapterRequirement:
    field_id: str
    kind: AdapterKind


@dataclass(frozen=True, slots=True)
class PreviewReason:
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True, slots=True)
class PreviewPolicy:
    action_id: str
    kind: PolicyKind
    reason: PreviewReason | None = None
    reads: tuple[ReadRequirement, ...] = ()
    adapters: tuple[AdapterRequirement, ...] = ()


@dataclass(frozen=True, slots=True)
class PreviewAction:
    action_id: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class PreviewAdmission:
    action_ids: tuple[str, ...]
    omitted_terminal_save: bool


@dataclass(frozen=True, slots=True)
class PreviewPolicyViolation(ValueError):
    action_id: str
    reason: str

    def __str__(self) -> str:
        return f"{self.action_id}: {self.reason}"


_ELIGIBLE_IDS: Final = frozenset(
    {
        "auto_contrast",
        "background",
        "border",
        "brightness",
        "canvas",
        "color_to_alpha",
        "colorize",
        "common",
        "contour",
        "contrast",
        "convert_mode",
        "crop",
        "desaturate",
        "effect",
        "equalize",
        "fit",
        "grid",
        "highlight",
        "invert",
        "mask",
        "maximum",
        "median",
        "minimum",
        "mirror",
        "offset",
        "perspective",
        "posterize",
        "rank",
        "reflection",
        "rotate",
        "round",
        "saturation",
        "scale",
        "shadow",
        "sketch",
        "solarize",
        "text",
        "transpose",
        "warm_up",
        "watermark",
    }
)

_BLOCKED_REASONS: Final = MappingProxyType(
    {
        "blender": "external process/temp output",
        "copy": "file write",
        "delete_tags": "metadata mutation",
        "geek": "arbitrary process",
        "geotag": "metadata/report I/O",
        "imagemagick": "external process",
        "lossless_jpeg": "file mutation",
        "rename": "source rename",
        "rename_tag": "metadata mutation",
        "save_tags": "metadata file output",
        "tamogen": "folder/content-dependent reads",
        "time_shift": "metadata/file-date mutation",
        "write_tag": "metadata mutation",
    }
)

_READS: Final = MappingProxyType(
    {
        "background": (
            ReadRequirement(
                "mark",
                ReadKind.PACKAGED_OR_SELECTED_FILE,
                ReadCondition("fill", "Image"),
            ),
        ),
        "highlight": (
            ReadRequirement("highlight", ReadKind.PACKAGED_OR_SELECTED_FILE),
        ),
        "mask": (ReadRequirement("mask", ReadKind.PACKAGED_OR_SELECTED_FILE),),
        "text": (ReadRequirement("font", ReadKind.PACKAGED_OR_SELECTED_FILE),),
        "watermark": (ReadRequirement("mark", ReadKind.PACKAGED_OR_SELECTED_FILE),),
    }
)

_ADAPTERS: Final = MappingProxyType(
    {
        "background": (AdapterRequirement("mark", AdapterKind.FILE_REFERENCE),),
        "highlight": (AdapterRequirement("highlight", AdapterKind.FILE_REFERENCE),),
        "mask": (AdapterRequirement("mask", AdapterKind.FILE_REFERENCE),),
        "perspective": (
            AdapterRequirement("projection", AdapterKind.PACKAGED_CATALOG),
        ),
        "watermark": (AdapterRequirement("mark", AdapterKind.FILE_REFERENCE),),
    }
)

_policies = {
    action_id: PreviewPolicy(
        action_id,
        PolicyKind.ELIGIBLE,
        reads=_READS.get(action_id, ()),
        adapters=_ADAPTERS.get(action_id, ()),
    )
    for action_id in _ELIGIBLE_IDS
}
_policies.update(
    {
        action_id: PreviewPolicy(action_id, PolicyKind.BLOCKED, PreviewReason(reason))
        for action_id, reason in _BLOCKED_REASONS.items()
    }
)
_policies["save"] = PreviewPolicy(
    "save",
    PolicyKind.TERMINAL_SAVE,
    PreviewReason("terminal Save is omitted from preview output"),
)
PREVIEW_POLICIES: Final[Mapping[str, PreviewPolicy]] = MappingProxyType(_policies)
del _policies


def policy_for(action_id: str) -> PreviewPolicy:
    try:
        return PREVIEW_POLICIES[action_id]
    except KeyError as error:
        raise PreviewPolicyViolation(
            action_id, f"unknown action ID: {action_id}"
        ) from error


def admit_preview_actions(
    actions: tuple[PreviewAction, ...],
) -> PreviewAdmission:
    policies = tuple(policy_for(action.action_id) for action in actions)
    enabled = tuple(
        policy
        for action, policy in zip(actions, policies, strict=True)
        if action.enabled
    )
    saves = tuple(
        policy for policy in enabled if policy.kind is PolicyKind.TERMINAL_SAVE
    )
    if len(saves) > 1:
        raise PreviewPolicyViolation("save", "preview accepts at most one enabled save")
    for index, policy in enumerate(enabled):
        match policy.kind:
            case PolicyKind.ELIGIBLE:
                continue
            case PolicyKind.BLOCKED:
                reason = policy.reason
                if reason is None:
                    raise PreviewPolicyViolation(
                        policy.action_id, "action is blocked from preview"
                    )
                raise PreviewPolicyViolation(policy.action_id, reason.message)
            case PolicyKind.TERMINAL_SAVE:
                if index != len(enabled) - 1:
                    raise PreviewPolicyViolation(
                        "save", "save must be the final enabled action"
                    )
            case unreachable:
                assert_never(unreachable)
    return PreviewAdmission(
        tuple(
            policy.action_id for policy in enabled if policy.kind is PolicyKind.ELIGIBLE
        ),
        bool(saves),
    )
