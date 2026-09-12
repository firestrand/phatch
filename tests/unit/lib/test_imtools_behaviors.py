from types import SimpleNamespace
from typing import Any, cast

import pytest
from PIL import Image

from phatch.lib import imtools


@pytest.mark.parametrize(
    ("image_mode", "target_format", "expected_mode"),
    [
        ("RGBA", "JPEG", "RGB"),
        ("LA", "JPEG", "L"),
        ("LA", "BMP", "L"),
        ("CMYK", "BMP", "RGB"),
        ("CMYK", "DIB", "RGB"),
        ("1", "EPS", "L"),
        ("RGBA", "EPS", "RGB"),
        ("RGB", "GIF", "P"),
        ("L", "PBM", "1"),
        ("RGBA", "PCX", "RGB"),
        ("LA", "PCX", "L"),
        ("LA", "PDF", "L"),
        ("RGBA", "PDF", "RGB"),
        ("RGB", "PGM", "L"),
        ("P", "PPM", "RGB"),
        ("LA", "PPM", "L"),
        ("1", "PS", "L"),
        ("RGBA", "PS", "RGB"),
        ("L", "XBM", "1"),
        ("YCbCr", "TIFF", "RGB"),
        ("CMYK", "PNG", "RGB"),
        ("RGB", "PNG", "RGB"),
        ("P", "PNG", "P"),
        ("RGB", "BMP", "RGB"),
        ("RGB", "DIB", "RGB"),
        ("RGB", "EPS", "RGB"),
        ("1", "PBM", "1"),
        ("L", "PCX", "L"),
        ("RGB", "PDF", "RGB"),
        ("L", "PGM", "L"),
        ("RGB", "PPM", "RGB"),
        ("RGB", "PS", "RGB"),
        ("1", "XBM", "1"),
        ("RGB", "TIFF", "RGB"),
    ],
)
def test_convert_save_mode_by_format(
    image_mode: str, target_format: str, expected_mode: str
) -> None:
    image = Image.new(image_mode, (2, 2))

    converted = imtools.convert_save_mode_by_format(image, target_format)

    assert converted.mode == expected_mode
    assert converted is not image


def test_convert_handles_palette_and_transparency_modes() -> None:
    palette = Image.new("P", (2, 2))
    palette.info["transparency"] = 0
    rgba = Image.new("RGBA", (2, 2), (10, 20, 30, 128))

    assert imtools.convert(palette, "P") is palette
    assert imtools.convert(Image.new("1", (2, 2)), "P").mode == "P"
    converted_rgba = imtools.convert(rgba, "P")
    assert converted_rgba.mode == "P"
    assert converted_rgba.info["transparency"] == 255
    assert imtools.convert(palette, "LA").mode == "LA"
    assert imtools.convert(Image.new("RGB", (2, 2)), "L").mode == "L"


def test_palette_helpers_manage_used_transparent_and_new_colors() -> None:
    image = Image.new("P", (2, 1))
    palette = [(index, index, index) for index in range(256)]
    image.putpalette(imtools.flatten(palette))
    image.putdata([0, 1])
    image.info["transparency"] = 0

    assert imtools.get_used_palette_indices(image) == {0, 1}
    assert 2 in imtools.get_unused_palette_indices(image)
    existing_index, unchanged = imtools.fit_color_in_palette(image, (1, 1, 1))
    new_index, changed = imtools.fit_color_in_palette(image, (10, 20, 30))

    assert existing_index == 1
    assert unchanged is not None
    assert new_index not in {0, 1}
    assert changed is not None and changed[new_index] == (10, 20, 30)

    copied = Image.new("P", image.size)
    imtools.put_palette(copied, image)
    assert copied.info["transparency"] == 0


def test_palette_helpers_find_duplicate_after_transparency_and_report_full() -> None:
    duplicate = Image.new("P", (2, 1))
    colors = [(index, index, index) for index in range(256)]
    colors[2] = colors[0]
    duplicate.putpalette(imtools.flatten(colors))
    duplicate.putdata([0, 2])
    duplicate.info["transparency"] = 0

    duplicate_index, palette = imtools.fit_color_in_palette(duplicate, (0, 0, 0))
    assert duplicate_index == 2
    assert palette is not None

    full = Image.new("P", (16, 16))
    full.putpalette(imtools.flatten(colors))
    full.putdata(range(256))
    missing_index, missing_palette = imtools.fit_color_in_palette(full, (1, 2, 3))
    assert missing_index == -1
    assert missing_palette is None


