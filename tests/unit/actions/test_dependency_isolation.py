import ast
import importlib
import inspect
import random
import sys
from pathlib import Path

from phatch.actions import imagemagick
from phatch.core import models
from phatch.external_tools import ExternalTools
from phatch.lib.capabilities import (
    Capability,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.lib.external_capability_probes import (
    BLENDER_LEGACY,
    EXIFTRAN,
    IMAGEMAGICK_6,
    JPEGTRAN,
)

ACTION_ROOT = Path(__file__).parents[3] / "phatch" / "actions"
SHUFFLE_SEED = 628_318


class NeverRunner:
    def run(self, command, *, cancelled=None):
        raise AssertionError("runner must not run while initializing actions")


def _external_tools():
    identifiers = (IMAGEMAGICK_6, JPEGTRAN, EXIFTRAN, BLENDER_LEGACY)
    return ExternalTools(
        runner=NeverRunner(),
        probes=tuple(
            (
                identifier,
                lambda identifier=identifier: Capability(
                    identifier,
                    CapabilityStatus.AVAILABLE,
                    CapabilityReasonCode.AVAILABLE,
                    "test capability",
                    executable=Path(f"/{identifier}"),
                ),
            )
            for identifier in identifiers
        ),
    )


def _built_in_action_modules():
    modules = []
    for source in ACTION_ROOT.glob("*.py"):
        if source.name.startswith("_") or source.name in {"__init__.py", "actions.py"}:
            continue
        tree = ast.parse(source.read_text(encoding="utf-8"))
        if any(
            isinstance(node, ast.ClassDef) and node.name == "Action"
            for node in tree.body
        ):
            modules.append((source, f"phatch.actions.{source.stem}"))
    return modules


def test_action_instances_own_mutable_configuration():
    first = imagemagick.Action()
    second = imagemagick.Action()

    first.tags.append("first-only")
    first.tags_hidden.append("first-only")
    first.metadata.append("first-only")
    first.exe["first-only"] = "/tmp/first-only"

    assert "first-only" not in second.tags
    assert "first-only" not in second.tags_hidden
    assert "first-only" not in second.metadata
    assert "first-only" not in second.exe


def test_action_base_does_not_clobber_initialized_instance_configuration():
    class ConfiguredAction(models.Action):
        def __init__(self):
            self.tags = ["configured"]
            self.metadata = ["configured"]
            super().__init__()

    action = ConfiguredAction()

    assert action.tags == ["configured"]
    assert action.metadata == ["configured"]


def test_built_in_actions_initialize_in_seeded_shuffled_order():
    action_modules = _built_in_action_modules()
    random.Random(SHUFFLE_SEED).shuffle(action_modules)
    tools = _external_tools()

    for _source, module_name in action_modules:
        module = importlib.import_module(module_name)
        first = module.Action()
        second = module.Action()
        if module_name == "phatch.actions.geek":
            first.set_field("Command", sys.executable)
            second.set_field("Command", sys.executable)
        parameters = inspect.signature(first.init).parameters
        if "tools" in parameters:
            first.init(tools=tools)
            second.init(tools=tools)
        else:
            first.init()
            second.init()

        assert first is not second
        assert first._fields is not second._fields
        assert first.tags is not second.tags
        assert first.tags_hidden is not second.tags_hidden
        assert first.metadata is not second.metadata
        assert first.exe is not second.exe


def test_built_in_actions_do_not_rebind_lazy_dependencies():
    violations = []
    for source, _module_name in _built_in_action_modules():
        tree = ast.parse(source.read_text(encoding="utf-8"))
        if any(isinstance(node, ast.Global) for node in ast.walk(tree)):
            violations.append(source.name)
        if any(
            isinstance(node, ast.arg) and node.arg == "_inject_deps"
            for node in ast.walk(tree)
        ):
            violations.append(source.name)

    assert violations == []


def test_imagemagick_preserves_injected_external_tools_identity():
    tools = _external_tools()
    first = imagemagick.Action()
    second = imagemagick.Action()

    first.init(tools=tools)
    second.init(tools=tools)

    assert first._external_tools is tools
    assert second._external_tools is tools
