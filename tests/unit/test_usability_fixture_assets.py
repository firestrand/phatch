from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from PIL import Image

_FIXTURE_HASHES = (
    "59eb093a0909bb0e649564a0eb69950a7b05131876d890cfe4ec83112222978f",
    "0fe5711b92aef9d6e8de2afeb834351c1bee9e72b3411f244a583722306ebb98",
    "a60c16c4a1fefefbd8372e0ed7637ca6a213d2f25084f7e3a429fbfaad5c768c",
    "7bef35b4a16d471bd8b55dec08dcf9a67a7a5ea275dd9a4353615e41c3c216e4",
)


def test_checked_assets_have_independent_hash_pixel_and_exif_contracts(
    project_root: Path,
) -> None:
    # Given
    root = project_root / "tests" / "fixtures" / "usability"
    paths = tuple(root / name for name in ("rgb.png", "rgba.png", "oriented.png"))

    # When
    hashes = tuple(
        sha256(path.read_bytes()).hexdigest() for path in (*paths, root / "corrupt.img")
    )
    with Image.open(paths[0]) as rgb_image:
        rgb = (rgb_image.mode, rgb_image.size, list(rgb_image.getdata()))
    with Image.open(paths[1]) as rgba_image:
        rgba = (rgba_image.mode, rgba_image.size, list(rgba_image.getdata()))
    with Image.open(paths[2]) as oriented_image:
        oriented = (
            oriented_image.mode,
            oriented_image.size,
            oriented_image.getexif()[274],
            list(oriented_image.getdata()),
        )

    # Then
    assert hashes == _FIXTURE_HASHES
    assert rgb == (
        "RGB",
        (3, 2),
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
            (0, 255, 255),
            (255, 0, 255),
        ],
    )
    assert rgba == (
        "RGBA",
        (2, 2),
        [(10, 20, 30, 0), (40, 50, 60, 64), (70, 80, 90, 128), (100, 110, 120, 255)],
    )
    assert oriented == (
        "RGB",
        (3, 2),
        6,
        [(1, 2, 3), (4, 5, 6), (7, 8, 9), (10, 11, 12), (13, 14, 15), (16, 17, 18)],
    )
