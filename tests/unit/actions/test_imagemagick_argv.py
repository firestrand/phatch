from __future__ import annotations

from pathlib import Path

import pytest

from phatch.actions._imagemagick_argv import build_argv
from phatch.lib.image_process import ImageProcessPaths

PATHS = ImageProcessPaths(
    Path("/private"), Path("/private/input.tif"), Path("/private/output.png")
)
VALUES = {
    "blur_radius": 4,
    "blur_sigma": 2,
    "blur_angle": 120,
    "border": 5,
    "blur1": 2,
    "shade": "120x30",
    "blur2": 1,
    "color": "rgb(1, 2, 3);$&%()",
    "charcoal_radius": 3,
    "sketch_radius": 1,
    "sketch_sigma": 6,
    "sketch_angle": 90,
    "paint_radius": 7,
    "caption": "literal '$HOME'; & (caption) %s",
    "border_color": "#ffffff",
    "shadow_color": "#000000",
    "horizontal_offset": 8,
    "vertical_offset": 9,
    "sharpen_radius": 1,
    "sharpen_sigma": 2,
    "contrast_factor": 2.5,
    "contrast_treshold": 50,
    "unsharp_radius": 3,
    "unsharp_sigma": 4,
    "wave_height": 5,
    "wave_length": 6,
}


@pytest.mark.parametrize(
    ("effect", "middle"),
    [
        (
            "3D Edge",
            (
                "-fx",
                "A",
                "+matte",
                "-blur",
                "0x6",
                "-shade",
                "110x30",
                "-normalize",
                "/private/input.tif",
                "-compose",
                "Overlay",
                "-composite",
                "/private/input.tif",
                "-matte",
                "-compose",
                "Dst_In",
                "-composite",
            ),
        ),
        ("Blur", ("-blur", "4x2")),
        (
            "Bullet",
            (
                "-matte",
                "(",
                "+clone",
                "-channel",
                "A",
                "-separate",
                "+channel",
                "-negate",
                "-bordercolor",
                "black",
                "-border",
                "5",
                "-blur",
                "0x2",
                "-shade",
                "120x30",
                "-normalize",
                "-blur",
                "0x1",
                "-fill",
                "rgb(1, 2, 3);$&%()",
                "-tint",
                "100",
                ")",
                "-gravity",
                "center",
                "-compose",
                "Atop",
                "-composite",
            ),
        ),
        ("Charcoal", ("-charcoal", "3")),
        ("Motion Blur", ("-motion-blur", "4x2+120")),
        ("Pencil Sketch", ("-colorspace", "gray", "-sketch", "1x6+90")),
        ("Paint", ("-paint", "7")),
        (
            "Polaroid",
            (
                "-caption",
                "literal '$HOME'; & (caption) %s",
                "-gravity",
                "center",
                "-bordercolor",
                "#ffffff",
                "-background",
                "#000000",
                "+polaroid",
            ),
        ),
        (
            "Shadow",
            (
                "(",
                "+clone",
                "-background",
                "#000000",
                "-shadow",
                "4x2+8+9",
                ")",
                "+swap",
                "-background",
                "none",
                "-layers",
                "merge",
                "+repage",
            ),
        ),
        ("Sharpen", ("-sharpen", "1x2")),
        ("Sigmoidal Contrast", ("-sigmoidal-contrast", "2.5,50%")),
        ("Unsharp", ("-unsharp", "3x4")),
        ("Wave", ("-wave", "5x6")),
    ],
)
def test_build_argv_preserves_exact_effect_vector(
    effect: str, middle: tuple[str, ...]
) -> None:
    argv = build_argv(effect, Path("/tool path/convert"), PATHS, VALUES)

    if effect == "Polaroid":
        assert argv == (
            "/tool path/convert",
            *middle[:4],
            "/private/input.tif",
            *middle[4:],
            "/private/output.png",
        )
    else:
        assert argv == (
            "/tool path/convert",
            "/private/input.tif",
            *middle,
            "/private/output.png",
        )


def test_polaroid_whitespace_caption_omits_caption_and_gravity() -> None:
    argv = build_argv("Polaroid", Path("convert"), PATHS, {**VALUES, "caption": " \t "})

    assert argv == (
        "convert",
        "/private/input.tif",
        "-bordercolor",
        "#ffffff",
        "-background",
        "#000000",
        "+polaroid",
        "/private/output.png",
    )
