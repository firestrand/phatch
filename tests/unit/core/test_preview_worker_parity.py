from __future__ import annotations

import importlib
import io
from hashlib import sha256
from pathlib import Path

from PIL import Image

from phatch.core import pil
from phatch.lib import metadata
from phatch.services.action_schema import normalize_identifier
from phatch.services.preview import run_preview
from phatch.services.preview_types import (
    PreviewActionSpec,
    PreviewExecutionSpec,
    PreviewLimits,
    PreviewReadContext,
    PreviewSize,
    PreviewSource,
    PreviewWorkerSuccess,
)


def _oriented_source(path: Path) -> None:
    with Image.new("RGB", (40, 20)) as image:
        for y in range(image.height):
            for x in range(image.width):
                image.putpixel((x, y), ((x * 5) % 256, (y * 11) % 256, x + y))
        exif = Image.Exif()
        exif[274] = 6
        image.save(path, quality=100, subsampling=0, exif=exif)


def _spec(path: Path) -> PreviewExecutionSpec:
    with Image.open(path) as image:
        source = PreviewSource(
            path,
            sha256(path.read_bytes()).hexdigest(),
            PreviewSize(*image.size),
            image.mode,
            image.format,
        )
    actions = (
        PreviewActionSpec("crop", (("mode", "All"), ("all", "10%"))),
        PreviewActionSpec(
            "border",
            (("method", "Equal for all sides"), ("border_width", "5%")),
        ),
    )
    return PreviewExecutionSpec(
        actions,
        source,
        (),
        (
            "dpi",
            "filename",
            "format",
            "height",
            "orientation",
            "path",
            "size",
            "type",
            "width",
        ),
        PreviewLimits(),
        PreviewReadContext(source, ()),
        False,
    )


def _serial_production(spec: PreviewExecutionSpec) -> bytes:
    source_path = str(spec.source.path)
    info = metadata.InfoExtract(source_path, vars=pil.BASE_VARS).dump()
    required = metadata.InfoExtract(vars=list(spec.required_variables))
    photo = pil.Photo(info, required)
    settings: dict[str, object] = {}
    cache: dict[str, object] = {}
    try:
        for action_spec in spec.actions:
            module = importlib.import_module(f"phatch.actions.{action_spec.action_id}")
            module.Action.init()
            action = module.Action()
            labels = {normalize_identifier(label): label for label in action._fields}
            action.load({labels[key]: value for key, value in action_spec.fields})
            action.apply(photo, settings, cache)
        image = photo.get_flattened_image()
        try:
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
        finally:
            image.close()
    finally:
        for layer in photo.layers.values():
            if layer.image is not None:
                layer.image.close()
        photo.close()


def test_spawned_oriented_percent_recipe_matches_serial_and_is_deterministic(
    tmp_path: Path,
) -> None:
    source = tmp_path / "oriented.jpg"
    _oriented_source(source)
    spec = _spec(source)
    expected = _serial_production(spec)

    first = run_preview(spec, "oriented-percent-1")
    second = run_preview(spec, "oriented-percent-2")

    assert isinstance(first, PreviewWorkerSuccess)
    assert isinstance(second, PreviewWorkerSuccess)
    assert first.image.data == expected
    assert second.image.data == expected
    assert (first.image.width, first.image.height) == (16, 36)
