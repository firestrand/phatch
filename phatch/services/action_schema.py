from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Protocol, TypeGuard, assert_never, runtime_checkable

from phatch.core.action_registry import RegisteredAction, RegistryField
from phatch.lib import metadata
from phatch.services.action_schema_types import (
    IDENTIFIER,
    SCHEMA_VERSION,
    ActionDocument,
    ActionField,
    ActionSpec,
    LegacyActionDocument,
    ParsedActionDocument,
    SchemaValidationError,
)
from phatch.services.action_schema_types import (
    parse_action_list as _parse_action_list,
)
from phatch.services.legacy_types import LegacyActionObject, LegacyField


class ActionSchemaCatalog(Protocol):
    def action_id(self, label: str) -> str | None: ...

    def action_label(self, action_id: str) -> str | None: ...

    def field_id(self, action_id: str, label: str) -> str | None: ...

    def field_label(self, action_id: str, field_id: str) -> str | None: ...

    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]:
        return ()


class SchemaActionRegistry(Protocol):
    @property
    def fields(self) -> Mapping[str, Mapping[str, RegistryField]]: ...

    def labels(self) -> tuple[str, ...]: ...

    def instantiate(self, label: str) -> RegisteredAction: ...


@runtime_checkable
class CommandField(Protocol):
    needs_exe: bool
    needs_in: bool
    needs_out: bool


def parse_action_list(source: str) -> ParsedActionDocument:
    return _parse_action_list(source)


class RegistrySchemaCatalog:
    __slots__ = ("_action_ids", "_descriptors", "_field_ids", "_fields", "_labels")

    def __init__(self, registry: SchemaActionRegistry) -> None:
        self._action_ids, self._labels = _identifier_maps(registry.labels())
        self._field_ids: dict[str, dict[str, str]] = {}
        self._fields: dict[str, dict[str, str]] = {}
        self._descriptors: dict[str, Mapping[str, RegistryField]] = {}
        registry_fields = registry.fields
        for action_id, label in self._labels.items():
            field_ids, fields = _identifier_maps(tuple(registry_fields[label]))
            self._field_ids[action_id] = field_ids
            self._fields[action_id] = fields
            self._descriptors[action_id] = registry_fields[label]

    def action_id(self, label: str) -> str | None:
        return self._action_ids.get(label)

    def action_label(self, action_id: str) -> str | None:
        return self._labels.get(action_id)

    def field_id(self, action_id: str, label: str) -> str | None:
        return self._field_ids.get(action_id, {}).get(label)

    def field_label(self, action_id: str, field_id: str) -> str | None:
        return self._fields.get(action_id, {}).get(field_id)

    def invalid_fields(self, spec: ActionSpec) -> tuple[str, ...]:
        fields = {
            self._fields[spec.action_id][field.field_id]: field.value
            for field in spec.fields
        }
        if spec.action_id == "geek":
            command = self._descriptors[spec.action_id]["Command"]
            if not isinstance(command, CommandField):
                raise SchemaValidationError("invalid Geek command field descriptor")
            values = {field.field_id: field.value for field in spec.fields}
            command.needs_exe = _is_true(values.get("verify_program", "yes"))
            command.needs_in = _is_true(values.get("verify_input", "yes"))
            command.needs_out = _is_true(values.get("verify_output", "yes"))
        invalid_labels = _invalid_field_values(
            self._descriptors[spec.action_id], fields
        )
        return tuple(self._field_ids[spec.action_id][label] for label in invalid_labels)


def normalize_identifier(label: str) -> str:
    if label == "__enabled__":
        return "enabled"
    normalized = re.sub(r"[^a-z0-9]+", "_", label.casefold()).strip("_")
    if IDENTIFIER.fullmatch(normalized) is None:
        raise SchemaValidationError(f"label has no stable identifier: {label}")
    return normalized


def _is_true(value: str) -> bool:
    return value.strip().casefold() in {"1", "true", "yes", "on"}


def _identifier_maps(labels: tuple[str, ...]) -> tuple[dict[str, str], dict[str, str]]:
    ids_by_label: dict[str, str] = {}
    labels_by_id: dict[str, str] = {}
    occurrences: dict[str, int] = {}
    for label in sorted(labels):
        base = normalize_identifier(label)
        occurrence = occurrences.get(base, 0) + 1
        occurrences[base] = occurrence
        identifier = base if occurrence == 1 else f"{base}_{occurrence}"
        ids_by_label[label] = identifier
        labels_by_id[identifier] = label
    return ids_by_label, labels_by_id


