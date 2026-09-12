import runpy
import struct
import sys
from io import BytesIO

import pytest

from phatch.other import EXIF


def _raw_ifd(entries: list[tuple[int, int, bytes]], start: int = 0) -> bytes:
    data_offset = start + 2 + (12 * len(entries)) + 4
    encoded_entries = bytearray()
    extra_data = bytearray()
    for tag, field_type, value in entries:
        type_length = EXIF.FIELD_TYPES[field_type][0]
        count = len(value) // type_length
        encoded_entries.extend(struct.pack("<HHI", tag, field_type, count))
        if len(value) <= 4:
            encoded_entries.extend(value.ljust(4, b"\0"))
        else:
            encoded_entries.extend(struct.pack("<I", data_offset + len(extra_data)))
            extra_data.extend(value)
    return (
        struct.pack("<H", len(entries))
        + encoded_entries
        + struct.pack("<I", 0)
        + extra_data
    )


def _maker_header(
    make: str, data: bytes, note_values: list[int], field_offset: int = 0
) -> EXIF.EXIF_header:
    header = EXIF.EXIF_header(BytesIO(data), "I", 0, False, False)
    header.tags["Image Make"] = EXIF.IFD_Tag(make, 0x010F, 2, make, 0, len(make))
    header.tags["EXIF MakerNote"] = EXIF.IFD_Tag(
        str(note_values), 0x927C, 7, note_values, field_offset, len(note_values)
    )
    return header


def test_nikon_type_one_makernote_decodes_older_tags(capsys) -> None:
    prefix = b"Nikon\0\x01\0"
    note = list(prefix + _raw_ifd([]))
    data = prefix + _raw_ifd([(0x0003, 3, struct.pack("<H", 1))], start=8)
    header = _maker_header("NIKON", data, note)
    header.debug = True

    header.decode_maker_note()

    assert header.tags["MakerNote Quality"].printable == "VGA Basic"
    assert "type 1 Nikon" in capsys.readouterr().out


def test_nikon_unlabeled_and_invalid_labeled_makernotes(capsys) -> None:
    data = _raw_ifd([(0x0004, 2, b"FINE\0")])
    header = _maker_header("NIKON", data, list(data))

    header.decode_maker_note()

    assert header.tags["MakerNote Quality"].values == "FINE"

    invalid = list(b"Nikon\0\x02" + b"\0" * 10)
    header = _maker_header("NIKON", bytes(invalid), invalid)
    header.debug = True
    with pytest.raises(ValueError, match="Missing marker"):
        header.decode_maker_note()
    assert "labeled type 2 Nikon" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("make", "prefix", "tag", "field_type", "value", "key", "expected"),
    [
        ("OLYMPUS", b"OLYMPUS\0", 0x0201, 3, struct.pack("<H", 3), "JPEGQual", "SHQ"),
        ("CASIO", b"", 0x0002, 3, struct.pack("<H", 3), "Quality", "Fine"),
        (
            "FUJIFILM",
            b"FUJIFILM\0\0\0\0",
            0x1002,
            3,
            struct.pack("<H", 256),
            "WhiteBalance",
            "Daylight",
        ),
    ],
)
def test_vendor_makernotes_decode_known_values(
    make: str,
    prefix: bytes,
    tag: int,
    field_type: int,
    value: bytes,
    key: str,
    expected: str,
) -> None:
    start = len(prefix)
    data = prefix + _raw_ifd([(tag, field_type, value)], start=start)
    header = _maker_header(make, data, list(data))

    header.decode_maker_note()

    assert header.tags[f"MakerNote {key}"].printable == expected


def test_canon_makernote_expands_camera_settings() -> None:
    camera_settings = struct.pack("<4H", 0, 1, 7, 3)
    shot_settings = struct.pack("<16H", *([0] * 7 + [1] + [0] * 8))
    data = _raw_ifd([(0x0001, 3, camera_settings), (0x0004, 3, shot_settings)])
    header = _maker_header("Canon", data, list(data))

    header.decode_maker_note()

    assert header.tags["MakerNote Macromode"].printable == "Macro"
    assert header.tags["MakerNote WhiteBalance"].printable == "Sunny"


@pytest.mark.parametrize("arguments", [[], ["--help"], ["--unknown"]])
def test_cli_usage_paths_exit(monkeypatch, capsys, arguments: list[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["EXIF.py", *arguments])

    with pytest.raises(SystemExit):
        runpy.run_module("phatch.other.EXIF", run_name="__main__")

    assert "Usage: EXIF.py" in capsys.readouterr().out


def test_cli_parses_real_tiff_file(monkeypatch, tmp_path, capsys) -> None:
    path = tmp_path / "sample.tiff"
    ifd = _raw_ifd([(0x0112, 3, struct.pack("<H", 6))], start=8)
    path.write_bytes(b"II*\0" + struct.pack("<I", 8) + ifd)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "EXIF.py",
            "--quick",
            "--strict",
            "--stop-tag",
            "Orientation",
            "--debug",
            str(path),
        ],
    )

    runpy.run_module("phatch.other.EXIF", run_name="__main__")

    output = capsys.readouterr().out
    assert "Image Orientation" in output
    assert "Rotated 90 CW" in output


def test_cli_reports_unreadable_file(monkeypatch, tmp_path, capsys) -> None:
    missing = tmp_path / "missing.jpg"
    monkeypatch.setattr(sys, "argv", ["EXIF.py", str(missing)])

    runpy.run_module("phatch.other.EXIF", run_name="__main__")

    assert "is unreadable" in capsys.readouterr().out
