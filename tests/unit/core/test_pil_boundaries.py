from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar
from unittest.mock import Mock

import pytest
from PIL import Image

from phatch.core import pil
from tests.unit.core.test_pil_behavior import info_photo, layer, photo


class MetadataDump:
    def __init__(self, values=None, error: Exception | None = None) -> None:
        self.values = values or {}
        self.error = error

    def open(self, path, sources):
        if self.error:
            raise self.error
        return SimpleNamespace(dump=lambda free: self.values)


class NativeImage(dict):
    def readMetadata(self) -> None:
        self["read"] = True


def test_info_constructor_covers_native_and_plain_metadata(monkeypatch) -> None:
    image = Image.new("RGB", (2, 3))
    native = NativeImage()
    monkeypatch.setattr(pil, "pyexiv2", SimpleNamespace(Image=lambda path: native))
    monkeypatch.setattr(
        pil,
        "exif",
        SimpleNamespace(
            is_readable_format=lambda format_name: True,
            is_writable_format_exif=lambda format_name: True,
        ),
    )
    info = pil.InfoPhoto(
        {"path": "source.jpg", "format": "JPEG"},
        MetadataDump({"custom": 3}),
        lambda: image,
        image,
    )
    assert info["custom"] == 3
    assert info.writable
    assert native["Exif.Image.Software"] == pil.TITLE

    monkeypatch.setattr(pil, "exif", False)
    plain = pil.InfoPhoto(
        {"path": "source.jpg", "format": "JPEG"},
        MetadataDump(),
        lambda: image,
    )
    assert plain.pyexiv2 is None


def test_info_constructor_reports_extraction_failure() -> None:
    image = Image.new("RGB", (1, 1))
    with pytest.raises(Exception, match=r"source\.jpg"):
        pil.InfoPhoto(
            {"path": "source.jpg"},
            MetadataDump(error=RuntimeError("broken")),
            lambda: image,
            image,
        )


def test_info_update_dirty_and_delete_paths(monkeypatch) -> None:
    image = Image.new("P", (2, 2))
    image.info["transparency"] = 4
    info = info_photo(image)
    info.update({"plain": 1}, explicit=False)
    info.writable_exif = True
    info.pyexiv2 = {"Exif.Photo.Test": "old"}
    monkeypatch.setattr(pil.metadata, "is_writable_tag", lambda tag: True)
    monkeypatch.setattr(
        pil.metadata, "is_writeable_not_exif_tag", lambda tag, mode: True
    )
    info.update({"second": 2})
    assert info["second"] == 2
    info._dirty = False
    del info["transparency"]
    dict.__setitem__(info, "Exif_Photo_Test", "old")
    del info["Exif_Photo_Test"]
    assert info.pyexiv2["Exif.Photo.Test"] is None
    del info["missing"]


def test_info_clean_state_checks_unchanged_size() -> None:
    info = info_photo(Image.new("RGB", (2, 2)))
    info.writable_exif = True

    assert info.is_dirty() is False


def test_info_orientation_readonly_and_native_write_failure(monkeypatch) -> None:
    info = info_photo(Image.new("RGB", (2, 2)))
    monkeypatch.setattr(pil.metadata, "is_writable_tag", lambda tag: True)
    monkeypatch.setattr(
        pil.metadata, "is_writeable_not_exif_tag", lambda tag, mode: True
    )
    info["orientation"] = 1
    with pytest.raises(KeyError, match="read only"):
        info["width"] = 4
    info.pyexiv2 = Mock()
    info.pyexiv2.__setitem__ = Mock(side_effect=RuntimeError("native"))
    with pytest.raises(KeyError, match="Impossible"):
        info["Exif_Image_Test"] = 3


def test_info_save_same_and_new_target(monkeypatch) -> None:
    info = info_photo(Image.new("RGB", (2, 2)))
    info.pyexiv2 = {"native": True}
    info._dirty = True
    info._flushed = False
    native = SimpleNamespace(
        flush=Mock(return_value=("flush",)),
        write_metadata=Mock(return_value=("write",)),
    )
    monkeypatch.setattr(pil, "exif", native)
    monkeypatch.setattr(pil, "pyexiv2", SimpleNamespace())
    assert info.save("source.png", thumbdata=b"thumb") == ("flush",)
    assert info.save("other.png", "PNG") == ("write",)
    monkeypatch.setattr(pil, "exif", False)
    with pytest.raises(ImportError):
        info.save("other.png")


