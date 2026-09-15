from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageChops

from phatch import actions
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.services.action_schema import RegistrySchemaCatalog
from phatch.services.preview_types import PreviewAdmissionError, PreviewErrorCode
from tests.unit.core.test_preview_conditional_parity import preview_action


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
def catalog_pair() -> tuple[ImmutableActionRegistry, RegistrySchemaCatalog]:
    return build_production_catalog()


def _transparent_source(path: Path) -> None:
    with Image.new("RGBA", (32, 24), (0, 0, 0, 0)) as image:
        image.save(path)


def _mark(path: Path) -> None:
    with Image.new("RGBA", (3, 2), (220, 20, 30, 255)) as image:
        image.save(path)


def test_background_color_and_image_modes_have_known_pixels(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "transparent.png"
    mark = tmp_path / "mark.png"
    _transparent_source(source)
    _mark(mark)

    color = preview_action(
        source,
        catalog_pair,
        "background",
        (("fill", "Color"), ("color", "#123456"), ("opacity", "100")),
    )
    image = preview_action(
        source,
        catalog_pair,
        "background",
        (("fill", "Image"), ("mark", str(mark)), ("method", "Tile")),
        (mark,),
    )

    assert color.size == image.size == (32, 24)
    assert color.getpixel((0, 0)) == (18, 52, 86)
    assert image.getpixel((0, 0)) == (220, 20, 30, 255)
    assert image.getpixel((31, 23)) == (220, 20, 30, 255)


def test_background_image_mode_rejects_an_undeclared_mark(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "transparent.png"
    mark = tmp_path / "mark.png"
    _transparent_source(source)
    _mark(mark)

    with pytest.raises(PreviewAdmissionError) as captured:
        preview_action(
            source,
            catalog_pair,
            "background",
            (("fill", "Image"), ("mark", str(mark))),
        )

    assert captured.value.code is PreviewErrorCode.UNDECLARED_READ


@pytest.mark.parametrize(
    ("method", "fields", "expected_bounds"),
    [
        ("Tile", (), (0, 0, 32, 24)),
        ("Scale", (), (0, 1, 32, 22)),
        (
            "By Offset",
            (
                ("position", "Custom"),
                ("horizontal_offset", "25%"),
                ("vertical_offset", "50%"),
                ("horizontal_justification", "Left"),
                ("vertical_justification", "Top"),
            ),
            (8, 12, 11, 14),
        ),
    ],
)
def test_watermark_methods_match_known_mark_bounds(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    method: str,
    fields: tuple[tuple[str, str], ...],
    expected_bounds: tuple[int, int, int, int],
) -> None:
    source = tmp_path / f"watermark-{method}.png"
    mark = tmp_path / "mark.png"
    _transparent_source(source)
    _mark(mark)

    preview = preview_action(
        source,
        catalog_pair,
        "watermark",
        (("mark", str(mark)), ("method", method), *fields),
        (mark,),
    )

    assert preview.getchannel("A").getbbox() == expected_bounds


@pytest.mark.parametrize(
    ("position", "expected_bounds"),
    [
        ("Center", (14, 11, 17, 13)),
        ("Bottom Left", (3, 20, 6, 22)),
        ("Bottom Right", (26, 20, 29, 22)),
        ("Top Left", (3, 2, 6, 4)),
        ("Top Right", (26, 2, 29, 4)),
    ],
)
def test_watermark_position_presets_apply_percent_offsets(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    position: str,
    expected_bounds: tuple[int, int, int, int],
) -> None:
    source = tmp_path / f"watermark-{position}.png"
    mark = tmp_path / "mark.png"
    _transparent_source(source)
    _mark(mark)

    preview = preview_action(
        source,
        catalog_pair,
        "watermark",
        (
            ("mark", str(mark)),
            ("method", "By Offset"),
            ("position", position),
            ("offset", "10%"),
        ),
        (mark,),
    )

    assert preview.getchannel("A").getbbox() == expected_bounds


def test_text_packaged_font_source_expression_and_custom_pixels(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "known-source.png"
    with Image.new("RGB", (40, 24), "white") as image:
        image.save(source)

    preview = preview_action(
        source,
        catalog_pair,
        "text",
        (
            ("text", "<filename>"),
            ("font", "Free Sans"),
            ("size", "8px"),
            ("color", "#000000"),
            ("position", "Custom"),
            ("horizontal_offset", "25%"),
            ("vertical_offset", "50%"),
            ("horizontal_justification", "Left"),
            ("vertical_justification", "Top"),
        ),
    )

    with Image.new("RGB", preview.size, "white") as background:
        bounds = ImageChops.difference(preview.convert("RGB"), background).getbbox()
    assert preview.size == (40, 24)
    assert bounds == (10, 14, 40, 21)
