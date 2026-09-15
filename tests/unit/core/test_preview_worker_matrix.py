from __future__ import annotations

import io
from contextlib import ExitStack
from pathlib import Path

import pytest
from PIL import Image

from phatch import actions
from phatch.core import pil
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.core.user_paths import HostPlatform
from phatch.lib import metadata
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema import RegistrySchemaCatalog
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview import admit_preview, run_preview
from phatch.services.preview_policy import PREVIEW_POLICIES, PolicyKind
from phatch.services.preview_types import (
    PackagedPreviewRead,
    PreviewDependencies,
    PreviewRequest,
    PreviewWorkerSuccess,
    SelectedPreviewRead,
)

ELIGIBLE_ACTION_IDS = tuple(
    sorted(
        action_id
        for action_id, policy in PREVIEW_POLICIES.items()
        if policy.kind is PolicyKind.ELIGIBLE
    )
)


def build_production_catalog() -> tuple[ImmutableActionRegistry, RegistrySchemaCatalog]:
    package_path = Path(actions.__file__).parent
    result = build_action_registry(
        ActionCatalogSources(
            built_in=tuple(package_path.glob("*.py")),
            user=(),
            built_in_package="phatch.actions",
        )
    )
    assert isinstance(result, ActionRegistryBuildSuccess)
    return result.registry, RegistrySchemaCatalog(result.registry)


@pytest.fixture(scope="module")
def production_catalog() -> tuple[ImmutableActionRegistry, RegistrySchemaCatalog]:
    return build_production_catalog()


def _source(path: Path) -> None:
    with Image.new("RGBA", (32, 24), (40, 80, 120, 180)) as image:
        image.save(path)


def serial_pixels(registry, catalog, spec, source: Path):
    action_spec = spec.actions[0]
    values = dict(action_spec.fields)
    with ExitStack() as resources:
        provider = ResourceProvider()
        for read in spec.reads:
            if isinstance(read, PackagedPreviewRead):
                if action_spec.action_id != "perspective":
                    values[read.field_id] = str(
                        resources.enter_context(provider.as_path(read.resource))
                    )
            elif isinstance(read, SelectedPreviewRead):
                values[read.field_id] = str(read.path)
        loaded = {
            catalog.field_label(action_spec.action_id, field_id): value
            for field_id, value in values.items()
        }
        assert None not in loaded
        action = registry.instantiate(catalog.action_label(action_spec.action_id))
        assert action.load(loaded) == []
        relevant = getattr(action, "get_relevant_field_labels", None)
        if callable(relevant):
            relevant()
        action.init()
        info = metadata.InfoExtract(str(source), vars=pil.BASE_VARS).dump()
        requested = metadata.InfoExtract(vars=list(spec.required_variables))
        photo = pil.Photo(info, requested)
        try:
            action.apply(photo, {}, {})
            image = photo.get_flattened_image()
            try:
                return image.mode, image.size, image.tobytes()
            finally:
                image.close()
        finally:
            for layer in photo.layers.values():
                if layer.image is not None:
                    layer.image.close()
            photo.close()


@pytest.mark.parametrize("action_id", ELIGIBLE_ACTION_IDS)
def test_every_eligible_default_runs_in_one_shot_spawn_without_leaks(
    tmp_path: Path,
    production_catalog: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    action_id: str,
) -> None:
    registry, catalog = production_catalog
    source = tmp_path / f"{action_id}.png"
    _source(source)
    label = catalog.action_label(action_id)
    assert label is not None
    serialized_fields = tuple(
        (field_label, field.get_as_string())
        for field_label, field in registry.fields[label].items()
    )
    fields = tuple(
        (field_id, value)
        for field_label, value in serialized_fields
        if (field_id := catalog.field_id(action_id, field_label)) is not None
    )
    request = PreviewRequest(
        ActionDocument.from_values("", ((action_id, fields),)),
        source,
    )
    dependencies = PreviewDependencies(
        catalog_factory=lambda: catalog,
        resources=ResourceProvider(),
        platform=HostPlatform.MACOS,
    )
    spec = admit_preview(request, dependencies)

    result = run_preview(spec, f"matrix-{action_id}")

    assert isinstance(result, PreviewWorkerSuccess), result
    expected_mode, expected_size, expected_pixels = serial_pixels(
        registry, catalog, spec, source
    )
    with Image.open(io.BytesIO(result.image.data)) as actual:
        assert actual.mode == expected_mode
        assert actual.size == expected_size
        assert actual.tobytes() == expected_pixels
    source.unlink()
    assert not source.exists()


def test_text_source_variables_match_original_admitted_path(
    tmp_path: Path,
    production_catalog: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    registry, catalog = production_catalog
    source = tmp_path / "admitted-original.png"
    with Image.new("RGB", (240, 40), "white") as image:
        image.save(source)
    label = catalog.action_label("text")
    assert label is not None
    serialized_fields = tuple(
        (field_label, field.get_as_string())
        for field_label, field in registry.fields[label].items()
    )
    fields = tuple(
        (field_id, "<path>" if field_id == "text" else value)
        for field_label, value in serialized_fields
        if (field_id := catalog.field_id("text", field_label)) is not None
    )
    request = PreviewRequest(
        ActionDocument.from_values("", (("text", fields),)),
        source,
    )
    dependencies = PreviewDependencies(
        catalog_factory=lambda: catalog,
        resources=ResourceProvider(),
        platform=HostPlatform.MACOS,
    )
    spec = admit_preview(request, dependencies)
    expected_mode, expected_size, expected_pixels = serial_pixels(
        registry, catalog, spec, source
    )

    result = run_preview(spec, "text-source-identity")

    assert isinstance(result, PreviewWorkerSuccess), result
    with Image.open(io.BytesIO(result.image.data)) as actual:
        assert actual.mode == expected_mode
        assert actual.size == expected_size
        assert actual.tobytes() == expected_pixels
