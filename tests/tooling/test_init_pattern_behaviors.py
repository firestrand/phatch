from __future__ import annotations

import ast
import inspect
import subprocess
import sys
from pathlib import Path

from scripts import update_init_pattern

LEGACY_ACTION = """class Action:
    @staticmethod
    def init():
        global sqrt
        # Lazily import the dependency.
        from math import sqrt

    def label(self):
        return "kept"
"""


def test_transform_preserves_class_scope_and_executes_both_dependency_paths() -> None:
    transformed = update_init_pattern.transform_init_function(LEGACY_ACTION)

    assert transformed is not None
    tree = ast.parse(transformed)
    action_node = tree.body[0]
    assert isinstance(action_node, ast.ClassDef)
    function_names = [
        node.name for node in action_node.body if isinstance(node, ast.FunctionDef)
    ]
    assert function_names == [
        "init",
        "label",
    ]

    namespace: dict[str, type] = {}
    exec(compile(tree, "temporary_action.py", "exec"), namespace)
    action_type = namespace["Action"]
    action_init = vars(action_type)["init"]
    sentinel = type("InjectedDependency", (), {})

    assert action_init({"sqrt": sentinel}) == {"sqrt": sentinel}
    assert action_init({}) == {}
    assert action_init()["sqrt"](81) == 9
    assert action_type().label() == "kept"


def test_transform_rejects_sources_without_a_legacy_global_initializer() -> None:
    assert update_init_pattern.transform_init_function("value = 1\n") is None
    assert (
        update_init_pattern.transform_init_function("def init():\n    return None\n")
        is None
    )


def test_extract_global_names_preserves_declaration_order() -> None:
    body = "    global Image, ImageChops\n    global ImageFilter\n"

    assert update_init_pattern.extract_global_names(body) == [
        "Image",
        "ImageChops",
        "ImageFilter",
    ]


def test_main_requires_and_mutates_only_the_explicit_actions_directory(
    tmp_path: Path, capsys
) -> None:
    actions_dir = tmp_path / "actions"
    actions_dir.mkdir()
    target = actions_dir / "resize.py"
    target.write_text(LEGACY_ACTION, encoding="utf-8")
    already_updated = actions_dir / "ready.py"
    already_updated.write_text(
        "def init(_inject_deps=None):\n    return {}\n", encoding="utf-8"
    )
    skipped = actions_dir / "plain.py"
    skipped.write_text("value = 1\n", encoding="utf-8")
    common = actions_dir / "common.py"
    common.write_text(LEGACY_ACTION, encoding="utf-8")

    result = update_init_pattern.main(actions_dir)

    assert result == 0
    assert "def init(_inject_deps=None):" in target.read_text(encoding="utf-8")
    assert already_updated.read_text(encoding="utf-8").startswith(
        "def init(_inject_deps"
    )
    assert skipped.read_text(encoding="utf-8") == "value = 1\n"
    assert common.read_text(encoding="utf-8") == LEGACY_ACTION
    output = capsys.readouterr().out
    assert "1 updated, 2 skipped" in output


def test_main_reports_missing_explicit_directory_without_writing(
    tmp_path: Path, capsys
) -> None:
    missing = tmp_path / "missing"

    result = update_init_pattern.main(missing)

    assert result == 1
    assert str(missing) in capsys.readouterr().err


def test_main_signature_has_no_default_target() -> None:
    actions_dir = inspect.signature(update_init_pattern.main).parameters["actions_dir"]

    assert actions_dir.default is inspect.Parameter.empty


def test_cli_without_explicit_directory_fails_before_transformation(
    project_root: Path,
) -> None:
    script = project_root / "scripts" / "update_init_pattern.py"

    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "actions_dir" in result.stderr
