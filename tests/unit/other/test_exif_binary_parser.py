import struct
from hashlib import sha256
from io import BytesIO

import pytest
from PIL import Image

from phatch.other import EXIF


def _pillow_jpeg_with_exif() -> BytesIO:
    stream = BytesIO()
    exif = Image.Exif()
    exif[0x010F] = "Phatch Camera"
    exif[0x0112] = 6
    exif[0x9003] = "2026:09:11 12:34:56"
    Image.new("RGB", (2, 2), "red").save(stream, format="JPEG", exif=exif)
    stream.seek(0)
    return stream


def _tiff_with_orientation_and_rational(byte_order: str) -> BytesIO:
    prefix = "<" if byte_order == "II" else ">"
    header = byte_order.encode("ascii") + struct.pack(f"{prefix}HI", 42, 8)
    value_offset = 8 + 2 + (2 * 12) + 4
    orientation = struct.pack(f"{prefix}HHI", 0x0112, 3, 1)
    orientation += struct.pack(f"{prefix}H", 6) + b"\x00\x00"
    resolution = struct.pack(f"{prefix}HHII", 0x011A, 5, 1, value_offset)
    first_ifd = struct.pack(f"{prefix}H", 2)
    first_ifd += orientation + resolution + struct.pack(f"{prefix}I", 0)
    rational = struct.pack(f"{prefix}II", 300, 1)
    return BytesIO(header + first_ifd + rational)


def _tiff_with_jpeg_thumbnail() -> tuple[BytesIO, bytes]:
    thumbnail_stream = BytesIO()
    Image.new("RGB", (3, 2), "blue").save(thumbnail_stream, format="JPEG")
    thumbnail = thumbnail_stream.getvalue()
    thumbnail_ifd_offset = 26
    thumbnail_offset = thumbnail_ifd_offset + 2 + (3 * 12) + 4
    image_ifd = struct.pack("<H", 1)
    image_ifd += struct.pack("<HHI", 0x0112, 3, 1) + struct.pack("<H", 1) + b"\0\0"
    image_ifd += struct.pack("<I", thumbnail_ifd_offset)
    thumbnail_ifd = struct.pack("<H", 3)
    thumbnail_ifd += struct.pack("<HHI", 0x0103, 3, 1) + b"\x06\0\0\0"
    thumbnail_ifd += struct.pack("<HHII", 0x0201, 4, 1, thumbnail_offset)
    thumbnail_ifd += struct.pack("<HHII", 0x0202, 4, 1, len(thumbnail))
    thumbnail_ifd += struct.pack("<I", 0)
    stream = BytesIO(
        b"II*\0" + struct.pack("<I", 8) + image_ifd + thumbnail_ifd + thumbnail
    )
    return stream, thumbnail


def test_process_file_parses_pillow_generated_jpeg_exif() -> None:
    stream = _pillow_jpeg_with_exif()

    tags = EXIF.process_file(stream)

    assert tags["Image Make"].printable == "Phatch Camera"
    assert tags["Image Orientation"].values == [6]
    assert tags["Image Orientation"].printable == "Rotated 90 CW"
    assert tags["Image DateTimeOriginal"].printable == "2026:09:11 12:34:56"


@pytest.mark.parametrize("byte_order", ["II", "MM"])
def test_process_file_parses_tiff_endian_and_rational(byte_order: str) -> None:
    stream = _tiff_with_orientation_and_rational(byte_order)

    tags = EXIF.process_file(stream)

    assert tags["Image Orientation"].values == [6]
    assert tags["Image Orientation"].field_offset == 18
    resolution = tags["Image XResolution"].values[0]
    assert (resolution.num, resolution.den) == (300, 1)
    assert str(resolution) == "300"


def test_process_file_extracts_embedded_jpeg_thumbnail() -> None:
    stream, expected_thumbnail = _tiff_with_jpeg_thumbnail()

    tags = EXIF.process_file(stream)

    thumbnail = tags["JPEGThumbnail"]
    assert sha256(thumbnail).digest() == sha256(expected_thumbnail).digest()
    with Image.open(BytesIO(thumbnail)) as image:
        assert image.size == (3, 2)


@pytest.mark.parametrize(
    "payload",
    [
        b"not an image stream",
        b"\xff\xd8",
        b"\xff\xd8\xff\xe0\x00\x04JFIF\0\0",
        b"\xff\xd8\xff\xe0\x00\x10JFIF",
        b"II*\x00",
    ],
)
def test_process_file_rejects_malformed_or_truncated_stream(payload: bytes) -> None:
    assert EXIF.process_file(BytesIO(payload)) == {}
