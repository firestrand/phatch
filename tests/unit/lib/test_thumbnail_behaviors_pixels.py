from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image, PngImagePlugin

from phatch.lib import thumbnail


@pytest.fixture
def isolated_thumbnail_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> dict[str, Path]:
    paths = {"normal": tmp_path / "normal", "large": tmp_path / "large"}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setattr(thumbnail, "FREEDESKTOP_PATH", paths)
    return paths


def save_source(path: Path, size: tuple[int, int] = (300, 100)) -> Path:
    Image.new("RGB", size, (11, 22, 33)).save(path)
    return path


def test_thumbnail_preserves_aspect_pixels_and_source() -> None:
    # Given: a wide real Pillow image
    source = Image.new("RGB", (300, 100), (11, 22, 33))

    # When: a bounded thumbnail copy is made
    result = thumbnail.thumbnail(source, (128, 128))

    # Then: dimensions, pixels, and source independence are observable
    assert result.size == (128, 43)
    assert result.getpixel((0, 0)) == (11, 22, 33)
    assert source.size == (300, 100)
    assert result is not source


def test_thumbnail_can_resize_in_place() -> None:
    # Given: a mutable image supplied for in-place thumbnailing
    source = Image.new("RGB", (300, 100), (11, 22, 33))

    # When: copying is disabled
    result = thumbnail.thumbnail(source, (30, 30), copy=False)

    # Then: the same image is resized
    assert result is source
    assert source.size == (30, 10)


def test_thumbnail_adds_checkerboard_for_transparency() -> None:
    # Given: a transparent image with one opaque red pixel
    source = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
    source.putpixel((0, 0), (255, 0, 0, 255))

    # When: checkerboard display is requested
    result = thumbnail.thumbnail(source, (2, 1), checkboard=True)

    # Then: alpha is flattened while the opaque pixel remains red
    assert result.mode == "RGB"
    assert result.getpixel((0, 0)) == (255, 0, 0)
    assert result.getpixel((1, 0)) != (0, 0, 0)


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        ((128, 128), "normal"),
        ((128, 129), "large"),
        ((256, 256), "large"),
        ((257, 1), ""),
    ],
)
def test_freedesktop_size_lookup_bounds(
    size: tuple[int, int], expected: str
) -> None:
    # Given: a request at a cache-size boundary
    # When: the freedesktop bucket is selected
    label = thumbnail.get_freedesktop_size_label(size)

    # Then: only requests within standard bounds receive a cache label
    assert label == expected


def test_unicode_uri_and_hash_are_clean_text(tmp_path: Path) -> None:
    # Given: a source path containing spaces and non-ASCII text
    source = tmp_path / "café photo.png"

    # When: its cache identity is generated
    uri = thumbnail.get_uri(str(source))

    # Then: the URI is quoted text and the hash derives from that exact text
    assert uri.endswith("caf%C3%A9%20photo.png")
    assert "b%27" not in uri
    assert thumbnail.get_hash(str(source)) == hashlib.md5(uri.encode()).hexdigest()
    assert thumbnail.get_uri(uri) == uri


def test_pnginfo_records_source_metadata_and_overrides(tmp_path: Path) -> None:
    # Given: a real source file and dimensions supplied by the caller
    source = save_source(tmp_path / "source.png", (9, 7))

    # When: freedesktop metadata is built with a software override
    info = thumbnail.get_freedesktop_pnginfo(
        str(source), thumb_info={"software": "Test", "width": 9, "height": 7}
    )

    # Then: cache identity, size, dimensions, and producer are recorded
    assert info.chunks == [
        (b"tEXt", b"Thumb::URI\x00" + thumbnail.get_uri(str(source)).encode(), False),
        (
            b"tEXt",
            b"Thumb::MTime\x00"
            + str(thumbnail.get_mtime(str(source))).encode(),
            False,
        ),
        (b"tEXt", b"Thumb::Size\x00" + str(source.stat().st_size).encode(), False),
        (b"tEXt", b"Thumb::Software\x00Test", False),
        (b"tEXt", b"Thumb::Image::Height\x007", False),
        (b"tEXt", b"Thumb::Image::Width\x009", False),
    ]


def test_pnginfo_uses_image_dimensions_and_can_omit_optional_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: metadata defaults without software and a source image
    source = save_source(tmp_path / "source.png", (9, 7))
    image = Image.open(source)

    # When: metadata is generated from image dimensions
    monkeypatch.setattr(thumbnail, "THUMB_INFO", {})
    info = thumbnail.get_freedesktop_pnginfo(str(source), image=image)

    # Then: dimensions remain present while software is omitted
    payloads = [chunk[1] for chunk in info.chunks]
    assert b"Thumb::Image::Height\x007" in payloads
    assert b"Thumb::Image::Width\x009" in payloads
    assert not any(b"Thumb::Software" in payload for payload in payloads)