def test_alpha_helpers_cover_opaque_alpha_and_palette_images() -> None:
    rgba = Image.new("RGBA", (2, 2), (1, 2, 3, 128))
    la = Image.new("LA", (2, 2), (4, 64))
    palette = Image.new("P", (2, 2))
    palette.info["transparency"] = 0
    rgb = Image.new("RGB", (2, 2), (1, 2, 3))

    assert imtools.has_alpha(rgba)
    assert imtools.has_transparency(palette)
    assert imtools.get_alpha(rgba).getextrema() == (128, 128)
    assert imtools.get_alpha(palette).getextrema()[0] == 0
    assert imtools.get_alpha(rgb).getextrema() == (255, 255)
    assert imtools.remove_alpha(rgba).mode == "RGB"
    assert imtools.remove_alpha(la).mode == "L"
    assert imtools.remove_alpha(palette).mode == "RGB"
    assert imtools.remove_alpha(rgb) is rgb

    alpha = Image.new("L", (2, 2), 32)
    imtools.put_alpha(rgba, alpha)
    assert imtools.get_alpha(rgba).getextrema() == (32, 32)
    assert imtools.put_alpha(Image.new("F", (2, 2)), alpha) is None


@pytest.mark.parametrize("orientation", range(1, 10))
def test_exif_transposition_round_trips_supported_orientations(
    orientation: int,
) -> None:
    transposition, reverse = imtools.get_exif_transposition(orientation)
    image = Image.new("RGB", (2, 3))

    restored = imtools.transpose(imtools.transpose(image, transposition), reverse)

    assert restored.size == image.size


def test_exif_orientation_and_transpose_fallbacks() -> None:
    assert imtools.get_exif_orientation(SimpleNamespace()) == 1
    assert imtools.get_exif_orientation(SimpleNamespace(_getexif=lambda: None)) == 1
    assert (
        imtools.get_exif_orientation(SimpleNamespace(_getexif=lambda: {0x0112: 6})) == 6
    )
    assert imtools.get_exif_orientation(SimpleNamespace(_getexif=lambda: {})) == 1

    image = Image.new("RGB", (2, 3))
    cast(Any, image)._getexif = lambda: {0x0112: 6}
    assert imtools.transpose_exif(image).size == (3, 2)
    assert imtools.transpose_exif(image, reverse=True).size == (3, 2)


def test_background_and_checkerboard_composition() -> None:
    rgba = Image.new("RGBA", (4, 4), (255, 0, 0, 0))
    opaque = Image.new("RGB", (4, 4), (1, 2, 3))

    assert imtools.fill_background_color(opaque, (4, 5, 6)) is opaque
    filled = imtools.fill_background_color(rgba, (4, 5, 6, 255))
    assert filled.mode == "RGB"
    assert filled.getpixel((0, 0)) == (4, 5, 6)

    first = imtools.checkboard((4, 4), delta=2)
    second = imtools.checkboard((4, 4), delta=2)
    assert first.tobytes() == second.tobytes()
    assert first is not second
    assert imtools.add_checkboard(rgba).mode == "RGB"
    assert imtools.add_checkboard(opaque) is opaque


