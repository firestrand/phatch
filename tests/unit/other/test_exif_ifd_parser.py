import struct
from io import BytesIO

import pytest

from phatch.other import EXIF


def _ifd_stream(entries: list[tuple[int, int, int, bytes]]) -> BytesIO:
    data_offset = 8 + 2 + (12 * len(entries)) + 4
    encoded_entries = bytearray()
    extra_data = bytearray()
    for tag, field_type, count, value in entries:
        encoded_entries.extend(struct.pack("<HHI", tag, field_type, count))
        if len(value) <= 4:
            encoded_entries.extend(value.ljust(4, b"\0"))
        else:
            encoded_entries.extend(struct.pack("<I", data_offset + len(extra_data)))
            extra_data.extend(value)
    ifd = struct.pack("<H", len(entries)) + encoded_entries + struct.pack("<I", 0)
    return BytesIO(b"II*\0" + struct.pack("<I", 8) + ifd + extra_data)


def _dump(entries: list[tuple[int, int, int, bytes]], **options):
    stream = _ifd_stream(entries)
    header = EXIF.EXIF_header(stream, "I", 0, False, options.pop("strict", False))
    header.dump_IFD(8, "Image", **options)
    return header.tags


def test_dump_ifd_decodes_ascii_numeric_signed_and_mapped_fields() -> None:
    entries = [
        (0x010F, 2, 11, b"Canon\0trash"),
        (0x0112, 3, 1, struct.pack("<H", 6)),
        (0x011A, 5, 1, struct.pack("<II", 6, 4)),
        (0xC001, 1, 1, b"\x07"),
        (0xC002, 6, 1, struct.pack("<b", -1)),
        (0xC003, 8, 1, struct.pack("<h", -2)),
        (0xC004, 9, 1, struct.pack("<i", -3)),
        (0xC005, 10, 1, struct.pack("<ii", -1, 2)),
        (0x9000, 7, 4, b"0231"),
    ]

    tags = _dump(entries)

    assert tags["Image Make"].values == "Canon"
    assert tags["Image Orientation"].printable == "Rotated 90 CW"
    assert repr(tags["Image XResolution"].values[0]) == "3/2"
    assert tags["Image Tag 0xC001"].values == [7]
    assert tags["Image Tag 0xC002"].values == [-1]
    assert tags["Image Tag 0xC003"].values == [-2]
    assert tags["Image Tag 0xC004"].values == [-3]
    assert repr(tags["Image Tag 0xC005"].values[0]) == "-1/2"
    assert tags["Image ExifVersion"].printable == "0231"


def test_dump_ifd_handles_empty_large_and_truncated_printables() -> None:
    entries = [
        (0x010F, 2, 0, b""),
        (0xC100, 1, 51, bytes(range(51))),
        (0xC101, 1, 1000, bytes(1000)),
        (0x927C, 7, 1000, bytes(1000)),
    ]

    tags = _dump(entries)

    assert tags["Image Make"].values == ""
    assert tags["Image Tag 0xC100"].printable.endswith(", ... ]")
    assert tags["Image Tag 0xC101"].values == []
    assert len(tags["Image MakerNote"].values) == 1000


def test_dump_ifd_resolves_relative_external_values() -> None:
    tags = _dump([(0x010F, 2, 6, b"Canon\0")], relative=1)

    assert tags["Image Make"].values == "Canon"


def test_dump_ifd_unknown_type_obeys_strict_mode() -> None:
    entry = [(0xC001, 0, 1, b"\0")]

    assert _dump(entry) == {}
    with pytest.raises(ValueError, match="unknown type 0"):
        _dump(entry, strict=True)


def test_dump_ifd_stop_tag_and_debug_output(capsys) -> None:
    entries = [
        (0x0112, 3, 1, struct.pack("<H", 6)),
        (0x0100, 4, 1, struct.pack("<I", 640)),
    ]
    stream = _ifd_stream(entries)
    header = EXIF.EXIF_header(stream, "I", 0, False, False, debug=True)

    header.dump_IFD(8, "Image", stop_tag="Orientation")

    assert set(header.tags) == {"Image Orientation"}
    assert "Orientation" in capsys.readouterr().out


