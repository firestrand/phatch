from __future__ import annotations

from typing import assert_never

from phatch.services.action_schema_types import ActionSpec
from phatch.services.preview_inspection import (
    inspect_preview_source,
    validate_preview_expressions,
    validate_preview_transition,
)
from phatch.services.preview_policy import (
    PolicyKind,
    PreviewAction,
    PreviewPolicy,
    PreviewPolicyViolation,
    policy_for,
)
from phatch.services.preview_reads import resolve_preview_reads
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewAdmissionError,
    PreviewDependencies,
    PreviewErrorCode,
    PreviewExecutionSpec,
    PreviewLimits,
    PreviewReadContext,
    PreviewRequest,
    ResolvedPreviewRead,
)

__all__ = [
    "admit_preview",
    "run_preview",
    "start_preview",
    "validate_preview_transition",
]


def start_preview(spec: PreviewExecutionSpec, request_id: str):
    from phatch.services.preview_process import start_preview as start

    return start(spec, request_id)


def run_preview(spec: PreviewExecutionSpec, request_id: str):
    from phatch.services.preview_process import run_preview as run

    return run(spec, request_id)


def admit_preview(
    request: PreviewRequest, dependencies: PreviewDependencies
) -> PreviewExecutionSpec:
    policies = _admit_policies(request)
    source = inspect_preview_source(request.source)
    required_variables = validate_preview_expressions(request, source)
    reads, bound_specs = resolve_preview_reads(request, policies, dependencies)
    _validate_catalog(bound_specs, reads, dependencies)
    actions = tuple(
        PreviewActionSpec(
            spec.action_id,
            tuple((field.field_id, field.value) for field in spec.fields),
        )
        for spec in bound_specs
    )
    limits = PreviewLimits()
    context = PreviewReadContext(source, reads)
    return PreviewExecutionSpec(
        actions,
        source,
        reads,
        required_variables,
        limits,
        context,
        len(policies) != len(bound_specs),
    )


def _admit_policies(request: PreviewRequest) -> tuple[PreviewPolicy, ...]:
    actions = tuple(
        PreviewAction(spec.action_id, _is_enabled(spec))
        for spec in request.document.actions
    )
    try:
        policies = tuple(policy_for(action.action_id) for action in actions)
    except PreviewPolicyViolation as error:
        raise PreviewAdmissionError(
            PreviewErrorCode.UNKNOWN_ACTION, error.reason, error.action_id
        ) from error
    enabled = tuple(
        policy
        for action, policy in zip(actions, policies, strict=True)
        if action.enabled
    )
    saves = tuple(item for item in enabled if item.kind is PolicyKind.TERMINAL_SAVE)
    if len(saves) > 1:
        raise PreviewAdmissionError(
            PreviewErrorCode.INVALID_SEQUENCE,
            "preview accepts at most one enabled save",
            "save",
        )
    for index, policy in enumerate(enabled):
        match policy.kind:
            case PolicyKind.ELIGIBLE:
                continue
            case PolicyKind.BLOCKED:
                reason = policy.reason
                if reason is None:
                    raise PreviewAdmissionError(
                        PreviewErrorCode.BLOCKED_ACTION,
                        "action is blocked from preview",
                        policy.action_id,
                    )
                raise PreviewAdmissionError(
                    PreviewErrorCode.BLOCKED_ACTION,
                    reason.message,
                    policy.action_id,
                )
            case PolicyKind.TERMINAL_SAVE:
                if index != len(enabled) - 1:
                    raise PreviewAdmissionError(
                        PreviewErrorCode.INVALID_SEQUENCE,
                        "save must be the final enabled action",
                        "save",
                    )
            case unreachable:
                assert_never(unreachable)
    return enabled


def _is_enabled(spec: ActionSpec) -> bool:
    value = next(
        (field.value for field in spec.fields if field.field_id == "enabled"), "yes"
    )
    return value.strip().casefold() not in {"0", "false", "no", "off"}


def _validate_catalog(
    specs: tuple[ActionSpec, ...],
    reads: tuple[ResolvedPreviewRead, ...],
    dependencies: PreviewDependencies,
) -> None:
    catalog = dependencies.catalog_factory()
    read_fields = {(read.action_index, read.field_id) for read in reads}
    for action_index, spec in enumerate(specs):
        if catalog.action_label(spec.action_id) is None:
            raise PreviewAdmissionError(
                PreviewErrorCode.UNKNOWN_ACTION,
                "action is absent from the schema catalog",
                spec.action_id,
            )
        for field in spec.fields:
            if catalog.field_label(spec.action_id, field.field_id) is None:
                raise PreviewAdmissionError(
                    PreviewErrorCode.INVALID_FIELD,
                    "field is absent from the schema catalog",
                    spec.action_id,
                    field.field_id,
                )
        validation_spec = ActionSpec(
            spec.action_id,
            tuple(
                field
                for field in spec.fields
                if (action_index, field.field_id) not in read_fields
            ),
        )
        invalid = catalog.invalid_fields(validation_spec)
        if invalid:
            raise PreviewAdmissionError(
                PreviewErrorCode.INVALID_FIELD,
                f"invalid fields: {', '.join(invalid)}",
                spec.action_id,
            )
