from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PIL import Image, ImageFont

from phatch.actions import geotag, save, text, time_shift


def _save_action(monkeypatch, values):
    action = save.Action()
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "is_done_info", lambda _info: ("out", "out/image.ext", values["As"]))
    monkeypatch.setattr(action, "ensure_path_or_desktop", lambda _folder, _photo, filename, desktop=False: filename)
    return action


def test_geotag_reads_gpx_writes_report_and_reuses_cache(monkeypatch, tmp_path):
    report = tmp_path / "gps.csv"
    action = geotag.Action()
    photo = SimpleNamespace(info={"Exif_Image_DateTime": "date", "path": "image.jpg"})
    values = {"Time Shift (seconds)": 5, "GPS Data (gpx)": "track.gpx", "GPS Report (csv)": str(report)}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(geotag.gps, "write_header", lambda stream: stream.write("header\n"))
    monkeypatch.setattr(geotag.gps, "read_gpx", lambda path: {"path": path})
    monkeypatch.setattr(geotag.gps, "get_metadata", lambda *_args: {"Exif.GPS.Latitude": 1})
    cache = {}

    first = action.apply(photo, None, cache)
    second = action.apply(photo, None, cache)
    cache["gps_report"].close()

    assert first is second is photo
    assert photo.info["Exif_GPS_Latitude"] == 1
    assert report.read_text() == "header\n"


def test_geotag_accepts_empty_report_path(monkeypatch):
    action = geotag.Action()
    photo = SimpleNamespace(info={"Exif_Image_DateTime": "date", "path": "image.jpg"})
    values = {"Time Shift (seconds)": 0, "GPS Data (gpx)": "track.gpx", "GPS Report (csv)": " "}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(geotag.gps, "read_gpx", lambda _path: {})
    monkeypatch.setattr(geotag.gps, "get_metadata", lambda *_args: {})
    cache = {}

    action.apply(photo, None, cache)

    assert cache["gps_report"] == ""


@pytest.mark.parametrize(
    ("extension", "fields"),
    [
        ("PNG", {"PNG Optimize"}),
        ("JPEG", {"Metadata", "JPEG Quality"}),
        ("TIFF", {"TIFF Compression", "Metadata"}),
    ],
)
def test_save_relevant_fields_follow_output_format(monkeypatch, extension, fields):
    action = save.Action()
    values = {"As": extension, "Show Type Options": "false", "TIFF Compression": "none"}
    monkeypatch.setattr(action, "get_field_string", lambda label: values[label])
    monkeypatch.setattr(action, "get_format", lambda ext: ext)

    labels = set(action.get_relevant_field_labels())

    assert fields <= labels


def test_save_type_options_reveal_all_advanced_fields(monkeypatch):
    action = save.Action()
    values = {"As": action.TYPE, "Show Type Options": "true", "TIFF Compression": "zip"}
    monkeypatch.setattr(action, "get_field_string", lambda label: values[label])
    monkeypatch.setattr(action, "get_format", lambda _ext: None)

    labels = action.get_relevant_field_labels()

    assert "PNG Optimize" in labels
    assert "JPEG Quality" in labels
    assert "TIFF Compression" in labels


def test_save_get_format_resolves_source_type(monkeypatch):
    action = save.Action()
    photo = SimpleNamespace(info={"format": "JPEG"})
    monkeypatch.setattr(save.imtools, "get_format", lambda extension: extension.lower())

    assert action.get_format(action.TYPE) is None
    assert action.get_format(action.TYPE, photo) == "jpeg"


def test_save_skips_existing_output_without_overwrite(monkeypatch):
    action = save.Action()
    photo = SimpleNamespace(info={})
    monkeypatch.setattr(action, "is_done_info", lambda _info: ("out", "existing.jpg", "JPEG"))
    monkeypatch.setattr(action, "get_format", lambda *_args: "JPEG")
    monkeypatch.setattr(save.os.path, "exists", lambda _path: True)

    result = action.apply(photo, lambda _key: False, {})

    assert result is photo


