from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import ClassVar

import pytest

from phatch.lib import metadata


class NativeValueError(ValueError):
    pass


class FakeNativeImage:
    created: ClassVar[list[FakeNativeImage]] = []

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.exif: dict[str, str] = {}
        self.iptc: dict[str, str] = {}
        self.comment = ""
        self.thumbnail: bytes | None = None
        self.calls: list[str] = []
        self.fail_exif: set[str] = set()
        self.fail_iptc: set[str] = set()
        self.fail_comment = False
        self.fail_thumbnail = False
        self.fail_write = False
        type(self).created.append(self)

    def readMetadata(self) -> None:
        self.calls.append("read")

    def writeMetadata(self) -> None:
        self.calls.append("write")
        if self.fail_write:
            raise OSError("metadata write failed")

    def exifKeys(self) -> list[str]:
        return list(self.exif)

    def iptcKeys(self) -> list[str]:
        return list(self.iptc)

    def _Image__getExifTag(self, tag: str) -> tuple[str, str]:
        return tag, self.exif[tag]

    def _Image__setExifTag(self, tag: str, value: str) -> None:
        if tag in self.fail_exif:
            raise NativeValueError("invalid EXIF value")
        self.exif[tag] = value

    def __getitem__(self, tag: str) -> str:
        return self.iptc[tag]

    def __setitem__(self, tag: str, value: str) -> None:
        if tag in self.fail_iptc:
            raise NativeValueError("invalid IPTC value")
        self.iptc[tag] = value

    def getComment(self) -> str:
        return self.comment

    def setComment(self, value: str) -> None:
        if self.fail_comment:
            raise NativeValueError("invalid comment")
        self.comment = value

    def getThumbnailData(self) -> bytes:
        if self.fail_thumbnail:
            raise NativeValueError("thumbnail unavailable")
        assert self.thumbnail is not None
        return self.thumbnail

    def setThumbnailData(self, value: bytes) -> None:
        if self.fail_thumbnail:
            raise NativeValueError("thumbnail rejected")
        self.thumbnail = value


@pytest.fixture
def adapter(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    FakeNativeImage.created.clear()

    class NativeModule(ModuleType):
        Image: type[FakeNativeImage]

    native = NativeModule("pyexiv2")
    native.Image = FakeNativeImage
    adapter_path = Path(__file__).parents[3] / "phatch" / "lib" / "_pyexiv2.py"
    module_name = "phatch.lib._pyexiv2_contract_test"
    spec = importlib.util.spec_from_file_location(module_name, adapter_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "pyexiv2", native)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("image_format", "readable", "writable", "exif", "iptc"),
    [
        (None, True, True, True, True),
        ("JPEG", True, True, True, True),
        ("TIFF", True, False, False, False),
        ("CR2", True, True, False, True),
        ("PNG", False, False, False, False),
    ],
)
def test_format_capabilities_match_native_provider_contract(
    adapter: ModuleType,
    image_format: str | None,
    readable: bool,
    writable: bool,
    exif: bool,
    iptc: bool,
) -> None:
    assert adapter.is_readable_format(image_format) is readable
    assert adapter.is_writable_format(image_format) is writable
    assert adapter.is_writable_format_exif(image_format) is exif
    assert adapter.is_writable_format_iptc(image_format) is iptc


@pytest.mark.parametrize(
    ("extension", "image_format"),
    [(".jpg", "JPEG"), (".jpe", "JPEG"), (".tif", "TIFF"), (".png", "PNG")],
)
def test_extension_conversion_normalizes_pillow_formats(
    adapter: ModuleType, extension: str, image_format: str
) -> None:
    assert adapter.extension_to_image_format(extension) == image_format


def test_copy_metadata_writes_valid_tags_thumbnail_and_comment(
    adapter: ModuleType,
) -> None:
    source = FakeNativeImage("source.jpg")
    source.exif = {"Exif.Image.Artist": "Ada"}
    source.iptc = {"Iptc.Application2.Caption": "portrait"}
    source.comment = "kept"

    warning = adapter._copy_metadata(
        source, "target.jpg", "JPEG", "JPEG", thumbdata=b"thumb"
    )

    target = FakeNativeImage.created[-1]
    assert warning == ""
    assert target.exif == source.exif
    assert target.iptc == source.iptc
    assert target.comment == "kept"
    assert target.thumbnail == b"thumb"
    assert target.calls == ["read", "write"]