def test_open_image_supports_data_file_uri_and_remote_cache(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = Image.new("RGB", (2, 2), (10, 20, 30))
    path = tmp_path / "source.png"
    source.save(path)

    with imtools.open_image(f"file://{path}") as opened:
        assert opened.getpixel((0, 0)) == (10, 20, 30)

    payload = path.read_bytes()
    uri = "https://example.invalid/source.png"
    remote_image = Image.new("RGB", (2, 2), (40, 50, 60))
    imtools.WWW_CACHE.pop(uri, None)
    monkeypatch.setattr(imtools.system, "is_www_file", lambda value: value == uri)
    monkeypatch.setattr(
        imtools, "urlopen", lambda _uri: SimpleNamespace(read=lambda: payload)
    )
    monkeypatch.setattr(imtools, "open_image_data", lambda _payload: remote_image)
    first = imtools.open_image(uri)
    second = imtools.open_image(uri)

    assert first is remote_image
    assert second is remote_image


def test_fill_background_color_handles_la_and_palette_transparency() -> None:
    la = Image.new("LA", (2, 2), (100, 128))
    assert imtools.fill_background_color(la, (1, 2, 3)).mode == "RGB"

    palette = Image.new("P", (2, 2), 0)
    palette.putpalette([0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254)
    palette.info["transparency"] = 0
    filled_palette = imtools.fill_background_color(palette, (4, 5, 6))
    assert filled_palette.mode == "P"
    assert "transparency" not in filled_palette.info
    filled_colors = filled_palette.getpalette()
    assert filled_colors is not None
    assert filled_colors[:3] == [4, 5, 6]

    transparent_palette = Image.new("P", (2, 2), 0)
    transparent_palette.info["transparency"] = 0
    rgba = imtools.fill_background_color(transparent_palette, (7, 8, 9, 128))
    assert rgba.mode == "RGBA"


@pytest.mark.parametrize("method", ["Tile", "Scale", "By Offset"])
def test_generate_layer_supports_each_positioning_method(
    method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    mark = Image.new("RGBA", (2, 2), (255, 0, 0, 255))
    monkeypatch.setattr(imtools, "open_image", lambda image: image)

    layer = imtools.generate_layer(
        (6, 4),
        mark,
        method,
        1,
        1,
        "Left",
        "Top",
        "ROTATE_90" if method == "By Offset" else "",
        100,
    )

    assert layer.mode == "RGBA"
    assert layer.size == (6, 4)
    assert layer.getbbox() is not None


def test_generate_layer_rejects_unknown_method(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imtools, "open_image", lambda image: image)

    with pytest.raises(ValueError, match="Unknown method"):
        imtools.generate_layer(
            (2, 2),
            Image.new("RGBA", (1, 1)),
            "Unknown",
            0,
            0,
            "Left",
            "Top",
            "",
            100,
        )


def test_identity_color_and_blend_cover_size_and_color_variants() -> None:
    assert imtools.identity_color(Image.new("L", (1, 1)), 7) == 7
    assert imtools.identity_color(Image.new("RGB", (1, 1)), 7) == (7, 7, 7)

    same_size = imtools.blend(
        Image.new("RGB", (2, 2), "black"),
        Image.new("RGB", (2, 2), "white"),
        0.5,
    )
    assert same_size.getpixel((0, 0)) == (127, 127, 127)


def test_opacity_location_and_safe_mode_edge_cases() -> None:
    image = Image.new("RGBA", (2, 2), (1, 2, 3, 128))
    assert imtools.reduce_opacity(image, -0.1) is image
    assert imtools.reduce_opacity(image, 1.1) is image

    assert imtools.calculate_location(
        -10, -20, "Middle", "Bottom", (100, 80), (20, 10)
    ) == (80.0, 50)
    assert imtools.calculate_location(
        30, 40, "Right", "Middle", (100, 80), (20, 10)
    ) == (10, 35.0)

    assert imtools.convert_safe_mode(Image.new("1", (1, 1))).mode == "L"
    assert imtools.convert_safe_mode(Image.new("CMYK", (1, 1))).mode == "RGB"


def test_save_helpers_verify_modes_and_safe_extension(tmp_path: Any) -> None:
    image = Image.new("RGB", (2, 2), (1, 2, 3))
    gif_path = tmp_path / "mode.gif"
    png_path = tmp_path / "safe.png"

    assert imtools.save_check_mode(image, gif_path, format="GIF") == "P"
    imtools.save_safely(image, png_path)

    with Image.open(png_path) as saved:
        assert saved.mode == "RGB"
        assert saved.getpixel((0, 0)) == (1, 2, 3)


def test_reverse_transposition_maps_rotations_and_preserves_other_values() -> None:
    assert imtools.get_reverse_transposition(Image.ROTATE_90) == Image.ROTATE_270
    assert imtools.get_reverse_transposition(Image.ROTATE_270) == Image.ROTATE_90
    assert (
        imtools.get_reverse_transposition(Image.FLIP_LEFT_RIGHT)
        == Image.FLIP_LEFT_RIGHT
    )


def test_open_image_exif_delegates_open_and_transposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    image = Image.new("RGB", (2, 3))
    monkeypatch.setattr(imtools, "open_image", lambda _uri: image)
    monkeypatch.setattr(
        imtools,
        "transpose_exif",
        lambda opened: opened.transpose(Image.ROTATE_90),
    )

    assert imtools.open_image_exif("source.jpg").size == (3, 2)


def test_save_translates_unknown_format_error(tmp_path: Any) -> None:
    class UnknownFormatImage:
        def save(self, _filename: Any, **_options: Any) -> None:
            raise KeyError("UNKNOWN")

    with pytest.raises(imtools.InvalidWriteFormatError):
        imtools.save(UnknownFormatImage(), tmp_path / "output.unknown")


def test_save_uses_temporary_file_after_unicode_error(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    destinations: list[Any] = []

    class UnicodePathImage:
        def save(self, filename: Any, **_options: Any) -> None:
            if filename == tmp_path / "output.png":
                raise UnicodeEncodeError("ascii", "x", 0, 1, "unsupported")
            destinations.append(filename)

    class TemporaryFile:
        path = tmp_path / "temporary.png"

        def close(self, *, dest: Any) -> None:
            destinations.append(dest)

    monkeypatch.setattr(imtools.system, "TempFile", lambda suffix: TemporaryFile())

    output = tmp_path / "output.png"
    imtools.save(UnicodePathImage(), output)

    assert destinations == [TemporaryFile.path, output]


def test_save_check_mode_ignores_unverifiable_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(imtools, "save", lambda *_args, **_options: None)

    def fail_open(_filename: Any) -> Any:
        raise OSError("not readable by Pillow")

    monkeypatch.setattr(imtools.Image, "open", fail_open)

    assert imtools.save_check_mode(Image.new("RGB", (1, 1)), "output.raw") == ""


def test_get_quality_returns_minimum_at_search_boundary() -> None:
    assert imtools.get_quality(Image.new("RGB", (1, 1)), 1, "JPEG", up=1) == 1