def test_cache_round_trip_has_metadata_dimensions_and_secure_mode(
    isolated_thumbnail_cache: dict[str, Path], tmp_path: Path
) -> None:
    # Given: a real source and image destined for the normal cache
    source = save_source(tmp_path / "source.png", (300, 100))
    image = Image.open(source)

    # When: the thumbnail is saved to cache
    result = thumbnail._save_to_cache(str(source), image, (128, 128), "normal")

    # Then: pixels, dimensions, metadata, and file permissions survive round-trip
    cached_path = Path(thumbnail.get_freedesktop_filename(str(source), "normal"))
    with Image.open(cached_path) as cached:
        assert cached.size == (128, 43)
        assert cached.info["Thumb::Image::Width"] == "300"
        assert cached.info["Thumb::Image::Height"] == "100"
    assert result.size == (128, 43)
    assert cached_path.stat().st_mode & 0o777 == 0o600


def test_large_cache_populates_both_sizes(
    isolated_thumbnail_cache: dict[str, Path], tmp_path: Path
) -> None:
    # Given: a source requiring the large freedesktop bucket
    source = save_source(tmp_path / "source.png", (600, 300))
    image = Image.open(source)

    # When: a large thumbnail is cached
    result = thumbnail._save_to_cache(str(source), image, (200, 200), "large")

    # Then: normal and large cache files exist and requested bounds are honored
    assert result.size == (200, 100)
    cache_hash = thumbnail.get_hash(str(source))
    assert all(
        (path / f"{cache_hash}.png").is_file()
        for path in isolated_thumbnail_cache.values()
    )
    normal_cache = isolated_thumbnail_cache["normal"] / f"{cache_hash}.png"
    with Image.open(normal_cache) as cached:
        assert cached.size == (128, 64)


def test_needs_update_handles_missing_broken_unmarked_stale_and_current_cache(
    isolated_thumbnail_cache: dict[str, Path], tmp_path: Path
) -> None:
    # Given: one source and its deterministic cache filename
    source = save_source(tmp_path / "source.png")
    cached = Path(thumbnail.get_freedesktop_filename(str(source)))
    assert thumbnail.needs_update(str(source), thumb_filename=str(cached))
    cached.write_bytes(b"not-png")
    assert thumbnail.needs_update(str(source), thumb_filename=str(cached))
    Image.new("RGB", (1, 1)).save(cached)
    assert thumbnail.needs_update(str(source), thumb_filename=str(cached))
    stale = PngImagePlugin.PngInfo()
    stale.add_text("Thumb::MTime", "0")
    Image.new("RGB", (1, 1)).save(cached, pnginfo=stale)
    assert thumbnail.needs_update(str(source), thumb_filename=str(cached))

    # When: cache metadata matches the source mtime
    current = thumbnail.get_freedesktop_pnginfo(str(source))
    Image.new("RGB", (1, 1)).save(cached, pnginfo=current)

    # Then: the cache is accepted as current
    assert not thumbnail.needs_update(str(source), thumb_filename=str(cached))


@pytest.mark.parametrize(
    ("size", "format_name", "expected"),
    [
        ((512, 512), "JPEG", False),
        ((513, 1), "JPEG", True),
        ((128, 128), "PNG", False),
        ((1, 129), "PNG", True),
    ],
)
def test_thumbnail_need_thresholds(
    size: tuple[int, int], format_name: str, expected: bool
) -> None:
    # Given: an image and output format at a thumbnail threshold
    # When: thumbnail necessity is evaluated
    needed = thumbnail.is_needed(Image.new("RGB", size), format_name)

    # Then: JPEG and other formats use their documented bounds
    assert needed is expected


def test_format_data_passes_a_bounded_image_to_encoder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an oversized source image
    source = Image.new("RGB", (300, 100), (11, 22, 33))

    # When: PNG thumbnail bytes are requested
    observed: list[tuple[tuple[int, int], tuple[int, int, int], str]] = []

    def encode(image: Image.Image, format_name: str) -> bytes:
        observed.append((image.size, image.getpixel((0, 0)), format_name))
        return b"encoded"

    monkeypatch.setattr(thumbnail.imtools, "get_format_data", encode)
    encoded = thumbnail.get_format_data(source, "PNG", (30, 30))

    # Then: Pillow can decode the bounded pixels
    assert encoded == b"encoded"
    assert observed == [((30, 10), (11, 22, 33), "PNG")]
