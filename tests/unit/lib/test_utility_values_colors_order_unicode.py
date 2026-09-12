from __future__ import annotations

import copy
from pathlib import Path

import pytest

from phatch.lib import colors, odict, unicoding


@pytest.mark.parametrize(
    ("rgb", "html", "pil"),
    [
        ((0, 0, 0), "#000000", 0x000000),
        ((255, 255, 255), "#ffffff", 0xFFFFFF),
        ((1, 16, 171), "#0110ab", 0xAB1001),
        ((18, 52, 86), "#123456", 0x563412),
    ],
)
def test_color_representations_round_trip(
    rgb: tuple[int, int, int], html: str, pil: int
) -> None:
    # Given: equivalent RGB, HTML, and legacy PIL color values
    # When: each representation is converted
    # Then: all conversion paths agree on the known values
    assert colors.RGBToHTMLColor(rgb) == html
    assert colors.HTMLColorToRGB(f"  {html.upper()}  ") == rgb
    assert colors.HTMLColorToRGB(html[1:]) == rgb
    assert colors.HTMLColorToPILColor(html) == pil
    assert colors.PILColorToRGB(pil) == rgb
    assert colors.PILColorToHTMLColor(pil) == html
    assert colors.RGBToPILColor(rgb) == pil


def test_rgba_preserves_caller_opacity() -> None:
    # Given: a valid HTML color and transparent alpha
    # When: RGBA is constructed
    result = colors.HTMLColorToRGBA("#123456", 0)

    # Then: RGB is parsed and opacity is preserved exactly
    assert result == (18, 52, 86, 0)


@pytest.mark.parametrize("value", ["", "#12345", "#1234567", "#12xz56"])
def test_invalid_html_colors_raise_value_error(value: str) -> None:
    # Given: malformed HTML color input
    # When/Then: parsing rejects it consistently
    with pytest.raises(ValueError):
        colors.HTMLColorToRGB(value)


def test_odict_preserves_order_across_mutations() -> None:
    # Given: an ordered mapping with three entries
    values = odict.odict({"a": 1, "b": 2, "c": 3})

    # When: an existing key changes, a key moves, and a new key is appended
    values["b"] = 20
    values.move("c", 0)
    values["d"] = 4

    # Then: each view reflects the maintained logical order
    assert values.keys() == ["c", "a", "b", "d"]
    assert list(values.items()) == [("c", 3), ("a", 1), ("b", 20), ("d", 4)]
    assert list(values.values()) == [3, 1, 20, 4]
    assert values.index("b") == 2


def test_odict_update_delete_pop_clear_and_deepcopy() -> None:
    # Given: an ordered mapping and an independent deep copy
    values = odict.odict({"a": [1], "b": [2]})
    cloned = copy.deepcopy(values)

    # When: update, deletion, pop, and clear mutate only the original
    values.update({"a": [10], "c": [3]})
    del values["b"]
    popped = values.popitem()
    values.clear()

    # Then: operations obey ordering while the deep copy stays independent
    assert popped == ("c", [3])
    assert values.keys() == []
    assert list(cloned.items()) == [("a", [1]), ("b", [2])]
    assert cloned["a"] is not values.get("a")


def test_odict_setdefault_returns_value_and_appends_only_new_keys() -> None:
    # Given: an ordered mapping with one existing key
    values = odict.odict({"a": 1})

    # When: defaults are requested for existing and absent keys
    existing = values.setdefault("a", 9)
    inserted = values.setdefault("b", 2)

    # Then: dict-compatible return values and insertion order are preserved
    assert existing == 1
    assert inserted == 2
    assert values.keys() == ["a", "b"]


def test_odict_reports_empty_or_missing_operations() -> None:
    # Given: an empty ordered mapping
    values = odict.odict()

    # When/Then: operations requiring an existing key raise KeyError
    with pytest.raises(KeyError):
        values.popitem()
    with pytest.raises(KeyError):
        values.move("missing", 0)
    with pytest.raises(KeyError):
        values.index("missing")


def test_odict_initializes_keys_when_setitem_precedes_init() -> None:
    # Given: an instance constructed through the deepcopy allocation path
    values = odict.odict.__new__(odict.odict)

    # When: deepcopy-style assignment occurs before __init__
    values["first"] = 1

    # Then: ordering state is initialized with the assigned key
    assert values.keys() == ["first"]


