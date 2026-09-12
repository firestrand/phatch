from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Final, TypeAlias

SCHEMA_VERSION: Final = 3
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")
JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


@dataclass(frozen=True, slots=True)
class SchemaValidationError(ValueError):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class ActionField:
    field_id: str
    value: str


@dataclass(frozen=True, slots=True)
class ActionSpec:
    action_id: str
    fields: tuple[ActionField, ...]


@dataclass(frozen=True, slots=True)
class ActionDocument:
    schema_version: int
    description: str
    actions: tuple[ActionSpec, ...]

    @classmethod
    def from_values(
        cls,
        description: str,
        actions: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
    ) -> ActionDocument:
        return cls(
            SCHEMA_VERSION,
            description,
            tuple(
                ActionSpec(
                    action_id,
                    tuple(ActionField(field_id, value) for field_id, value in fields),
                )
                for action_id, fields in actions
            ),
        )


@dataclass(frozen=True, slots=True)
class LegacyActionSpec:
    label: str
    fields: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class LegacyActionDocument:
    format_version: str
    description: str
    actions: tuple[LegacyActionSpec, ...]


ParsedActionDocument: TypeAlias = ActionDocument | LegacyActionDocument


def parse_action_list(source: str) -> ParsedActionDocument:
    try:
        raw = json.loads(source)
    except json.JSONDecodeError:
        try:
            raw = ast.literal_eval(source)
        except (SyntaxError, ValueError) as error:
            raise SchemaValidationError(
                "action list is not valid JSON or legacy literal data"
            ) from error
    if not isinstance(raw, dict):
        raise SchemaValidationError("action list document must be an object")
    if raw.get("schema_version") is not None:
        return _parse_current(raw)
    return _parse_legacy(raw)


def _parse_current(raw: dict[str, JsonValue]) -> ActionDocument:
    _require_keys(raw, {"schema_version", "description", "actions"}, "document")
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise SchemaValidationError("unsupported action-list schema version")
    description = raw.get("description")
    actions = raw.get("actions")
    if not isinstance(description, str) or not isinstance(actions, list):
        raise SchemaValidationError("invalid action-list description or actions")
    return ActionDocument(
        SCHEMA_VERSION,
        description,
        tuple(_parse_current_action(action) for action in actions),
    )


def _parse_current_action(raw: JsonValue) -> ActionSpec:
    if not isinstance(raw, dict):
        raise SchemaValidationError("action must be an object")
    _require_keys(raw, {"id", "fields"}, "action")
    action_id = raw.get("id")
    fields = raw.get("fields")
    if not isinstance(action_id, str) or IDENTIFIER.fullmatch(action_id) is None:
        raise SchemaValidationError("invalid action ID")
    if not isinstance(fields, dict):
        raise SchemaValidationError("action fields must be an object")
    return ActionSpec(
        action_id,
        tuple(
            _parse_current_field(field_id, value) for field_id, value in fields.items()
        ),
    )


def _parse_current_field(field_id: str, value: JsonValue) -> ActionField:
    if IDENTIFIER.fullmatch(field_id) is None or not isinstance(value, str):
        raise SchemaValidationError("field IDs and values must be strings")
    return ActionField(field_id, value)


def _parse_legacy(raw: dict[str, JsonValue]) -> LegacyActionDocument:
    _require_keys(
        raw,
        {"version", "format_version", "description", "actions"},
        "legacy document",
    )
    explicit = raw.get("format_version")
    version = raw.get("version")
    if explicit is None:
        if not isinstance(version, str) or not version.startswith(("0.2", "0.3")):
            raise SchemaValidationError("unsupported legacy action-list version")
        format_version = "1.0"
    else:
        format_version = str(explicit)
        if format_version not in {"1.0", "2.0"}:
            raise SchemaValidationError("unsupported legacy action-list format")
    description = raw.get("description", "")
    actions = raw.get("actions")
    if not isinstance(description, str) or not isinstance(actions, list):
        raise SchemaValidationError("invalid legacy description or actions")
    return LegacyActionDocument(
        format_version,
        description,
        tuple(_parse_legacy_action(action) for action in actions),
    )


def _parse_legacy_action(raw: JsonValue) -> LegacyActionSpec:
    if not isinstance(raw, dict):
        raise SchemaValidationError("legacy action must be an object")
    _require_keys(raw, {"label", "fields"}, "legacy action")
    label = raw.get("label")
    fields = raw.get("fields")
    if not isinstance(label, str) or not isinstance(fields, dict):
        raise SchemaValidationError("invalid legacy action label or fields")
    parsed: list[tuple[str, str]] = []
    for field_label, value in fields.items():
        if not isinstance(value, str):
            raise SchemaValidationError("legacy field values must be strings")
        parsed.append((field_label, value))
    return LegacyActionSpec(label, tuple(parsed))


def _require_keys(raw: dict[str, JsonValue], allowed: set[str], context: str) -> None:
    unknown = set(raw).difference(allowed)
    if unknown:
        raise SchemaValidationError(f"unknown {context} key: {sorted(unknown)[0]}")
