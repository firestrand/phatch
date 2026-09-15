from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest

from phatch import actions
from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildSuccess,
    ImmutableActionRegistry,
    build_action_registry,
)
from phatch.services.action_schema import RegistrySchemaCatalog
from tests.unit.core.test_preview_conditional_parity import (
    pattern_source,
    preview_action,
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
def catalog_pair() -> tuple[ImmutableActionRegistry, RegistrySchemaCatalog]:
    return build_production_catalog()


PRESET_PIXEL_HASHES = {
    "Top": "e791c1bfdd96d54910596ee87ec820f27aae76e63ea3d1b03ca3f161a1b67883",
    "Top Stretched": "f1742bc4059635f51b5934e78c24d0e4ab5d20e082593dcac5d365b81e44f53c",
    "Bottom": "41747f04be241d0f019d64423acdbf2a0aaebb22e2e91bdb76f50b5f7049b049",
    "Bottom Stretched": (
        "11b24c6e3530d8510925e3673529bcecc7b539fa317c802382c03d128d42cd11"
    ),
    "Left": "0bb7a2a54b8eb98ddb33e975ee5c5e6a5659932b8b6277cf645a5911e31e265a",
    "Left Stretched": (
        "a12a26c95fc1be9fa62df6f9a9d170df7c27bd2425b4ed23ddb977480cb0796a"
    ),
    "Right": "21131dfedd458535f7d0c843f1fdc00e7e85370991c21421c1be92b51ddf3daf",
    "Right Stretched": (
        "03a9c29a4330c09e85e7e245ca67fce47e0eea89a205c14615f682c54e929dc4"
    ),
    "Corner Top Left": (
        "71cd2c22f3175bd56d1715022a224667e1a831e265e4ff006e162c1e5cac608e"
    ),
    "Corner Top Right": (
        "2dfa7f1480feb6a8397ba849071f15bda8da243efb30618f75fe6e16061cebc6"
    ),
    "Corner Bottom Left": (
        "915a70c79f753e2ee6248ed53a68d69e5230f10edf6a0ace721a0b2de8568d87"
    ),
    "Corner Bottom Right": (
        "bbff635d37f5eb0dc6106c768bdf31939ca7bf768e5463aa2dbeb2de46031a7c"
    ),
}


@pytest.mark.parametrize(("projection", "expected_hash"), PRESET_PIXEL_HASHES.items())
def test_every_perspective_preset_matches_known_pixels(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
    projection: str,
    expected_hash: str,
) -> None:
    source = tmp_path / f"{projection}.png"
    pattern_source(source)

    preview = preview_action(
        source,
        catalog_pair,
        "perspective",
        (("projection", projection), ("auto_crop", "no")),
    )

    assert preview.size == (32, 24)
    assert sha256(preview.tobytes()).hexdigest() == expected_hash


def test_perspective_user_mode_honors_nondefault_custom_fields(
    tmp_path: Path,
    catalog_pair: tuple[ImmutableActionRegistry, RegistrySchemaCatalog],
) -> None:
    source = tmp_path / "user.png"
    pattern_source(source)
    fields = (
        ("projection", "User"),
        ("scale", "80"),
        ("left_shear_angle", "10"),
        ("top_shear_angle", "-5"),
        ("bottom_shear_factor", "20"),
        ("right_shear_factor", "-10"),
        ("horizontal_offset", "7px"),
        ("vertical_offset", "3px"),
        ("transpose", "None"),
        ("auto_crop", "no"),
    )

    preview = preview_action(
        source,
        catalog_pair,
        "perspective",
        fields,
    )

    assert preview.mode == "RGBA"
    assert preview.size == (32, 24)
    assert sha256(preview.tobytes()).hexdigest() == (
        "91fd5df4c96d2feaae0487237dc3abf1ee21ebff638f01cec75212c28ea7176a"
    )
