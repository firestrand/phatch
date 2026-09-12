from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from phatch.lib import thumbnail


@pytest.fixture
def cache_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    paths = {"normal": tmp_path / "normal", "large": tmp_path / "large"}
    for path in paths.values():
        path.mkdir()
    monkeypatch.setattr(thumbnail, "FREEDESKTOP_PATH", paths)
    return paths


def test_path_and_stat_helpers_cover_existing_and_new_paths(tmp_path: Path) -> None:
    # Given: a parent path and a real source file
    source = tmp_path / "source.bin"
    source.write_bytes(b"12345")
    file_stat = source.stat()

    # When: a child directory is ensured twice
    created = thumbnail.ensure_path(str(tmp_path), "cache")
    existing = thumbnail.ensure_path(str(tmp_path), "cache")

    # Then: path and stat helpers return stable filesystem values
    assert created == existing == str(tmp_path / "cache")
    assert thumbnail.get_mtime(str(source)) == thumbnail.get_mtime(
        str(source), file_stat
    )
    assert thumbnail.get_filesize(str(source)) == 5
    assert thumbnail.get_filesize(str(source), file_stat) == 5


def test_open_internal_uses_current_cache(
    cache_paths: dict[str, Path], tmp_path: Path
) -> None:
    # Given: a source with a current cache thumbnail
    source = tmp_path / "source.png"
    Image.new("RGB", (300, 100), "red").save(source)
    cached = Path(thumbnail.get_freedesktop_filename(str(source)))
    info = thumbnail.get_freedesktop_pnginfo(str(source))
    Image.new("RGB", (64, 32), "blue").save(cached, pnginfo=info)

    # When: internal open performs cache lookup
    def unexpected_open(path: str) -> Image.Image:
        raise AssertionError(path)

    result = thumbnail._open(str(source), open_image=unexpected_open)

    # Then: cached dimensions and pixels are used
    assert isinstance(result, Image.Image)
    with result:
        assert result.size == (64, 32)
        assert result.getpixel((0, 0)) == (0, 0, 255)


def test_open_internal_can_skip_or_use_cache_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: an uncached source and deterministic image opener/cache writer
    source = tmp_path / "source.png"
    source.write_bytes(b"source")
    image = Image.new("RGB", (20, 10), "green")
    monkeypatch.setattr(
        thumbnail,
        "get_freedesktop_filename",
        lambda *args: str(tmp_path / "missing.png"),
    )
    observed: list[tuple[str, tuple[int, int]]] = []

    def save(
        filename: str,
        opened: Image.Image,
        size: tuple[int, int],
        label: str,
    ) -> Image.Image:
        observed.append((filename, size))
        return opened

    monkeypatch.setattr(thumbnail, "_save_to_cache", save)

    # When: calls disable and enable cache writing
    direct = thumbnail._open(
        str(source), open_image=lambda path: image, save_cache=False
    )
    cached = thumbnail._open(str(source), image=image, size=(64, 64), save_cache=True)

    # Then: only the enabled call reaches the cache writer
    assert direct is image
    assert cached is image
    assert observed == [(str(source), (64, 64))]


def test_save_to_cache_opens_source_or_uses_supplied_image(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a cache adapter and explicit/opened source images
    opened = Image.new("RGB", (8, 4), "red")
    supplied = Image.new("RGB", (4, 8), "blue")
    observed: list[Image.Image] = []

    def save(filename: str, image: Image.Image, **options: str) -> None:
        observed.append(image)

    monkeypatch.setattr(
        thumbnail,
        "_save_to_cache",
        save,
    )

    # When: both public save paths are invoked
    thumbnail.save_to_cache("source", open_image=lambda path: opened)
    thumbnail.save_to_cache("source", image=supplied)

    # Then: the expected image reaches the cache adapter each time
    assert observed == [opened, supplied]


def test_public_open_bounds_large_results_and_flattens_small_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: internal open results above and below the requested dimensions
    large = Image.new("RGBA", (20, 10), (255, 0, 0, 128))
    small = Image.new("RGBA", (2, 1), (0, 255, 0, 128))
    results = iter((large, small))
    monkeypatch.setattr(thumbnail, "_open", lambda **options: next(results))

    # When: public open renders both thumbnails
    open_thumbnail = vars(thumbnail)["open"]
    bounded = open_thumbnail("large", size=(5, 5))
    flattened = open_thumbnail("small", size=(5, 5))

    # Then: both are RGB and only the oversized result is resized
    assert bounded.mode == flattened.mode == "RGB"
    assert bounded.size == (5, 3)
    assert flattened.size == (2, 1)


def test_delete_removes_present_cache_files_and_ignores_absent_one(
    cache_paths: dict[str, Path], tmp_path: Path
) -> None:
    # Given: only one of the two standard cache files exists
    source = str(tmp_path / "source.png")
    normal = Path(thumbnail.get_freedesktop_filename(source, "normal"))
    normal.write_bytes(b"cache")

    # When: cache deletion runs
    thumbnail.delete(source)

    # Then: deleting a partial cache completes without error
    assert not normal.exists()


def test_oversized_uncached_request_bypasses_cache_bucket(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: a request larger than standard cache dimensions
    source = tmp_path / "source.png"
    image = Image.new("RGB", (400, 200), "red")
    monkeypatch.setattr(
        thumbnail,
        "get_freedesktop_filename",
        lambda *args: (_ for _ in ()).throw(AssertionError("cache lookup")),
    )

    # When: internal open receives the already opened image
    result = thumbnail._open(str(source), image=image, size=(300, 300))

    # Then: no freedesktop cache bucket is consulted
    assert result is image


def test_save_to_cache_noops_when_platform_adapter_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a platform without a cache writer
    monkeypatch.setattr(thumbnail, "_save_to_cache", None)

    # When: public cache save is requested
    result = thumbnail.save_to_cache(
        "source", open_image=lambda path: Image.new("RGB", (1, 1))
    )

    # Then: the unsupported operation completes without opening the source
    assert result is None


def test_needs_update_uses_default_cache_filename(
    cache_paths: dict[str, Path], tmp_path: Path
) -> None:
    # Given: a source whose default normal cache entry is absent
    source = tmp_path / "source.png"
    Image.new("RGB", (1, 1)).save(source)

    # When: freshness is checked without an explicit thumbnail path
    stale = thumbnail.needs_update(str(source))

    # Then: the absent default cache entry needs regeneration
    assert stale


def test_thumbnail_preserves_pixels_after_pillow_rotation() -> None:
    # Given: a two-pixel image rotated clockwise by Pillow
    source = Image.new("RGB", (2, 1))
    source.putpixel((0, 0), (255, 0, 0))
    source.putpixel((1, 0), (0, 0, 255))
    rotated = source.transpose(Image.Transpose.ROTATE_270)

    # When: the rotated image is passed through thumbnail rendering
    result = thumbnail.thumbnail(rotated, (2, 2))

    # Then: orientation dimensions and exact endpoint pixels remain intact
    assert result.size == (1, 2)
    assert result.getpixel((0, 0)) == (255, 0, 0)
    assert result.getpixel((0, 1)) == (0, 0, 255)
