from __future__ import annotations

from pathlib import Path

import pytest
from PIL import ImageFont

from phatch.lib import fonts
from phatch.resources.provider import ResourceProvider


@pytest.fixture(autouse=True)
def isolated_font_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Given: font globals and caches confined to the current test directory
    monkeypatch.setattr(fonts, "_FONT_DICTIONARY", None)
    monkeypatch.setattr(fonts, "_FONT_NAMES", None)
    monkeypatch.setattr(fonts, "SHIPPED_FONTS", {})
    monkeypatch.setattr(fonts, "USER_FONTS_CACHE_PATH", str(tmp_path / "user.cache"))
    monkeypatch.setattr(fonts, "ROOT_FONTS_CACHE_PATH", str(tmp_path / "root.cache"))
    monkeypatch.setattr(
        fonts, "WRITABLE_FONTS_CACHE_PATH", str(tmp_path / "write.cache")
    )


def test_packaged_font_is_parsed_and_named_by_real_pillow() -> None:
    # Given: the actual font distributed by the package resource provider
    provider = ResourceProvider()

    # When: Pillow and Phatch parse the materialized font
    with provider.as_path("data/fonts/FreeSans.ttf") as font_path:
        pillow_font = ImageFont.truetype(str(font_path), 16)
        discovered = fonts._font_dictionary([str(font_path)])

    # Then: both consumers expose usable font information
    assert pillow_font.getbbox("Phatch")[2] > 0
    assert list(discovered) == ["Free Sans"]


def test_collect_fonts_recurses_and_filters_supported_extensions(
    tmp_path: Path,
) -> None:
    # Given: nested font and non-font files under one temporary root
    nested = tmp_path / "nested"
    nested.mkdir()
    ttf = nested / "Alpha.TTF"
    otf = nested / "Beta.otf"
    ignored = nested / "notes.txt"
    for path in (ttf, otf, ignored):
        path.write_bytes(b"fixture")

    # When: fonts are discovered from explicit paths only
    discovered = fonts.collect_fonts_from_dirs(
        [str(tmp_path), str(tmp_path / "absent")]
    )

    # Then: discovery is recursive and extension matching is case-insensitive
    assert set(discovered) == {str(ttf), str(otf)}


def test_merge_supports_nested_true_type_and_open_type_fonts(tmp_path: Path) -> None:
    # Given: font roots containing nested TTF and OTF files
    first = tmp_path / "first"
    second = tmp_path / "second" / "nested"
    first.mkdir()
    second.mkdir(parents=True)
    (first / "AlphaBold.ttf").write_bytes(b"fixture")
    (second / "BetaItalic.otf").write_bytes(b"fixture")

    # When: configured font roots are merged
    merged = fonts.merge(str(first), str(tmp_path / "second"))

    # Then: both supported formats participate in name matching
    assert set(merged) == {"Alpha Bold", "Beta Italic"}


def test_font_dictionary_decodes_byte_paths() -> None:
    # Given: byte paths such as those returned by Unix subprocess discovery
    font_path = b"/tmp/FreeSans.ttf"

    # When: the dictionary derives display names
    discovered = fonts._font_dictionary([font_path])

    # Then: public paths and names are text
    assert discovered == {"Free Sans": "/tmp/FreeSans.ttf"}


def test_font_dictionary_reads_cache_and_merges_shipped_fonts(tmp_path: Path) -> None:
    # Given: a UTF-8 cache and a separately shipped font
    cache = tmp_path / "fonts.cache"
    cache.write_text("{'Café': '/tmp/café.ttf'}", encoding="utf-8")
    fonts.SHIPPED_FONTS = {"Free Sans": "/package/FreeSans.ttf"}

    # When: the cache is loaded without a system scan
    discovered = fonts.font_dictionary(str(cache))

    # Then: cached and shipped mappings are both available
    assert discovered == {
        "Café": "/tmp/café.ttf",
        "Free Sans": "/package/FreeSans.ttf",
    }