@pytest.mark.parametrize("output_format", ["PNG", "JPEG", "TIFF"])
def test_save_applies_format_specific_options(monkeypatch, output_format):
    values = {"As": output_format, "Resolution": 72, "Metadata": True, "PNG Optimize": True, "JPEG Size Maximum": 100, "JPEG Quality": 90, "JPEG Size Tolerance": 5, "TIFF Compression": "zip"}
    action = _save_action(monkeypatch, values)
    photo = SimpleNamespace(info={}, save=MagicMock(), get_flattened_image=lambda: Image.new("RGB", (2, 2)))
    monkeypatch.setattr(action, "get_format", lambda *_args: output_format)
    monkeypatch.setattr(save.os.path, "exists", lambda _path: False)
    monkeypatch.setattr(save, "get_size", lambda *_args, **_kwargs: 200)
    monkeypatch.setattr(save, "get_quality", lambda *_args, **_kwargs: 75)

    action.apply(photo, lambda key: key == "overwrite_existing_images", {})

    options = photo.save.call_args.kwargs
    assert options["format"] == output_format


def test_save_retries_invalid_format_as_png(monkeypatch):
    values = {"As": "BAD", "Resolution": 72, "Metadata": False}
    action = _save_action(monkeypatch, values)
    photo = SimpleNamespace(info={}, save=MagicMock(side_effect=[save.InvalidWriteFormatError(), None]), log=MagicMock())
    monkeypatch.setattr(action, "get_format", lambda *_args: "BAD")
    monkeypatch.setattr(save.os.path, "exists", lambda _path: False)

    result = action.apply(photo, lambda key: key == "overwrite_existing_images", {})

    assert result is photo
    assert photo.save.call_args.kwargs["format"] == "PNG"


def test_text_uses_font_and_orientation(monkeypatch):
    image = Image.new("RGB", (20, 20), "white")
    font = ImageFont.load_default()
    monkeypatch.setattr(text.ImageFont, "truetype", lambda *_args: font)

    result = text.draw_text(image, "x", 0, 0, "Left", "Top", 10, orientation="ROTATE_90", font="font.ttf")

    assert result.size == image.size


def test_text_uses_legacy_textsize_after_bbox_error(monkeypatch):
    class LegacyDraw:
        def textbbox(self, *_args, **_kwargs):
            raise ValueError("unsupported")

        def textsize(self, *_args, **_kwargs):
            return 4, 5

        def text(self, *_args, **_kwargs):
            return None

    image = Image.new("RGB", (20, 20), "white")
    monkeypatch.setattr(text.ImageDraw, "Draw", lambda _image: LegacyDraw())

    result = text.draw_text(image, "x", 0, 0, "Left", "Top", 10, font="")

    assert result is image


def test_text_estimates_size_when_pillow_has_no_measurement_api(monkeypatch):
    class MinimalDraw:
        def text(self, *_args, **_kwargs):
            return None

    font = SimpleNamespace(size=7)
    image = Image.new("RGB", (20, 20), "white")
    monkeypatch.setattr(text.ImageDraw, "Draw", lambda _image: MinimalDraw())
    monkeypatch.setattr(text.ImageFont, "truetype", lambda *_args: font)

    result = text.draw_text(image, "xx", 0, 0, "Left", "Top", 10, font="font.ttf")

    assert result is image


def test_text_values_uses_average_dimension_as_pixel_reference(monkeypatch):
    action = text.Action()
    monkeypatch.setattr(text.models.Action, "values", lambda self, info, pixel_fields=None, exclude=None: pixel_fields)

    result = action.values({"size": (100, 50)})

    assert result == {
        "Size": 75,
        "Horizontal Offset": 100,
        "Vertical Offset": 50,
    }


def test_time_shift_falls_back_when_exif_datetime_missing(monkeypatch):
    action = time_shift.Action()
    info = {"year": 2020, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}
    photo = SimpleNamespace(info=info)
    values = {"Change": time_shift.OPTIONS[2], "Use exif datetime": True, "Seconds": 0, "Minutes": 0, "Hours": 0, "Days": 0, "Months": 0, "Years": 0}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])

    result = action.apply(photo, None, {})

    assert result is photo
    assert "Exif_Image_DateTime" in info
