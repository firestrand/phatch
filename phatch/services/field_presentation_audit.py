from __future__ import annotations

import ast
import importlib
from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from phatch.lib import formField
from phatch.services.action_schema import normalize_identifier
from phatch.services.field_presentation import (
    FieldPresentation,
    FieldPresentationError,
    describe_action_fields,
    descriptor_keys,
)
from phatch.services.field_presentation_data import ACTION_FIELD_LABELS


@dataclass(frozen=True, slots=True)
class FieldPresentationAudit:
    descriptors: Mapping[tuple[str, str], FieldPresentation]
    action_count: int
    field_count: int
    field_classes: frozenset[str]
    missing_descriptor_keys: tuple[tuple[str, str], ...]
    extra_descriptor_keys: tuple[tuple[str, str], ...]
    conditional_sources: frozenset[str]
    conditional_source_count: int
    conditional_action_count: int
    branch_count: int
    uncovered_conditional_fields: tuple[tuple[str, str], ...]
    unvisited_controller_values: tuple[tuple[str, str, str], ...]
    visited_values: Mapping[tuple[str, str], frozenset[str]]
    relevant_sets: Mapping[str, frozenset[tuple[str, ...]]]


@dataclass(frozen=True, slots=True)
class FieldPresentationAuditError(RuntimeError):
    source: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.source}: {self.reason}"


def _literal_action_label(tree: ast.Module, source: Path) -> str | None:
    action_nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Action"
    ]
    if not action_nodes:
        return None
    if len(action_nodes) != 1:
        raise FieldPresentationAuditError(source, "multiple top-level Action classes")
    labels: list[str] = []
    for node in action_nodes[0].body:
        value = None
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name) and target.id == "label"
                for target in node.targets
            )
        ) or (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "label"
        ):
            value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            labels.append(value.value)
        elif (
            isinstance(value, ast.Call)
            and len(value.args) == 1
            and isinstance(value.args[0], ast.Constant)
            and isinstance(value.args[0].value, str)
        ):
            labels.append(value.args[0].value)
    if len(labels) != 1:
        raise FieldPresentationAuditError(source, "Action.label is not one literal")
    return labels[0]


def _source_inventory(actions_root: Path) -> tuple[tuple[str, Path], ...]:
    discovered: list[tuple[str, Path]] = []
    identifiers: set[str] = set()
    for source in sorted(actions_root.glob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeError) as error:
            raise FieldPresentationAuditError(source, str(error)) from error
        label = _literal_action_label(tree, source)
        if label is None:
            continue
        action_id = normalize_identifier(label)
        if action_id in identifiers:
            raise FieldPresentationAuditError(source, f"duplicate ID {action_id}")
        identifiers.add(action_id)
        discovered.append((action_id, source))
    return tuple(discovered)


def _conditional_sources(actions_root: Path) -> frozenset[str]:
    result: set[str] = set()
    for source in actions_root.glob("*.py"):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeError) as error:
            raise FieldPresentationAuditError(source, str(error)) from error
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "get_relevant_field_labels"
            for node in ast.walk(tree)
        ):
            result.add(source.name)
    return frozenset(result)


def _state(action) -> tuple[tuple[str, str], ...]:
    return tuple(
        (label, field.get_as_string())
        for label, field in action._fields.items()
        if field.visible
    )


def _restore(action, state: tuple[tuple[str, str], ...]) -> None:
    for label, value in state:
        action.set_field_as_string(label, value)


def _variants(action, field: formField.Field) -> tuple[str, ...]:
    class_names = {candidate.__name__ for candidate in type(field).__mro__}
    if "BooleanField" in class_names:
        return ("no", "yes")
    if "BlenderObjectField" in class_names:
        return tuple(item.name for item in action._objects)
    if "BlenderRotationField" in class_names:
        return (field.get_as_string(), "User")
    if "PerspectiveField" in class_names:
        module = importlib.import_module(type(action).__module__)
        return (*module.PRESETS, "User")
    choices = getattr(field, "choices", ())
    if not isinstance(choices, (list, tuple)):
        return ()
    return tuple(str(choice) for choice in choices)


def _relevance_signature(action, labels: tuple[str, ...]) -> tuple[str, ...]:
    signature = list(labels)
    command = action._fields.get("Command")
    if command is not None:
        signature.extend(
            (
                f"needs_exe={getattr(command, 'needs_exe', None)}",
                f"needs_in={getattr(command, 'needs_in', None)}",
                f"needs_out={getattr(command, 'needs_out', None)}",
                f"valid_last={getattr(action, 'valid_last', None)}",
            )
        )
    return tuple(signature)


