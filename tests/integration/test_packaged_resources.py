from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from phatch import release_inventory
from phatch.resources.inventory import RESOURCE_CLASSES, ResourceClass
from phatch.resources.provider import ResourceProvider

EXPECTED_COUNTS = {
    ResourceClass.ACTION_LISTS: 25,
    ResourceClass.BLENDER: 105,
    ResourceClass.DOCUMENTATION: 360,
    ResourceClass.FONTS: 2,
    ResourceClass.HIGHLIGHTS: 22,
    ResourceClass.IMAGES: 38,
    ResourceClass.LOCALES: 50,
    ResourceClass.MASKS: 40,
    ResourceClass.PERSPECTIVE: 15,
}

STARTER_RESOURCES = {
    "data/actionlists/crop_scale.phatch",
    "data/actionlists/metadata_preserving_export.phatch",
    "data/actionlists/resize.phatch",
    "data/actionlists/watermark.phatch",
    "data/actionlists/watermark.png",
    "data/actionlists/web_size_export.phatch",
}


@pytest.fixture(scope="module")
def built_distributions(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("runtime distribution inventory")
    output = root / "dist"
    project_root = Path(__file__).parents[2]
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", output],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return next(output.glob("*.tar.gz")), next(output.glob("*.whl"))


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


def test_macos_application_icon_has_valid_high_resolution_pixels() -> None:
    # Given: the packaged artwork selected for native macOS application branding
    payload = ResourceProvider().read_bytes("images/icons/256x256/phatch.png")

    # When: Pillow decodes the complete image payload
    with Image.open(BytesIO(payload)) as image:
        image.load()

        # Then: the asset is a non-empty, high-resolution RGBA PNG
        assert image.format == "PNG"
        assert image.size == (256, 256)
        assert image.mode == "RGBA"
        assert image.getbbox() is not None


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


def test_runtime_inventory_imports_modules_and_reads_starter_resources() -> None:
    # Given: the package's explicit 0.5 runtime inventory contract
    collect_runtime_inventory = getattr(
        release_inventory, "collect_runtime_inventory", None
    )

    # When: the source runtime is inventoried through real imports and reads
    assert collect_runtime_inventory is not None
    inventory = collect_runtime_inventory()

    # Then: every registered module imported and every starter asset was read
    assert set(inventory.modules) == set(release_inventory.REQUIRED_RUNTIME_MODULES)
    assert {resource.path for resource in inventory.resources} == STARTER_RESOURCES
    assert all(
        resource.size > 0 and len(resource.sha256) == 64
        for resource in inventory.resources
    )
    assert dict(inventory.resource_counts)[ResourceClass.ACTION_LISTS.value] == 25


def test_runtime_inventory_script_reports_deterministic_json(tmp_path: Path) -> None:
    # Given: execution outside the checkout through the current interpreter
    script = Path(__file__).parents[2] / "scripts" / "runtime_inventory.py"

    # When: the runtime inventory command reads the installed/source package
    completed = subprocess.run(
        [sys.executable, script, "--json"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    # Then: it emits the complete machine-readable inventory
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["modules"] == sorted(release_inventory.REQUIRED_RUNTIME_MODULES)
    assert {item["path"] for item in payload["resources"]} == STARTER_RESOURCES
    assert payload["resource_counts"][ResourceClass.ACTION_LISTS.value] == 25


@pytest.mark.slow
def test_built_sdist_and_wheel_contain_runtime_inventory_contract(
    built_distributions: tuple[Path, Path],
) -> None:
    # Given: source and wheel artifacts built from the current tree
    source_distribution, wheel = built_distributions

    # When: artifact members are inspected directly
    with tarfile.open(source_distribution, "r:gz") as archive:
        source_members = {member.name for member in archive.getmembers()}
    with zipfile.ZipFile(wheel) as archive:
        wheel_members = set(archive.namelist())

    # Then: the sdist carries the probe and the wheel carries its full contract
    assert any(
        name.endswith("/scripts/runtime_inventory.py") for name in source_members
    )
    assert {
        module.replace(".", "/") + ".py"
        for module in release_inventory.REQUIRED_RUNTIME_MODULES
    } <= wheel_members
    assert {f"phatch_assets/{path}" for path in STARTER_RESOURCES} <= wheel_members


@pytest.mark.slow
def test_wheel_package_import_does_not_shadow_spawned_package(
    built_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: an extracted wheel imported outside the checkout
    _, wheel = built_distributions
    extracted = tmp_path / "spawn-safe wheel"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(extracted)
    work = tmp_path / "spawned interpreter"
    work.mkdir()
    environment = {**os.environ, "PYTHONPATH": str(extracted)}
    command = (
        "import phatch, sys; "
        "from pathlib import Path; "
        "package_dir = str(Path(phatch.__file__).parent); "
        "assert sys.path.index(str(Path(phatch.__file__).parent.parent)) "
        "< sys.path.index(package_dir), sys.path"
    )

    # When: a fresh interpreter imports the installed package
    completed = subprocess.run(
        [sys.executable, "-c", command],
        cwd=work,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=30,
    )

    # Then: child imports cannot resolve phatch.py as a top-level package shadow
    assert completed.returncode == 0, completed.stderr


@pytest.mark.slow
def test_runtime_probe_fails_for_wheel_with_omitted_preview_module(
    built_distributions: tuple[Path, Path], tmp_path: Path
) -> None:
    # Given: a built wheel extracted without one registered runtime module
    _, wheel = built_distributions
    extracted = tmp_path / "omitted wheel"
    with zipfile.ZipFile(wheel) as archive:
        archive.extractall(extracted)
    omitted = "phatch/services/preview_worker.py"
    (extracted / omitted).unlink()
    work = tmp_path / "outside checkout"
    work.mkdir()
    environment = {**os.environ, "PYTHONPATH": str(extracted)}
    script = Path(__file__).parents[2] / "scripts" / "runtime_inventory.py"

    # When: the executable runtime probe imports the deliberately incomplete wheel
    completed = subprocess.run(
        [sys.executable, script, "--json"],
        cwd=work,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=30,
    )

    # Then: runtime import failure is reported instead of inventory-only success
    assert completed.returncode == 1
    assert "phatch.services.preview_worker" in completed.stderr
