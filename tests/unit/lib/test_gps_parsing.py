import datetime
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from xml.parsers.expat import ExpatError

import pytest

from phatch.lib import gps

PLAIN_GPX = """<?xml version="1.0"?>
<gpx><trk><trkseg>
<trkpt lat="51.5007" lon="-0.1246">
<ele>15.2</ele><time>2024-02-29T12:00:00Z</time></trkpt>
<trkpt lat="48.8584" lon="2.2945">
<ele>35.0</ele><time>2024-02-29T12:05:00Z</time></trkpt>
</trkseg></trk></gpx>
"""

NAMESPACED_GPX = """<?xml version="1.0"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>
<trkpt lat="-33.5" lon="151.25">
<ele>-12.3</ele><time>2024-02-29T10:20:30Z</time></trkpt>
</trkseg></trk></gpx>
"""


@dataclass(frozen=True, slots=True)
class RationalValue:
    numerator: int
    denominator: int


class FakePyexiv2:
    Rational = RationalValue


def write_gpx(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "track.gpx"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (
            PLAIN_GPX,
            {
                "2024-02-29T12:00:00Z": ["15.2", "51.5007", "-0.1246"],
                "2024-02-29T12:05:00Z": ["35.0", "48.8584", "2.2945"],
            },
        ),
        (
            NAMESPACED_GPX,
            {"2024-02-29T10:20:30Z": ["-12.3", "-33.5", "151.25"]},
        ),
    ],
)
def test_read_gpx_parses_known_coordinates_from_temporary_file(
    tmp_path: Path, content: str, expected: dict[str, list[str]]
) -> None:
    assert gps.read_gpx(write_gpx(tmp_path, content)) == expected


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("2024-02-29T11:59:00Z", "2024-02-29T12:00:00Z"),
        ("2024-02-29T12:00:00Z", "2024-02-29T12:00:00Z"),
        ("2024-02-29T12:02:00Z", "2024-02-29T12:05:00Z"),
        ("2024-02-29T12:06:00Z", "2024-02-29T12:05:00Z"),
    ],
)
def test_search_returns_documented_lower_bound_at_all_bounds(
    target: str, expected: str
) -> None:
    points = {
        "2024-02-29T12:00:00Z": ["15.2", "51.5007", "-0.1246"],
        "2024-02-29T12:05:00Z": ["35.0", "48.8584", "2.2945"],
    }

    assert gps.search(points, target) == expected


def test_parser_propagates_invalid_xml_and_missing_track_values(tmp_path: Path) -> None:
    with pytest.raises(ExpatError):
        gps.read_gpx(write_gpx(tmp_path, "<gpx>"))

    missing_elevation = """<gpx><trk><trkseg>
    <trkpt lat="1" lon="2"><time>2024-01-01T00:00:00Z</time></trkpt>
    </trkseg></trk></gpx>"""
    with pytest.raises(IndexError):
        gps.read_gpx(write_gpx(tmp_path, missing_elevation))


def test_empty_search_and_missing_file_propagate_native_errors(tmp_path: Path) -> None:
    with pytest.raises(IndexError):
        gps.search({}, "2024-01-01T00:00:00Z")
    with pytest.raises(FileNotFoundError):
        gps.read_gpx(tmp_path / "missing.gpx")


def test_coordinate_components_and_utc_shift_have_known_values() -> None:
    angle = 33.5
    instant = datetime.datetime(2024, 2, 29, 10, 20, 30, tzinfo=datetime.UTC)

    assert (gps.d(angle), gps.m(angle), gps.s(angle)) == (33, 30, 0)
    assert gps.get_xml_timez(instant, 90) == "2024-02-29T10:22:00Z"


def test_get_metadata_maps_known_southern_western_point_and_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gps, "pyexiv2", FakePyexiv2)
    instant = datetime.datetime(2024, 2, 29, 10, 20, 30, tzinfo=datetime.UTC)
    points = {"2024-02-29T10:20:30Z": ["-12.3", "-33.5", "-151.25"]}
    report = StringIO()

    metadata = gps.get_metadata(instant, points, 0, "photo.jpg", report)

    assert metadata["Exif_GPSInfo_GPSAltitude"] == RationalValue(123, 10)
    assert metadata["Exif_GPSInfo_GPSAltitudeRef"] == 1
    assert metadata["Exif_GPSInfo_GPSLatitude"] == [
        RationalValue(33, 1),
        RationalValue(30, 1),
        RationalValue(0, 1),
    ]
    assert metadata["Exif_GPSInfo_GPSLatitudeRef"] == "S"
    assert metadata["Exif_GPSInfo_GPSLongitude"] == [
        RationalValue(151, 1),
        RationalValue(15, 1),
        RationalValue(0, 1),
    ]
    assert metadata["Exif_GPSInfo_GPSLongitudeRef"] == "W"
    assert "photo.jpg" in report.getvalue()


def test_get_metadata_handles_positive_point_without_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(gps, "pyexiv2", FakePyexiv2)
    instant = datetime.datetime(2024, 2, 29, 10, 20, 30, tzinfo=datetime.UTC)
    points = {"2024-02-29T10:20:30Z": ["12.3", "33.5", "151.25"]}

    metadata = gps.get_metadata(instant, points, 0, "photo.jpg")

    assert metadata["Exif_GPSInfo_GPSAltitudeRef"] == 0
    assert metadata["Exif_GPSInfo_GPSLatitudeRef"] == "N"
    assert metadata["Exif_GPSInfo_GPSLongitudeRef"] == "E"


def test_get_metadata_requires_pyexiv2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gps, "pyexiv2", None)

    with pytest.raises(ImportError, match="pyexiv2 is not installed"):
        gps.get_metadata(datetime.datetime(2024, 1, 1), {}, 0, "photo.jpg")


def test_write_header_emits_csv_columns() -> None:
    report = StringIO()

    gps.write_header(report)

    assert report.getvalue() == (
        "camera time,nearest gps,latitude,longitude,elev,photofile\n"
    )
