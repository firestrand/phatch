from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "phatch.core.action_registry",
        "phatch.core.execution_types",
        "phatch.core.execution_ports",
    ],
)
def test_execution_boundary_imports_exclude_legacy_and_gui_modules(
    module_name: str,
) -> None:
    script = """
import importlib
import sys

before = set(sys.modules)
importlib.import_module(sys.argv[1])
delta = set(sys.modules) - before
forbidden = ("phatch.core.api", "phatch.core.pil", "phatch.pyWx", "PIL", "wx")
blocked = sorted(
    name
    for name in delta
    if any(name == prefix or name.startswith(f"{prefix}.") for prefix in forbidden)
)
if blocked:
    raise SystemExit(",".join(blocked))
"""

    completed = subprocess.run(
        [sys.executable, "-c", script, module_name],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
