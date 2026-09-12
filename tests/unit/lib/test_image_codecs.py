from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageChops, ImageCms, ImageSequence, ImageStat

from phatch.lib import image_codecs
from phatch.lib.image_codecs import codec_capabilities, codec_for_extension


def test_codec_capabilities_follow_live_pillow_registries() -> None:
    # Given
    Image.init()

    # When
    capabilities = codec_capabilities()

    # Then
    by_format = {capability.format_name: capability for capability in capabilities}
    assert by_format["PNG"].can_read is ("PNG" in Image.OPEN)
    assert by_format["PNG"].can_write is ("PNG" in Image.SAVE)
    assert ".png" in by_format["PNG"].extensions
    assert codec_for_extension(".png", capabilities) == by_format["PNG"]


@pytest.mark.parametrize("extension", ["jpg", "png", "tiff", "gif", "webp"])
def test_registered_core_codec_roundtrip_is_real(
    extension: str, tmp_path: Path
) -> None:
    # Given
    capability = codec_for_extension(extension, codec_capabilities())
    if capability is None or not (capability.can_read and capability.can_write):
        pytest.skip(f"runtime Pillow build lacks {extension}")
    output = tmp_path / f"roundtrip.{extension}"
    image = Image.new("RGBA", (8, 6), (20, 40, 60, 128))
    if capability.format_name == "JPEG":
        image = image.convert("RGB")

    # When
    image.save(output, format=capability.format_name, quality=85)

    # Then
    with Image.open(output) as decoded:
        decoded.load()
        assert decoded.size == (8, 6)
        assert decoded.format == capability.format_name


def test_gif_roundtrip_preserves_animation_policy(tmp_path: Path) -> None:
    # Given
    output = tmp_path / "animated.gif"
    first = Image.new("RGB", (4, 3), "red")
    second = Image.new("RGB", (4, 3), "blue")

    # When
    first.save(
        output,
        save_all=True,
        append_images=[second],
        duration=[40, 80],
        loop=2,
        transparency=0,
    )

    # Then
    with Image.open(output) as decoded:
        durations = [
            frame.info["duration"] for frame in ImageSequence.Iterator(decoded)
        ]
        assert decoded.n_frames == 2
        assert decoded.info["loop"] == 2
        assert durations == [40, 80]


@pytest.mark.parametrize("extension", ["jpg", "png", "tiff", "webp", "avif"])
def test_registered_codec_preserves_supported_color_metadata(
    extension: str, tmp_path: Path
) -> None:
    # Given
    capability = codec_for_extension(extension, codec_capabilities())
    if capability is None or not (capability.can_read and capability.can_write):
        pytest.skip(f"runtime Pillow build lacks {extension}")
    output = tmp_path / f"metadata.{extension}"
    image = Image.new("RGB", (16, 12), (30, 80, 120))
    exif = Image.Exif()
    exif[0x010E] = "phatch-codec-test"
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

    # When
    image.save(
        output,
        format=capability.format_name,
        quality=90,
        exif=exif,
        icc_profile=profile,
    )

    # Then
    with Image.open(output) as decoded:
        decoded.load()
        assert decoded.size == image.size
        assert decoded.getexif().get(0x010E) == "phatch-codec-test"
        assert decoded.info.get("icc_profile") == profile


def test_jpeg_quality_has_bounded_pixel_error(tmp_path: Path) -> None:
    # Given
    image = Image.effect_noise((128, 128), 64).convert("RGB")
    low = tmp_path / "low.jpg"
    high = tmp_path / "high.jpg"

    # When
    image.save(low, quality=20)
    image.save(high, quality=90)

    # Then
    with Image.open(low) as low_image, Image.open(high) as high_image:
        low_error = sum(ImageStat.Stat(ImageChops.difference(image, low_image)).mean)
        high_error = sum(ImageStat.Stat(ImageChops.difference(image, high_image)).mean)
    assert high_error < low_error
    assert high_error < 30


@pytest.mark.parametrize("extension", ["png", "webp", "avif"])
def test_registered_alpha_codec_preserves_transparency(
    extension: str, tmp_path: Path
) -> None:
    # Given
    capability = codec_for_extension(extension, codec_capabilities())
    if capability is None or not capability.can_write:
        pytest.skip(f"runtime Pillow build lacks {extension}")
    output = tmp_path / f"alpha.{extension}"
    image = Image.new("RGBA", (8, 8), (30, 60, 90, 77))

    # When
    image.save(output, format=capability.format_name, quality=90)

    # Then
    with Image.open(output) as decoded:
        assert decoded.convert("RGBA").getchannel("A").getextrema() == (77, 77)


def test_heif_is_runtime_optional(tmp_path: Path) -> None:
    # Given
    capability = codec_for_extension("heic", codec_capabilities())

    # When / Then
    if capability is None:
        assert capability is None
        return
    output = tmp_path / "optional.heic"
    Image.new("RGB", (8, 6), "green").save(output, format=capability.format_name)
    with Image.open(output) as decoded:
        assert decoded.size == (8, 6)


def test_optional_heif_registration_calls_provider(monkeypatch) -> None:
    # Given
    registrations = []
    provider = SimpleNamespace(
        register_heif_opener=lambda: registrations.append("registered")
    )
    monkeypatch.setattr(image_codecs.importlib, "import_module", lambda _name: provider)

    # When
    result = image_codecs.register_optional_heif()

    # Then
    assert result is provider
    assert registrations == ["registered"]


def test_optional_heif_provider_without_opener_remains_nonfatal(monkeypatch) -> None:
    # Given
    provider = SimpleNamespace()
    monkeypatch.setattr(image_codecs.importlib, "import_module", lambda _name: provider)

    # When / Then
    assert image_codecs.register_optional_heif() is provider