def _explore_relevance(action_id: str, action):
    expected = ACTION_FIELD_LABELS[action_id]
    ids_by_label = {label: field_id for field_id, label in expected}
    initial = _state(action)
    queue = deque((initial,))
    seen_states = {initial}
    signatures: set[tuple[str, ...]] = set()
    relevant_sets: set[tuple[str, ...]] = set()
    covered: set[str] = set()
    discovered_values: dict[str, set[str]] = {}
    visited_values: dict[str, set[str]] = {}
    while queue:
        state = queue.popleft()
        _restore(action, state)
        labels = tuple(action.get_relevant_field_labels())
        field_ids = tuple(ids_by_label[label] for label in labels)
        relevant_sets.add(field_ids)
        covered.update(field_ids)
        signature = _relevance_signature(action, labels)
        signatures.add(signature)
        current = _state(action)
        for label in labels:
            field = action._fields[label]
            variants = _variants(action, field)
            if not variants:
                continue
            field_id = ids_by_label[label]
            discovered_values.setdefault(field_id, set()).update(variants)
            for value in variants:
                visited_values.setdefault(field_id, set()).add(value)
                _restore(action, current)
                action.set_field_as_string(label, value)
                candidate_labels = tuple(action.get_relevant_field_labels())
                candidate_signature = _relevance_signature(action, candidate_labels)
                candidate_state = _state(action)
                is_new_signature = candidate_signature != signature
                if is_new_signature and candidate_state not in seen_states:
                    seen_states.add(candidate_state)
                    queue.append(candidate_state)
    _restore(action, initial)
    unvisited = tuple(
        (action_id, field_id, value)
        for field_id, values in discovered_values.items()
        for value in sorted(values - visited_values.get(field_id, set()))
    )
    visited = {
        (action_id, field_id): frozenset(values)
        for field_id, values in visited_values.items()
    }
    return signatures, relevant_sets, covered, unvisited, visited


@lru_cache(maxsize=4)
def audit_builtin_presentations(actions_root: Path) -> FieldPresentationAudit:
    sources = _source_inventory(actions_root)
    descriptors: dict[tuple[str, str], FieldPresentation] = {}
    field_classes: set[str] = set()
    all_relevant_sets: dict[str, frozenset[tuple[str, ...]]] = {}
    all_visited: dict[tuple[str, str], frozenset[str]] = {}
    uncovered: list[tuple[str, str]] = []
    unvisited: list[tuple[str, str, str]] = []
    branch_count = 0
    conditional_count = 0
    for action_id, source in sources:
        if action_id not in ACTION_FIELD_LABELS:
            raise FieldPresentationError(action_id, "*", "unknown action descriptor")
        module = importlib.import_module(f"phatch.actions.{source.stem}")
        action = module.Action()
        action_descriptors = describe_action_fields(action_id, action._fields)
        for field_id, descriptor in action_descriptors.items():
            descriptors[(action_id, field_id)] = descriptor
        field_classes.update(
            type(field).__name__ for field in action._fields.values() if field.visible
        )
        if not callable(getattr(action, "get_relevant_field_labels", None)):
            continue
        conditional_count += 1
        signatures, relevant_sets, covered, missing_values, visited = (
            _explore_relevance(action_id, action)
        )
        branch_count += len(signatures)
        all_relevant_sets[action_id] = frozenset(relevant_sets)
        all_visited.update(visited)
        unvisited.extend(missing_values)
        uncovered.extend(
            (action_id, field_id)
            for field_id, _label in ACTION_FIELD_LABELS[action_id]
            if field_id not in covered
        )
    static_keys = descriptor_keys()
    conditional_sources = _conditional_sources(actions_root)
    return FieldPresentationAudit(
        MappingProxyType(descriptors),
        len(sources),
        len(descriptors),
        frozenset(field_classes),
        tuple(sorted(descriptors.keys() - static_keys)),
        tuple(sorted(static_keys - descriptors.keys())),
        conditional_sources,
        len(conditional_sources),
        conditional_count,
        branch_count,
        tuple(sorted(uncovered)),
        tuple(sorted(unvisited)),
        MappingProxyType(all_visited),
        MappingProxyType(all_relevant_sets),
    )
