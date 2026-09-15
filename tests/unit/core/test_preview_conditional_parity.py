from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from phatch import actions
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.core.user_paths import HostPlatform
from phatch.resources.provider import ResourceProvider
from phatch.services.action_schema import RegistrySchemaCatalog
from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview import admit_preview, run_preview
from phatch.services.preview_types import (
    PreviewDependencies,
    PreviewRequest,
    PreviewWorkerSuccess,
)
from tests.unit.core.test_preview_worker_matrix import serial_pixels


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


def pattern_source(path: Path) -> None:
    with Image.new("RGBA", (32, 24)) as image:
        for vertical in range(image.height):
            for horizontal in range(image.width):
                image.putpixel(
                    (horizontal, vertical),
                    (
                        horizontal * 7 % 256,
                        vertical * 11 % 256,
                        (horizontal + vertical) * 5 % 256,
                        255,
                    ),
                )
        image.save(path)


def preview_action(
    source: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    action_id: str,
    fields: tuple[tuple[str, str], ...],
    selected_files: tuple[Path, ...] = (),
) -> Image.Image:
    registry, catalog = catalog_pair
    request = PreviewRequest(
        ActionDocument.from_values("", ((action_id, fields),)),
        source,
        selected_files,
    )
    spec = admit_preview(
        request,
        PreviewDependencies(
            catalog_factory=lambda: catalog,
            resources=ResourceProvider(),
            platform=HostPlatform.MACOS,
        ),
    )

    result = run_preview(spec, f"conditional-{action_id}")

    assert isinstance(result, PreviewWorkerSuccess), result
    expected_mode, expected_size, expected_pixels = serial_pixels(
        registry, catalog, spec, source
    )
    with Image.open(io.BytesIO(result.image.data)) as preview:
        assert (preview.mode, preview.size, preview.tobytes()) == (
            expected_mode,
            expected_size,
            expected_pixels,
        )
        return preview.copy()


@pytest.mark.parametrize(
    ("action_id", "fields", "expected_size"),
    [
        (
            "border",
            (
                ("method", "Different for each side"),
                ("left", "10%"),
                ("right", "2px"),
                ("top", "25%"),
                ("bottom", "1px"),
            ),
            (37, 31),
        ),
        ("crop", (("mode", "All"), ("all", "10%")), (26, 18)),
        (
            "crop",
            (
                ("mode", "Custom"),
                ("left", "25%"),
                ("right", "2px"),
                ("top", "25%"),
                ("bottom", "1px"),
            ),
            (22, 17),
        ),
        (
            "grid",
            (
                ("columns", "2"),
                ("rows", "2"),
                ("scale_to_keep_size", "yes"),
                ("column_line_width", "1px"),
                ("row_line_width", "2px"),
                ("line_color", "#ff00ff"),
                ("line_opacity", "100"),
            ),
            (33, 26),
        ),
        (
            "reflection",
            (
                ("depth", "50%"),
                ("gap", "2px"),
                ("scale_reflection", "yes"),
                ("scale_method", "nearest"),
            ),
            (32, 38),
        ),
        (
            "canvas",
            (
                ("canvas_width", "40px"),
                ("canvas_height", "30px"),
                ("align_horizontal", "25"),
                ("align_vertical", "75"),
            ),
            (40, 30),
        ),
        (
            "fit",
            (
                ("canvas_width", "20px"),
                ("canvas_height", "18px"),
                ("resample_image", "automatic"),
            ),
            (20, 18),
        ),
        (
            "scale",
            (
                ("canvas_width", "20px"),
                ("canvas_height", "10px"),
                ("constrain_proportions", "no"),
                ("scale_down_only", "yes"),
            ),
            (20, 10),
        ),
        (
            "shadow",
            (
                ("horizontal_offset", "-4px"),
                ("vertical_offset", "5px"),
                ("border", "2px"),
            ),
            (40, 33),
        ),
        (
            "transpose",
            (("method", "Rotate 90"), ("amount", "100")),
            (24, 32),
        ),
    ],
)
def test_nondefault_geometry_modes_match_production_and_known_dimensions(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    action_id: str,
    fields: tuple[tuple[str, str], ...],
    expected_size: tuple[int, int],
) -> None:
    source = tmp_path / f"{action_id}.png"
    pattern_source(source)

    preview = preview_action(source, catalog_pair, action_id, fields)

    assert preview.size == expected_size


def test_auto_crop_matches_known_content_bounds(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "auto-crop.png"
    with Image.new("RGBA", (32, 24), (0, 0, 0, 0)) as image:
        ImageDraw.Draw(image).rectangle((5, 4, 26, 19), fill="navy")
        image.save(source)

    preview = preview_action(source, catalog_pair, "crop", (("mode", "Auto"),))

    assert preview.size == (22, 16)


@pytest.mark.parametrize(
    ("selection", "pixel"),
    [
        ("Value", (7, 9)),
        ("Top Left", (0, 0)),
        ("Top Right", (31, 0)),
        ("Bottom Left", (0, 23)),
        ("Bottom Right", (31, 23)),
    ],
)
def test_color_selection_modes_zero_the_independently_selected_pixel(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    selection: str,
    pixel: tuple[int, int],
) -> None:
    source = tmp_path / f"color-{selection}.png"
    pattern_source(source)
    with Image.open(source) as image:
        selected = image.getpixel(pixel)
    fields = (("select_color_by", selection),)
    if selection == "Value":
        fields += (("color_value", "#316350"),)

    preview = preview_action(source, catalog_pair, "color_to_alpha", fields)

    assert preview.size == (32, 24)
    assert preview.getchannel("A").getpixel(pixel) == 0
    if selection == "Value":
        assert selected[:3] == (49, 99, 80)


def test_independent_corner_modes_produce_expected_alpha_mask(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "round.png"
    pattern_source(source)
    fields = (
        ("radius", "6px"),
        ("same_method_for_all_corners", "no"),
        ("top_left_corner", "Square"),
        ("top_right_corner", "Cross"),
        ("bottom_left_corner", "Rounded"),
        ("bottom_right_corner", "Square"),
    )

    preview = preview_action(source, catalog_pair, "round", fields)

    assert preview.size == (32, 24)
    alpha = preview.getchannel("A")
    corner_alpha = tuple(
        alpha.getpixel(point) for point in ((0, 0), (31, 0), (0, 23), (31, 23))
    )
    assert corner_alpha == (255, 0, 1, 255)