def construct_document_actions(
    document: ActionDocument,
    catalog: ActionSchemaCatalog,
    registry: SchemaActionRegistry,
) -> tuple[LegacyActionObject, ...]:
    _validate_catalog_ids(document, catalog)
    invalid = validate_document_fields(document, catalog)
    if invalid:
        raise SchemaValidationError(f"invalid fields: {', '.join(invalid)}")
    actions: list[LegacyActionObject] = []
    for spec in document.actions:
        label = catalog.action_label(spec.action_id)
        assert label is not None
        try:
            action = registry.instantiate(label)
        except (KeyError, TypeError) as error:
            raise SchemaValidationError(
                f"could not construct action: {spec.action_id}"
            ) from error
        if not _is_legacy_action(action):
            raise SchemaValidationError(
                f"action does not implement execution contract: {spec.action_id}"
            )
        fields: dict[str, str] = {}
        for field in spec.fields:
            field_label = catalog.field_label(spec.action_id, field.field_id)
            if field_label is None:
                raise SchemaValidationError(
                    f"unknown field ID for {spec.action_id}: {field.field_id}"
                )
            fields[field_label] = field.value
        invalid = action.load(fields)
        if invalid:
            raise SchemaValidationError(
                f"invalid fields for {spec.action_id}: {', '.join(invalid)}"
            )
        get_relevant_fields = getattr(action, "get_relevant_field_labels", None)
        if callable(get_relevant_fields):
            get_relevant_fields()
        invalid_values = _invalid_field_values(action._get_fields(), fields)
        if invalid_values:
            raise SchemaValidationError(
                f"invalid fields for {spec.action_id}: {', '.join(invalid_values)}"
            )
        actions.append(action)
    return tuple(actions)


def _is_legacy_action(action: RegisteredAction) -> TypeGuard[LegacyActionObject]:
    return all(
        callable(getattr(action, name, None))
        for name in ("_get_fields", "load", "is_enabled")
    )


def validate_document_fields(
    document: ActionDocument, catalog: ActionSchemaCatalog
) -> tuple[str, ...]:
    return tuple(
        f"{spec.action_id}.{field_id}"
        for spec in document.actions
        for field_id in catalog.invalid_fields(spec)
    )


def _invalid_field_values(
    action_fields: Mapping[str, RegistryField | LegacyField],
    fields: Mapping[str, str],
) -> tuple[str, ...]:
    invalid: list[str] = []
    test_info = metadata.InfoTest()
    for label, value in fields.items():
        field = action_fields[label]
        set_as_string = getattr(field, "set_as_string", None)
        assert_safe = getattr(field, "assert_safe", None)
        get = getattr(field, "get", None)
        try:
            if callable(assert_safe):
                if callable(set_as_string):
                    set_as_string(value)
                assert_safe(label, test_info)
            get_size = getattr(field, "get_size", None)
            if callable(get_size):
                get_size(test_info, 100, 100, label, value)
            elif callable(get):
                get(test_info, label, value, test=True)
        except Exception:
            invalid.append(label)
    return tuple(invalid)


def migrate_action_list(
    document: ParsedActionDocument, catalog: ActionSchemaCatalog
) -> ActionDocument:
    match document:
        case ActionDocument() as current:
            _validate_catalog_ids(current, catalog)
            return current
        case LegacyActionDocument(description=description, actions=actions):
            migrated: list[ActionSpec] = []
            for action in actions:
                action_id = catalog.action_id(action.label)
                if action_id is None:
                    raise SchemaValidationError(
                        f"unknown legacy action label: {action.label}"
                    )
                fields: list[ActionField] = []
                for label, value in action.fields:
                    field_id = catalog.field_id(action_id, label)
                    if field_id is None:
                        raise SchemaValidationError(
                            f"unknown field label for {action_id}: {label}"
                        )
                    fields.append(ActionField(field_id, value))
                migrated.append(ActionSpec(action_id, tuple(fields)))
            return ActionDocument(SCHEMA_VERSION, description, tuple(migrated))
        case unreachable:
            assert_never(unreachable)


def serialize_action_list(document: ActionDocument) -> str:
    payload = {
        "schema_version": document.schema_version,
        "description": document.description,
        "actions": [
            {
                "id": action.action_id,
                "fields": {field.field_id: field.value for field in action.fields},
            }
            for action in document.actions
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _validate_catalog_ids(
    document: ActionDocument, catalog: ActionSchemaCatalog
) -> None:
    for action in document.actions:
        if catalog.action_label(action.action_id) is None:
            raise SchemaValidationError(f"unknown action ID: {action.action_id}")
        for field in action.fields:
            if catalog.field_label(action.action_id, field.field_id) is None:
                raise SchemaValidationError(
                    f"unknown field ID for {action.action_id}: {field.field_id}"
                )
