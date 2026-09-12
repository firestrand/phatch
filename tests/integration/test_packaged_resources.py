from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest

from phatch.resources.inventory import RESOURCE_CLASSES, ResourceClass
from phatch.resources.provider import ResourceProvider

EXPECTED_COUNTS = {
    ResourceClass.ACTION_LISTS: 20,
    ResourceClass.BLENDER: 105,
    ResourceClass.DOCUMENTATION: 360,
    ResourceClass.FONTS: 2,
    ResourceClass.HIGHLIGHTS: 22,
    ResourceClass.IMAGES: 38,
    ResourceClass.LOCALES: 50,
    ResourceClass.MASKS: 40,
    ResourceClass.PERSPECTIVE: 15,
}


@pytest.mark.parametrize("resource_class", tuple(ResourceClass))
def test_every_required_resource_class_is_complete_in_source(
    resource_class: ResourceClass,
) -> None:
    # Given: the complete declared runtime resource inventory
    provider = ResourceProvider()
    root = RESOURCE_CLASSES[resource_class]

    # When: every file in the class is enumerated and read
    resources = provider.walk_files(root)
    hashes = {
        resource.value: hashlib.sha256(provider.read_bytes(resource)).hexdigest()
        for resource in resources
    }

    # Then: the class has its full expected population and valid bytes
    assert len(resources) == EXPECTED_COUNTS[resource_class]
    assert all(hashes.values())


def test_source_resource_paths_are_checkout_independent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: execution from an unrelated path containing spaces and Unicode
    unrelated = tmp_path / "outside checkout 資源"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)

    # When: a source resource is resolved
    payload = ResourceProvider().read_bytes("images/icons/48x48/phatch.png")

    # Then: lookup succeeds without using the current directory
    assert payload.startswith(b"\x89PNG")


def test_resource_import_does_not_import_gui(tmp_path: Path) -> None:
    # Given: a fresh interpreter outside the checkout working directory
    command = (
        "import sys; "
        "from phatch.resources.provider import ResourceProvider; "
        "assert ResourceProvider; "
        "assert 'wx' not in sys.modules; "
        "assert 'phatch.pyWx.gui' not in sys.modules"
    )

    # When: only the resource provider is imported
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    # Then: resource imports remain GUI-independent
    assert completed.returncode == 0, completed.stderr
