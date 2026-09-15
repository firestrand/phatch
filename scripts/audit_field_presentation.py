#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run --frozen python scripts/audit_field_presentation.py

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

from phatch.services.field_presentation import FieldPresentationError
from phatch.services.field_presentation_audit import (
    FieldPresentationAuditError,
    audit_builtin_presentations,
)

PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_ACTIONS_ROOT: Final = PROJECT_ROOT / "phatch" / "actions"


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit built-in runtime fields against presentation descriptors."
    )
    parser.add_argument(
        "--actions-root",
        type=Path,
        default=DEFAULT_ACTIONS_ROOT,
        help="directory containing built-in action source files",
    )
    options = parser.parse_args(arguments)
    try:
        audit = audit_builtin_presentations(options.actions_root)
    except (FieldPresentationAuditError, FieldPresentationError) as error:
        print(error, file=sys.stderr)
        return 2
    for (action_id, field_id), descriptor in sorted(audit.descriptors.items()):
        units = ",".join(descriptor.units) or "-"
        print(
            f"{action_id}.{field_id}: {descriptor.editor.value}; "
            f"preset={descriptor.preset.value}; units={units}; "
            f"basis={descriptor.percentage_basis.value}"
        )
    print(
        f"{audit.action_count} actions, {audit.field_count} fields, "
        f"{audit.conditional_source_count} conditional sources, "
        f"{audit.branch_count} runtime branches; exhaustive"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
