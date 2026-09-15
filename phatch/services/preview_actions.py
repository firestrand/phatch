from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Protocol, assert_never, runtime_checkable

from phatch import actions
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildFailure,
    ActionRegistryBuildSuccess,
    build_action_registry,
)
from phatch.services.action_schema import RegistrySchemaCatalog
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewAdmissionError,
    PreviewErrorCode,
)


@runtime_checkable
class _PreviewAction(Protocol):
    def init(self) -> object: ...

    def values(self, info: Mapping[str, object]) -> Mapping[str, object]: ...

    def get_field(self, label: str, info: Mapping[str, object]) -> object: ...

    def get_field_size(
        self,
        label: str,
        info: Mapping[str, object],
        reference: int,
        dpi: object,
    ) -> object: ...

    def apply(
        self,
        photo: object,
        settings: object,
        cache: MutableMapping[str, object],
    ) -> object: ...


def construct_preview_actions(
    specs: tuple[PreviewActionSpec, ...],
    fields: tuple[dict[str, str], ...],
) -> tuple[_PreviewAction, ...]:
    package_path = Path(actions.__file__).parent
    result = build_action_registry(
        ActionCatalogSources(
            built_in=tuple(package_path.glob("*.py")),
            user=(),
            built_in_package="phatch.actions",
        )
    )
    match result:
        case ActionRegistryBuildFailure(issues=issues):
            reason = "; ".join(issue.message for issue in issues)
            raise PreviewAdmissionError(PreviewErrorCode.WORKER_FAILED, reason)
        case ActionRegistryBuildSuccess(registry=registry):
            catalog = RegistrySchemaCatalog(registry)
        case unreachable:
            assert_never(unreachable)
    constructed: list[_PreviewAction] = []
    for spec, action_fields in zip(specs, fields, strict=True):
        label = catalog.action_label(spec.action_id)
        if label is None:
            raise PreviewAdmissionError(
                PreviewErrorCode.UNKNOWN_ACTION,
                "action is absent from the production registry",
                spec.action_id,
            )
        action = registry.instantiate(label)
        loaded: dict[str, str] = {}
        for field_id, value in action_fields.items():
            field_label = catalog.field_label(spec.action_id, field_id)
            if field_label is None:
                raise PreviewAdmissionError(
                    PreviewErrorCode.INVALID_FIELD,
                    "field is absent from the production registry",
                    spec.action_id,
                )
            loaded[field_label] = value
        if not isinstance(action, _PreviewAction):
            raise PreviewAdmissionError(
                PreviewErrorCode.WORKER_FAILED,
                "registered action lacks the preview execution contract",
                spec.action_id,
            )
        invalid = action.load(loaded)
        if invalid:
            raise PreviewAdmissionError(
                PreviewErrorCode.INVALID_FIELD,
                f"invalid fields: {', '.join(invalid)}",
                spec.action_id,
            )
        relevant = getattr(action, "get_relevant_field_labels", None)
        if callable(relevant):
            relevant()
        action.init()
        constructed.append(action)
    return tuple(constructed)