def test_photo_save_infers_format_timestamp_dpi_and_layer_default(
    tmp_path: Path,
) -> None:
    item = photo(Image.new("RGB", (2, 2), "blue"))
    alternate = layer(Image.new("RGB", (1, 1)))
    item.current_layer_name = "alternate"
    item.set_layer(alternate)
    item.__dict__["modify_date"] = 1_600_000_000
    destination = tmp_path / "result.png"
    item.save(str(destination), dpi=(72, 72))
    assert destination.exists()
    assert destination.stat().st_mtime_ns == 1_600_000_000_000_000_000
    assert item.info["dpi"] == 72
    assert item.report_files[-1]["path"] == str(destination)


def test_photo_mode_paths_and_safe_mode(monkeypatch) -> None:
    item = photo(Image.new("RGB", (2, 2)))
    item.convert("RGB")
    item.convert("P")
    item.convert("P")
    item.safe_mode("JPEG")
    image = item.get_layer().image
    assert image is not None
    assert image.mode == "RGB"

    non_palette = photo(Image.new("RGB", (2, 2)))
    non_palette.convert("L")
    converted = non_palette.get_layer().image
    assert converted is not None
    assert converted.mode == "L"


def test_photo_save_logs_mode_conversion(tmp_path: Path) -> None:
    item = photo(Image.new("RGB", (2, 2), "blue"))
    item.info.log = Mock()

    item.save(str(tmp_path / "result.gif"), format="GIF")

    item.info.log.assert_called()


class TempFile:
    created: ClassVar[list[TempFile]] = []

    def __init__(self, extension, output_filename=None) -> None:
        self.path = output_filename or f"temporary.{extension}"
        self.closed = False
        self.created.append(self)

    def close(self) -> None:
        self.closed = True


def test_external_call_rewrites_inputs_and_loads_output(
    monkeypatch, tmp_path: Path
) -> None:
    item = photo(Image.new("RGB", (4, 4)))
    output = tmp_path / "output.png"
    TempFile.created.clear()
    monkeypatch.setattr(pil.system, "TempFile", TempFile)
    monkeypatch.setattr(
        pil.system, "call", lambda command, shell: output.write_bytes(b"x")
    )
    monkeypatch.setattr(pil.system, "fix_quotes", lambda value: value)
    monkeypatch.setattr(pil.imtools, "save_safely", lambda image, path: None)
    opened: list[str] = []
    current = item.get_layer()
    current.open = lambda uri: opened.append(uri)

    item.call(
        "tool file_in.png file_out.png",
        shell=False,
        size=(2, 2),
        output_filename=str(output),
        mode="RGBA",
    )
    assert opened == [str(output)]
    assert all(temp.closed for temp in TempFile.created)


def test_external_call_rejects_multiple_or_missing_outputs(monkeypatch) -> None:
    item = photo(Image.new("RGB", (2, 2)))
    monkeypatch.setattr(pil.system, "TempFile", TempFile)
    monkeypatch.setattr(pil.system, "call", lambda command, shell: None)
    monkeypatch.setattr(pil.system, "fix_quotes", lambda value: value)
    with pytest.raises(Exception, match="Only one"):
        item.call("tool file_out.png file_out.jpg", shell=False)
    with pytest.raises(Exception, match="did not produce"):
        item.call("tool file_out.png", shell=False)


def test_external_call_uses_default_shell_and_deduplicates_inputs(monkeypatch) -> None:
    item = photo(Image.new("RGB", (2, 2)))
    TempFile.created.clear()
    calls: list[bool] = []
    monkeypatch.setattr(pil.system, "TempFile", TempFile)
    monkeypatch.setattr(pil.system, "call", lambda command, shell: calls.append(shell))
    monkeypatch.setattr(pil.system, "fix_quotes", lambda value: value)
    monkeypatch.setattr(pil.imtools, "save_safely", lambda image, path: None)

    item.call("tool file_in.png file_in.png", mode="RGB")

    assert calls == [not pil.system.WINDOWS]
    assert len(TempFile.created) == 1