def test_font_dictionary_force_rescans_and_writes_only_temporary_cache(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: an initialized mapping and a deterministic replacement scan
    fonts._FONT_DICTIONARY = {"Stale": "/old.ttf"}
    scanned = {"Fresh": "/new.ttf"}
    monkeypatch.setattr(fonts, "_font_dictionary", lambda: scanned.copy())

    # When: a forced refresh is requested
    discovered = fonts.font_dictionary(force=True)

    # Then: stale data is replaced and the configured temp cache is written
    assert discovered == scanned
    assert (tmp_path / "write.cache").read_text(encoding="utf-8") == str(scanned)


def test_empty_scan_provides_ui_placeholder_without_uninitialized_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: no configured cache paths and no discovered fonts
    monkeypatch.setattr(fonts, "USER_FONTS_CACHE_PATH", None)
    monkeypatch.setattr(fonts, "ROOT_FONTS_CACHE_PATH", None)
    monkeypatch.setattr(fonts, "WRITABLE_FONTS_CACHE_PATH", None)
    monkeypatch.setattr(fonts, "_font_dictionary", lambda: {})

    # When: consumers request the font mapping
    discovered = fonts.font_dictionary()

    # Then: the UI-safe placeholder is returned without touching HOME
    assert discovered == {"": ""}


def test_root_cache_is_selected_and_font_names_are_memoized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: only the root cache exists and system scanning must not run
    root_cache = tmp_path / "root.cache"
    root_cache.write_text("{'Root Font': '/root/font.ttf'}", encoding="utf-8")
    monkeypatch.setattr(
        fonts,
        "_font_dictionary",
        lambda: (_ for _ in ()).throw(AssertionError("system scan")),
    )

    # When: names are requested twice
    first = fonts.font_names()
    second = fonts.font_names()

    # Then: the root cache is selected and the sorted name list is reused
    assert first == ["Root Font"]
    assert second is first


def test_root_user_chooses_root_cache_for_writes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: isolated empty font roots and an effective root user
    user_fonts = tmp_path / "user"
    root_fonts = tmp_path / "root"
    user_fonts.mkdir()
    root_fonts.mkdir()
    monkeypatch.setattr(fonts.os, "getuid", lambda: 0)

    # When: cache paths are configured
    root_cache = tmp_path / "root.cache"
    fonts.set_font_cache(
        str(user_fonts),
        str(root_fonts),
        str(tmp_path / "user.cache"),
        str(root_cache),
    )

    # Then: cache writes are directed to the isolated root cache
    assert str(root_cache) == fonts.WRITABLE_FONTS_CACHE_PATH


def test_set_font_cache_invalidates_derived_globals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: stale derived state and new isolated font/cache roots
    user_fonts = tmp_path / "user-fonts"
    root_fonts = tmp_path / "root-fonts"
    user_fonts.mkdir()
    root_fonts.mkdir()
    (user_fonts / "Fresh.ttf").write_bytes(b"fixture")
    fonts._FONT_DICTIONARY = {"Stale": "/old.ttf"}
    fonts._FONT_NAMES = ["Stale"]
    monkeypatch.setattr(fonts.os, "getuid", lambda: 501)
    monkeypatch.setattr(fonts, "collect_fonts", lambda: [])

    # When: font cache paths are reconfigured
    fonts.set_font_cache(
        str(user_fonts),
        str(root_fonts),
        str(tmp_path / "user.cache"),
        str(tmp_path / "root.cache"),
    )

    # Then: derived values are rebuilt from the new roots
    assert fonts.font_names() == ["", "Fresh"]
    assert str(tmp_path / "user.cache") == fonts.WRITABLE_FONTS_CACHE_PATH


@pytest.mark.parametrize(
    ("raw_name", "base", "expected"),
    [
        ("Ariblk", "xxx", ("Arial", "Arial Black")),
        ("Cour", "xxx", ("Cour", "Courier New")),
        ("Micross", "xxx", ("Microsoft Sans Serif", "Microsoft Sans Serif Regular")),
        ("Lucon", "xxx", ("Lucida", "Lucida Console")),
        ("L 10646", "xxx", ("Lucida", "Lucida Sans Unicode")),
        ("Pala", "xxx", ("Pala", "Palatino Linotype")),
        ("Trebuc", "xxx", ("Trebuc", "Trebuchet")),
        ("Gen A Book", "xxx", ("Gentium Alt  Book", "Gentium")),
        ("Gen Book", "xxx", ("Gentium Book", "Gentium")),
        ("Free It", "Free", ("Free Italic", "Free")),
        ("Free Bd", "Free", ("Free Bold", "Free")),
        ("Free Bi", "Free", ("Free Bold Italic", "Free")),
        ("Free Mr", "Free", ("Free Mono Regular", "Free")),
        ("Free Mri", "Free", ("Free Mono Italic", "Free")),
        ("Free Mb", "Free", ("Free Mono Bold", "Free")),
        ("Free Mbi", "Free", ("Free Mono Bold Italic", "Free")),
        ("Free Rr", "Free", ("Free Serif", "Free")),
        ("Free Rri", "Free", ("Free Serif Italic", "Free")),
        ("Free Rb", "Free", ("Free Serif Bold", "Free")),
        ("Free Rbi", "Free", ("Free Serif Bold Italic", "Free")),
        ("Free Sb", "Free", ("Free Sans Bold", "Free")),
        ("Free Sbi", "Free", ("Free Sans Bold Italic", "Free")),
        ("Free Sr", "Free", ("Free Sans", "Free")),
        ("Free Sri", "Free", ("Free Sans Italic", "Free")),
        ("Novel Bd", "xxx", ("Novel Bold", "Novel")),
    ],
)
def test_font_name_expands_legacy_filename_abbreviations(
    raw_name: str, base: str, expected: tuple[str, str]
) -> None:
    # Given: a legacy filename-derived name and its current family base
    # When: the matching heuristic expands it
    expanded = fonts._font_name(raw_name, base)

    # Then: the user-facing font name identifies its family and style
    assert expanded == expected