def test_process_file_details_false_omits_expensive_fields() -> None:
    entries = [
        (0x010F, 2, 6, b"Canon\0"),
        (0x927C, 7, 8, b"raw note"),
        (0x9286, 7, 12, b"ASCII\0\0\0text"),
    ]

    tags = EXIF.process_file(_ifd_stream(entries), details=False)

    assert set(tags) == {"Image Make"}


def test_process_file_debug_reports_format_and_ifd(capsys) -> None:
    tags = EXIF.process_file(
        _ifd_stream([(0x0112, 3, 1, struct.pack("<H", 1))]),
        debug=True,
    )

    assert tags["Image Orientation"].printable == "Horizontal (normal)"
    output = capsys.readouterr().out
    assert "Intel format" in output
    assert "IFD 0 (Image)" in output


@pytest.mark.parametrize(("byte_order", "prefix"), [(b"II", "<"), (b"MM", ">")])
def test_process_file_extracts_uncompressed_tiff_thumbnail(
    byte_order: bytes, prefix: str
) -> None:
    pixel = b"\x10\x20\x30"
    thumbnail_ifd_offset = 26
    pixel_offset = thumbnail_ifd_offset + 2 + (3 * 12) + 4
    inline_one = struct.pack(f"{prefix}H", 1) + b"\0\0"
    image_ifd = struct.pack(f"{prefix}H", 1)
    image_ifd += struct.pack(f"{prefix}HHI", 0x0112, 3, 1) + inline_one
    image_ifd += struct.pack(f"{prefix}I", thumbnail_ifd_offset)
    thumbnail_ifd = struct.pack(f"{prefix}H", 3)
    thumbnail_ifd += struct.pack(f"{prefix}HHI", 0x0103, 3, 1) + inline_one
    thumbnail_ifd += struct.pack(f"{prefix}HHII", 0x0111, 4, 1, pixel_offset)
    thumbnail_ifd += struct.pack(f"{prefix}HHII", 0x0117, 4, 1, len(pixel))
    thumbnail_ifd += struct.pack(f"{prefix}I", 0)
    stream = BytesIO(
        byte_order
        + struct.pack(f"{prefix}H", 42)
        + struct.pack(f"{prefix}I", 8)
        + image_ifd
        + thumbnail_ifd
        + pixel
    )

    tags = EXIF.process_file(stream)

    assert tags["TIFFThumbnail"].startswith(byte_order)
    assert tags["TIFFThumbnail"].endswith(pixel)


def test_process_file_traverses_exif_interoperability_gps_and_multiple_ifds(
    capsys,
) -> None:
    data = bytearray(300)
    data[:8] = b"II*\0" + struct.pack("<I", 8)
    data[8:38] = (
        struct.pack("<H", 2)
        + struct.pack("<HHII", 0x8769, 4, 1, 80)
        + struct.pack("<HHII", 0x8825, 4, 1, 180)
        + struct.pack("<I", 220)
    )
    data[80:110] = (
        struct.pack("<H", 2)
        + struct.pack("<HHII", 0x9003, 2, 20, 110)
        + struct.pack("<HHII", 0xA005, 4, 1, 140)
        + struct.pack("<I", 0)
    )
    data[110:130] = b"2026:09:11 12:34:56\0"
    data[140:158] = (
        struct.pack("<H", 1)
        + struct.pack("<HHI", 0x0001, 2, 4)
        + b"R98\0"
        + struct.pack("<I", 0)
    )
    data[180:198] = (
        struct.pack("<H", 1)
        + struct.pack("<HHI", 0x0001, 2, 2)
        + b"N\0\0\0"
        + struct.pack("<I", 0)
    )
    data[220:226] = struct.pack("<HI", 0, 240)
    data[240:258] = (
        struct.pack("<H", 1)
        + struct.pack("<HHI", 0x0100, 4, 1)
        + struct.pack("<I", 800)
        + struct.pack("<I", 0)
    )

    tags = EXIF.process_file(BytesIO(data), debug=True)

    assert tags["EXIF DateTimeOriginal"].values == "2026:09:11 12:34:56"
    assert tags["EXIF Interoperability InteroperabilityIndex"].values == "R98"
    assert tags["GPS GPSLatitudeRef"].values == "N"
    assert tags["IFD 2 ImageWidth"].values == [800]
    output = capsys.readouterr().out
    assert "EXIF Interoperability SubSubIFD" in output
    assert "GPS SubIFD" in output
