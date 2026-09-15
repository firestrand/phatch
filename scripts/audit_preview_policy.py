#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run --frozen python scripts/audit_preview_policy.py

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Set
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from phatch.services.action_schema import normalize_identifier
from phatch.services.preview_policy import PREVIEW_POLICIES

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS_ROOT: Final = PROJECT_ROOT / "phatch" / "actions"


@dataclass(frozen=True, slots=True)
class ActionSource:
    action_id: str
    label: str
    source: Path


@dataclass(frozen=True, slots=True)
class PolicyAudit:
    sources: tuple[ActionSource, ...]
    missing_policy_ids: frozenset[str]
    stale_policy_ids: frozenset[str]

    @property
    def covered(self) -> int:
        return len(self.sources) - len(self.missing_policy_ids)

    @property
    def total(self) -> int:
        return len(self.sources)

    @property
    def complete(self) -> bool:
        return not self.missing_policy_ids and not self.stale_policy_ids


@dataclass(frozen=True, slots=True)
class ActionAuditError(ValueError):
    source: Path
    reason: str

    def __str__(self) -> str:
        return f"{self.source}: {self.reason}"


def _literal_label(value: ast.expr) -> str | None:
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if (
        isinstance(value, ast.Call)
        and len(value.args) == 1
        and not value.keywords
        and isinstance(value.args[0], ast.Constant)
        and isinstance(value.args[0].value, str)
    ):
        return value.args[0].value
    return None


def _action_label(tree: ast.Module, source: Path) -> str | None:
    actions = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Action"
    ]
    if not actions:
        return None
    if len(actions) != 1:
        raise ActionAuditError(source, "expected exactly one top-level Action class")
    labels: list[str] = []
    for node in actions[0].body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "label"
            for target in node.targets
        ):
            label = _literal_label(node.value)
            if label is not None:
                labels.append(label)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "label"
            and node.value is not None
        ):
            label = _literal_label(node.value)
            if label is not None:
                labels.append(label)
    if len(labels) != 1:
        raise ActionAuditError(source, "Action.label must be one literal string")
    return labels[0]


def discover_action_sources(actions_root: Path) -> tuple[ActionSource, ...]:
    if not actions_root.is_dir():
        raise ActionAuditError(actions_root, "action source directory does not exist")
    discovered: list[ActionSource] = []
    identifiers: set[str] = set()
    for source in sorted(actions_root.glob("*.py")):
        try:
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        except (OSError, SyntaxError, UnicodeError) as error:
            raise ActionAuditError(
                source, f"could not parse source: {error}"
            ) from error
        label = _action_label(tree, source)
        if label is None:
            continue
        action_id = normalize_identifier(label)
        if action_id in identifiers:
            raise ActionAuditError(source, f"duplicate action ID: {action_id}")
        identifiers.add(action_id)
        discovered.append(ActionSource(action_id, label, source))
    return tuple(sorted(discovered, key=lambda item: item.action_id))


def audit_action_sources(
    actions_root: Path,
    expected_ids: Set[str] | None = None,
) -> PolicyAudit:
    sources = discover_action_sources(actions_root)
    discovered_ids = frozenset(source.action_id for source in sources)
    policy_ids = (
        frozenset(PREVIEW_POLICIES) if expected_ids is None else frozenset(expected_ids)
    )
    return PolicyAudit(
        sources,
        discovered_ids - policy_ids,
        policy_ids - discovered_ids,
    )


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the static built-in action inventory against preview policy."
    )
    parser.add_argument(
        "--actions-root",
        type=Path,
        default=DEFAULT_ACTIONS_ROOT,
        help="directory containing built-in action source files",
    )
    options = parser.parse_args(arguments)
    try:
        result = audit_action_sources(options.actions_root)
    except ActionAuditError as error:
        print(error, file=sys.stderr)
        return 2
    for source in result.sources:
        print(f"{source.action_id}: {source.source.name}")
    if result.missing_policy_ids:
        print(
            f"missing policy IDs: {', '.join(sorted(result.missing_policy_ids))}",
            file=sys.stderr,
        )
    if result.stale_policy_ids:
        print(
            f"extra policy IDs: {', '.join(sorted(result.stale_policy_ids))}",
            file=sys.stderr,
        )
    print(f"{result.covered}/{result.total} covered")
    return 0 if result.complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