def test_odict_move_to_later_index_preserves_all_keys() -> None:
    # Given: three ordered keys
    values = odict.odict({"a": 1, "b": 2, "c": 3})

    # When: the first key moves after its current position
    values.move("a", 3)

    # Then: the key is moved once without duplication
    assert values.keys() == ["b", "c", "a"]


def test_read_only_dict_is_callable_and_reflects_source_updates() -> None:
    # Given: a callable read-only facade over mutable source data
    source = {"name": "first"}
    read = odict.ReadOnlyDict(source)

    # When: source data changes
    source["name"] = "second"

    # Then: lookup reflects the source without exposing mutation methods
    assert read("name") == "second"
    with pytest.raises(KeyError):
        read("missing")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("café 東京", "café 東京"), (42, "42"), (None, "None"), (b"caf\xc3\xa9", "café")],
)
def test_ensure_unicode_returns_readable_text(
    value: str | int | bytes | None, expected: str
) -> None:
    # Given: a common value crossing a display boundary
    # When: it is normalized to text
    normalized = unicoding.ensure_unicode(value)

    # Then: known Unicode and UTF-8 byte content remains readable
    assert normalized == expected


def test_ensure_unicode_replaces_invalid_bytes() -> None:
    # Given: invalid UTF-8 data from an external boundary
    # When: decoding uses replacement semantics
    normalized = unicoding.ensure_unicode(b"bad\xff", encoding="utf-8")

    # Then: output remains usable Unicode text
    assert normalized == "bad�"


class BrokenTextError(Exception):
    def __str__(self) -> str:
        raise RuntimeError("broken text conversion")


def test_exception_to_unicode_handles_normal_and_broken_messages() -> None:
    # Given: exceptions with readable and broken string conversion
    # When: messages are normalized for display
    # Then: Unicode is retained and irrecoverable conversion uses a marker
    assert unicoding.exception_to_unicode(ValueError("café")) == "café"
    assert unicoding.exception_to_unicode(BrokenTextError()) == "?"


def test_candidate_encodings_prioritize_unique_preference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: a deterministic platform encoding
    monkeypatch.setattr(unicoding, "ENCODING", "cp1252")

    # When: default and explicit candidate lists are requested
    # Then: ordering is stable and a repeated preference appears once
    assert unicoding._candidate_encodings() == ["latin1", "utf-8", "cp1252"]
    assert unicoding._candidate_encodings("utf-8") == ["utf-8", "latin1", "cp1252"]


def test_fix_filename_known_paths_and_falsey_values(tmp_path: Path) -> None:
    # Given: an existing Unicode path and its filesystem bytes
    path = tmp_path / "café 東京.txt"
    path.write_text("data", encoding="utf-8")

    # When/Then: known paths normalize to text and falsey paths are absent
    assert unicoding.fix_filename(str(path)) == str(path)
    assert unicoding.fix_filename(bytes(path)) == str(path)
    assert unicoding.fix_filename("") is None
    assert unicoding.fix_filename(None) is None
    assert unicoding.fix_filename(str(tmp_path / "missing")) is None


def test_fix_filename_recovers_bytes_with_preferred_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: Latin-1 bytes whose decoded text is reported as an existing file
    raw = b"caf\xe9.txt"
    monkeypatch.setattr(unicoding.os.path, "isfile", lambda path: False)
    monkeypatch.setattr(unicoding.system, "is_file", lambda path: path == "café.txt")

    # When: Latin-1 is explicitly preferred
    recovered = unicoding.fix_filename(raw, encoding="latin1")

    # Then: the known readable filename is returned
    assert recovered == "café.txt"


def test_fix_filename_falls_back_after_system_type_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: a system probe that rejects text while the OS probe accepts it
    path = tmp_path / "plain.txt"
    path.write_text("data", encoding="utf-8")
    monkeypatch.setattr(
        unicoding.system,
        "is_file",
        lambda path: (_ for _ in ()).throw(TypeError("unsupported path")),
    )

    # When: filename recovery probes the path
    recovered = unicoding.fix_filename(str(path))

    # Then: the direct filesystem check returns the original text
    assert recovered == str(path)
