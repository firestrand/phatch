from io import BytesIO

import pytest

from phatch.other import EXIF


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([0, 31], [0, 31]),
        ([0, 65, 10, 255], "Aÿ"),
        ([0] * 8 + [80, 104, 97, 116, 99, 104], "Phatch"),
    ],
)
def test_string_helpers_filter_binary_values(
    values: list[int], expected: str | list[int]
) -> None:
    if len(values) > 8:
        assert EXIF.make_string_uc(values) == expected
    else:
        assert EXIF.make_string(values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([252, 1, 6, 0], "-2/3 EV"),
        ([253, 1, 6, 0], "-1/2 EV"),
        ([254, 1, 6, 0], "-1/3 EV"),
        ([0, 1, 6, 0], "0 EV"),
        ([0, 2, 6, 0], "0 EV"),
        ([2, 1, 6, 0], "+1/3 EV"),
        ([3, 1, 6, 0], "+1/2 EV"),
        ([4, 1, 6, 0], "+2/3 EV"),
        ([6, 1, 6, 0], "+1 EV"),
        ([250, 1, 6, 0], "-1 EV"),
        ([5, 1, 6, 0], "+5/6 EV"),
        ([1, 2], ""),
    ],
)
def test_nikon_ev_bias_formats_camera_values(values: list[int], expected: str) -> None:
    assert EXIF.nikon_ev_bias(values) == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([3, 2, 4], "Panorama - sequence 2 - Top to bottom"),
        ([9, 2, 4], [9, 2, 4]),
        ([3, 2, 9], [3, 2, 9]),
    ],
)
def test_olympus_special_mode_maps_known_values(
    values: list[int], expected: str | list[int]
) -> None:
    assert EXIF.olympus_special_mode(values) == expected


def test_ratio_and_tag_representations_preserve_metadata_contract() -> None:
    ratio = EXIF.Ratio(6, 4)
    tag = EXIF.IFD_Tag("3/2", 0x011A, 5, [ratio], 38, 8)

    assert repr(ratio) == "3/2"
    assert str(tag) == "3/2"
    assert repr(tag) == "(0x011A) Ratio=3/2 @ 38"


@pytest.mark.parametrize(
    ("endian", "encoded"),
    [("I", b"\x78\x56\x34\x12"), ("M", b"\x12\x34\x56\x78")],
)
def test_header_integer_conversion_obeys_endian(endian: str, encoded: bytes) -> None:
    header = EXIF.EXIF_header(BytesIO(encoded), endian, 0, False, False)

    assert header.s2n(0, 4) == 0x12345678
    assert header.n2s(0x12345678, 4) == encoded


def test_header_signed_integer_conversion_sign_extends() -> None:
    header = EXIF.EXIF_header(BytesIO(b"\xff\xfe"), "M", 0, False, False)

    assert header.s2n(0, 2, signed=True) == -2


def test_canon_decoder_maps_known_and_unknown_array_members(capsys) -> None:
    header = EXIF.EXIF_header(BytesIO(), "I", 0, False, False, debug=True)

    header.canon_decode_tag(
        [0, 1, 7, 9],
        {1: ("Mode", {1: "Auto"}), 2: ("Count",)},
    )

    assert header.tags["MakerNote Mode"].printable == "Auto"
    assert header.tags["MakerNote Count"].printable == "7"
    assert header.tags["MakerNote Unknown"].printable == "9"
    assert "Mode" in capsys.readouterr().out
