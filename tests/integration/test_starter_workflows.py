from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from PIL import Image

from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import ResourceProvider
from phatch.services.action_list import ActionListService
from phatch.services.action_schema import parse_action_list
from phatch.services.action_schema_types import ActionDocument, LegacyActionDocument
from phatch.services.preview import admit_preview
from phatch.services.preview_types import PackagedPreviewRead, PreviewDependencies
from tests.integration.test_installed_wheel_automation import InstalledPhatch
from tests.unit.core.test_preview_admission import FixtureCatalog, _request

pytest_plugins = ("tests.integration.test_installed_wheel_automation",)


@dataclass(frozen=True, slots=True)
class WorkflowCase:
    resource: str
    output_folder: str
    output_name: str
    expected_size: tuple[int, int]


NEW_RESOURCES = (
    "crop_scale.phatch",
    "watermark.phatch",
    "metadata_preserving_export.phatch",
    "web_size_export.phatch",
)
EXECUTABLE_CASES = (
    WorkflowCase(
        "crop_scale.phatch", "_phatch-crop-scale", "sample-crop-scale.png", (60, 36)
    ),
    WorkflowCase(
        "watermark.phatch",
        "_phatch-watermark",
        "sample-watermarked.png",
        (120, 80),
    ),
    WorkflowCase("web_size_export.phatch", "_phatch-web", "sample-web.png", (96, 64)),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _materialize_installed_resource(
    installed: InstalledPhatch, resource: str, destination: Path
) -> None:
    python = installed.command.parent / "python"
    statement = (
        "from pathlib import Path; "
        "from phatch.resources.provider import ResourceProvider; "
        "Path(__import__('sys').argv[2]).write_bytes("
        "ResourceProvider().read_bytes(__import__('sys').argv[1]))"
    )
    subprocess.run(
        [str(python), "-c", statement, resource, str(destination)],
        cwd=installed.work,
        env=installed.environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _installed_recipe(installed: InstalledPhatch, name: str) -> Path:
    destination = installed.work / name
    _materialize_installed_resource(installed, f"data/actionlists/{name}", destination)
    return destination


def _assert_success_report(completed: subprocess.CompletedProcess[str]) -> None:
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["report_version"] == 2
    assert report["outcome"] == "success"
    assert report["counts"] == {
        "processed": 1,
        "skipped": 0,
        "failed": 0,
        "cancelled": 0,
        "total": 1,
    }
    assert report["files"][0]["outcome"] == "processed"
    assert report["files"][0]["outputs"][0]["survived"] is True


def test_starter_recipe_resources_are_schema_three_and_portable() -> None:
    provider = ResourceProvider()

    for name in NEW_RESOURCES:
        document = parse_action_list(provider.read_text(f"data/actionlists/{name}"))
        assert isinstance(document, ActionDocument)
        assert document.schema_version == 3
        save_actions = tuple(
            action
            for action in document.actions
            if action.action_id in {"save", "save_tags"}
        )
        assert len(save_actions) == 1
        fields = {field.field_id: field.value for field in save_actions[0].fields}
        assert fields["in"].startswith("<folder>/_phatch-")
        assert fields["file_name"].startswith("<filename>-")
        assert not Path(fields["in"]).is_absolute()

    legacy = parse_action_list(provider.read_text("data/actionlists/resize.phatch"))
    assert isinstance(legacy, LegacyActionDocument)
    assert provider.read_bytes("data/actionlists/watermark.png").startswith(b"\x89PNG")


def test_starter_watermark_resolves_as_a_packaged_preview_read(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (10, 8), "blue").save(source)
    dependencies = PreviewDependencies(
        catalog_factory=FixtureCatalog,
        resources=ResourceProvider(),
        platform=HostPlatform.MACOS,
    )

    admitted = admit_preview(
        _request(source, ("watermark", (("mark", "Watermark"),))), dependencies
    )

    assert isinstance(admitted.reads[0], PackagedPreviewRead)
    assert admitted.reads[0].resource.value == "data/actionlists/watermark.png"


@pytest.mark.parametrize(
    ("name", "action_index", "field_label", "value"),
    [
        ("crop_scale.phatch", 0, "All", "8px"),
        ("watermark.phatch", 0, "Opacity", "67"),
        ("metadata_preserving_export.phatch", 0, "File Name", "<filename>-tags"),
        ("web_size_export.phatch", 0, "Canvas Width", "100px"),
    ],
)
def test_action_list_service_edits_saves_and_reloads_starter_raw_values(
    tmp_path: Path,
    initialized_runtime: None,
    name: str,
    action_index: int,
    field_label: str,
    value: str,
) -> None:
    source = ResourceProvider().traversable(f"data/actionlists/{name}")
    loaded = ActionListService(safe_mode_checker=lambda: False).load(str(source))
    loaded.actions[action_index].set_field_as_string(field_label, value)
    saved = tmp_path / name

    ActionListService().save(str(saved), loaded.description, loaded.actions)
    reopened = ActionListService(safe_mode_checker=lambda: False).load(str(saved))

    assert reopened.data["schema_version"] == 3
    assert reopened.actions[action_index].get_field_string(field_label) == value


@pytest.mark.slow
def test_installed_wheel_executes_starter_workflows_without_touching_source(
    installed_phatch: InstalledPhatch,
) -> None:
    source = installed_phatch.work / "sample.png"
    Image.new("RGB", (120, 80), (20, 90, 160)).save(source)
    source_hash = _sha256(source)

    for case in EXECUTABLE_CASES:
        recipe = _installed_recipe(installed_phatch, case.resource)
        completed = installed_phatch.run(
            "--max-workers", "1", "--report-format=json", str(recipe), str(source)
        )
        destination = installed_phatch.work / case.output_folder / case.output_name

        _assert_success_report(completed)
        assert destination.stat().st_size > 0
        assert _sha256(destination) != source_hash
        with Image.open(destination) as output:
            assert output.size == case.expected_size
        assert _sha256(source) == source_hash

    resize = _installed_recipe(installed_phatch, "resize.phatch")
    desktop = Path(installed_phatch.environment["HOME"]) / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    completed = installed_phatch.run(
        "--max-workers", "1", "--report-format=json", str(resize), str(source)
    )
    _assert_success_report(completed)
    with Image.open(desktop / "phatch" / source.name) as output:
        assert output.size == (800, 533)
    assert _sha256(source) == source_hash


@pytest.mark.slow
def test_installed_web_workflow_keeps_existing_output(
    installed_phatch: InstalledPhatch,
) -> None:
    recipe = _installed_recipe(installed_phatch, "web_size_export.phatch")
    source = installed_phatch.work / "conflict.png"
    destination = installed_phatch.work / "_phatch-web" / "conflict-web.png"
    destination.parent.mkdir(exist_ok=True)
    Image.new("RGB", (120, 80), "blue").save(source)
    Image.new("RGB", (8, 8), "red").save(destination)
    existing_hash = _sha256(destination)

    completed = installed_phatch.run(
        "--keep", "--report-format=json", str(recipe), str(source)
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report["report_version"] == 2
    assert report["counts"]["skipped"] == 1
    assert report["files"][0]["outcome"] == "skipped"
    assert _sha256(destination) == existing_hash


@pytest.mark.slow
def test_installed_metadata_workflow_reports_optional_capability_or_preserves_exif(
    installed_phatch: InstalledPhatch,
) -> None:
    recipe = _installed_recipe(installed_phatch, "metadata_preserving_export.phatch")
    source = installed_phatch.work / "metadata.jpg"
    exif = Image.Exif()
    exif[315] = "Phatch starter workflow"
    Image.new("RGB", (40, 30), "green").save(source, exif=exif)
    source_hash = _sha256(source)
    planned = installed_phatch.run(
        "--dry-run", "--report-format=json", str(recipe), str(source)
    )
    preflight = json.loads(planned.stdout)

    if "legacy-metadata" in preflight["unavailable_capabilities"]:
        assert planned.returncode == 3
        assert preflight["outcome"] == "unavailable_capability"
        assert not (installed_phatch.work / "_phatch-metadata").exists()
    else:
        completed = installed_phatch.run(
            "--report-format=json", str(recipe), str(source)
        )
        _assert_success_report(completed)
        output = installed_phatch.work / "_phatch-metadata" / "metadata-metadata.jpg"
        with Image.open(output) as saved:
            assert saved.getexif()[315] == "Phatch starter workflow"
    assert _sha256(source) == source_hash