def test_copy_metadata_filters_broken_exif_and_reports_invalid_tags(
    adapter: ModuleType,
) -> None:
    source = FakeNativeImage("source.jpg")
    source.exif = {"Exif.Canon.Tuple": "broken", "Exif.Image.Artist": "Ada"}
    source.iptc = {"Iptc.Application2.Caption": "portrait"}
    target = FakeNativeImage("prepared.jpg")
    target.fail_exif.add("Exif.Image.Artist")
    target.fail_iptc.add("Iptc.Application2.Caption")
    original_factory = adapter.pyexiv2.Image
    adapter.pyexiv2.Image = lambda filename: target
    try:
        warning = adapter._copy_metadata(
            source, "target.jpg", "JPEG", "JPEG", adapter.RE_BROKEN
        )
    finally:
        adapter.pyexiv2.Image = original_factory

    assert "Exif.Image.Artist: invalid EXIF value" in warning
    assert "Iptc.Application2.Caption: invalid IPTC value" in warning
    assert "Exif.Canon.Tuple" not in target.exif
    assert target.calls == ["read", "write"]


def test_copy_metadata_respects_source_and_target_format_boundaries(
    adapter: ModuleType,
) -> None:
    source = FakeNativeImage("source.png")
    source.exif = {"Exif.Image.Artist": "Ada"}
    source.iptc = {"Iptc.Application2.Caption": "portrait"}
    source.comment = "ignored"

    warning = adapter._copy_metadata(source, "target.cr2", "PNG", "CR2")

    target = FakeNativeImage.created[-1]
    assert warning == ""
    assert target.exif == {}
    assert target.iptc == {}
    assert target.comment == ""
    assert target.calls == ["read"]


def test_copy_metadata_reports_invalid_comment(adapter: ModuleType) -> None:
    source = FakeNativeImage("source.jpg")
    source.comment = "comment"
    target = FakeNativeImage("prepared.jpg")
    target.fail_comment = True
    original_factory = adapter.pyexiv2.Image
    adapter.pyexiv2.Image = lambda filename: target
    try:
        warning = adapter._copy_metadata(source, "target.jpg", "JPEG", "JPEG")
    finally:
        adapter.pyexiv2.Image = original_factory

    assert warning == "invalid comment\n"
    assert target.calls == ["read"]


def test_write_metadata_handles_empty_unsupported_warning_and_failure(
    adapter: ModuleType,
) -> None:
    assert adapter.write_metadata(None, "target.png", target_format="PNG") == ""
    assert adapter.write_metadata(None, "target.jpg", target_format="JPEG") == ""

    source = FakeNativeImage("source.jpg")
    source.exif = {"Exif.Canon.Tuple": "broken", "Exif.Image.Artist": "Ada"}
    target = FakeNativeImage("prepared.jpg")
    target.fail_exif.add("Exif.Image.Artist")
    original_factory = adapter.pyexiv2.Image
    adapter.pyexiv2.Image = lambda filename: target
    try:
        warning = adapter.write_metadata(source, "target.jpg", "JPEG", "JPEG")
        target.fail_exif.clear()
        target.fail_write = True
        failure = adapter.write_metadata(source, "target.jpg", "JPEG", "JPEG")
    finally:
        adapter.pyexiv2.Image = original_factory

    assert warning.startswith("Saving metadata to target.jpg caused following issues:")
    assert "invalid EXIF value" in warning
    assert "Failed to save metadata to target.jpg" in failure
    assert "metadata write failed" in failure
    assert "Exif[.]Canon" in failure


def test_thumbnail_and_flush_surface_success_and_native_errors(
    adapter: ModuleType,
) -> None:
    image = FakeNativeImage("image.jpg")
    image.thumbnail = b"old"
    assert adapter.read_thumbdata(image) == b"old"
    assert adapter.write_thumbdata(image, None) == ""
    assert adapter.write_thumbdata(image, b"new") == ""
    assert image.thumbnail == b"new"

    image.fail_thumbnail = True
    assert adapter.read_thumbdata(image) is None
    assert adapter.write_thumbdata(image, b"bad") == "thumbnail rejected"
    image.fail_write = True
    assert adapter.flush(image, b"bad") == "thumbnail rejected\nmetadata write failed"


def test_datetime_tag_conversion_preserves_calendar_fields() -> None:
    converted = metadata.convert_from_string("2026:09:11 12:34:56")
    assert isinstance(converted, metadata.DateTime)
    assert (converted.year, converted.month, converted.day) == (2026, 9, 11)
    assert (converted.hour, converted.minute, converted.second) == (12, 34, 56)
    assert metadata.convert_from_string("not an EXIF date") == "not an EXIF date"
