from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from phatch.core import pil


def info_photo(image: Image.Image) -> pil.InfoPhoto:
    info = pil.InfoPhoto.__new__(pil.InfoPhoto)
    dict.__init__(info, path="source.png", format="PNG", orientation=1)
    info.get_pil = lambda: image
    info.pyexiv2 = None
    info.writable = False
    info.writable_exif = False
    info.writable_iptc = False
    info._original_size = image.size
    info._dirty = False
    info._flushed = True
    info._log = ""
    return info


def layer(image: Image.Image) -> pil.Layer:
    result = pil.Layer.__new__(pil.Layer)
    result.image = image
    return result


def photo(image: Image.Image) -> pil.Photo:
    result = pil.Photo.__new__(pil.Photo)
    background = layer(image)
    result.modify_date = None
    result.report_files = []
    result._exif_transposition_reverse = None
    result.current_layer_name = "background"
    result.layers = {"background": background}
    result.info = info_photo(image)
    result.info.get_pil = result.get_flattened_image
    return result


def test_image_helpers_and_variable_partition(tmp_path: Path, monkeypatch) -> None:
    image = Image.new("RGB", (3, 4))
    path = tmp_path / "photo.png"
    image.save(path)
    monkeypatch.setattr(
        pil.metadata,
        "InfoExtract",
        lambda filename, vars: SimpleNamespace(dump=lambda: {}),
    )
    monkeypatch.setattr(pil, "Photo", lambda info: info)

    assert pil.image_to_dict(str(path)) == {
        "path": str(path),
        "filename": "photo.png",
    }
    assert pil.image_to_dict(str(path), image)["height"] == 4
    assert pil.get_photo(str(path)) == {}
    static, dynamic = pil.split_vars_static_dynamic(("path", "width", "mode"))
    assert set(static) == {"path"}
    assert set(dynamic) == {"width", "mode"}


def test_info_dynamic_values_orientation_and_contains() -> None:
    image = Image.new("P", (3, 4))
    image.info["transparency"] = 7
    info = info_photo(image)
    dict.__setitem__(info, "Exif_Image_Orientation", 6)

    assert info["size"] == (3, 4)
    assert info["width"] == 3
    assert info["height"] == 4
    assert info["mode"] == "P"
    assert info["transparency"] == 7
    assert info["orientation"] == 6
    assert "transparency" in info
    assert "width" in info
    assert "absent" not in info


def test_info_mutation_logging_and_size(monkeypatch) -> None:
    image = Image.new("RGB", (3, 4))
    info = info_photo(image)
    info.writable_exif = True
    info.writable = True
    info.pyexiv2 = {}
    monkeypatch.setattr(pil.metadata, "is_writable_tag", lambda tag: True)
    monkeypatch.setattr(
        pil.metadata, "is_writeable_not_exif_tag", lambda tag, mode: True
    )
    info["custom"] = "value"
    assert info.is_dirty()
    info._dirty = False
    image = Image.new("RGB", (5, 6))
    info.get_pil = lambda: image
    info.update_size()
    assert info.pyexiv2["Exif.Photo.PixelXDimension"] == 5
    assert info.pyexiv2["Exif.Photo.PixelYDimension"] == 6
    info.log("message")
    assert info.get_log() == "message\n"
    info.clear_log()
    assert info.get_log() == ""
    assert pil.InfoPhoto._fix("Exif_Image_Orientation") == "Exif.Image.Orientation"


def test_info_transparency_and_writable_failures(monkeypatch) -> None:
    image = Image.new("RGB", (2, 2))
    info = info_photo(image)
    with pytest.raises(KeyError):
        info.assert_transparency()
    monkeypatch.setattr(pil.metadata, "is_writable_tag", lambda tag: False)
    with pytest.raises(pil.NotWritableTagError):
        info.assert_writable("invalid")
    monkeypatch.setattr(pil.metadata, "is_writable_tag", lambda tag: True)
    monkeypatch.setattr(
        pil.metadata, "is_writeable_not_exif_tag", lambda tag, mode: False
    )
    with pytest.raises(pil.NotWritableTagError):
        info.assert_writable("Exif_Image_Test")


def test_photo_layer_image_and_report_operations(tmp_path: Path, monkeypatch) -> None:
    image = Image.new("RGBA", (3, 4), "red")
    item = photo(image)
    item.info.log = Mock()
    item.info.clear_log = Mock()
    item.info.get_log = Mock(return_value="log")

    item.log("message")
    item.clear_log()
    assert item.get_log() == "log"
    assert item.get_filename("out", "name", "png") == "out/name.png"
    assert item.get_layer().image is image
    alternate = layer(Image.new("RGB", (1, 1)))
    item.set_layer(alternate, "alternate")
    assert item.get_layer("alternate") is alternate
    monkeypatch.setattr(pil.thumbnail, "thumbnail", lambda image, **kwargs: image)
    assert item.get_thumb((2, 2)).size == (3, 4)
    output = tmp_path / "output.png"
    item.append_to_report(str(output), image)
    assert item.report_files[0]["source"] == "source.png"


def test_photo_converts_resizes_rotates_and_applies(monkeypatch) -> None:
    item = photo(Image.new("RGBA", (4, 5)))
    second = layer(Image.new("RGB", (2, 3)))
    item.layers["second"] = second
    item.convert("P")
    images = [entry.image for entry in item.layers.values()]
    assert all(image is not None and image.mode == "P" for image in images)
    assert item.info["transparency"] == 255
    item.resize((0, 2), Image.Resampling.NEAREST)
    images = [entry.image for entry in item.layers.values()]
    assert all(image is not None and image.size == (1, 2) for image in images)
    monkeypatch.setattr(
        pil.imtools, "get_exif_transposition", lambda value: ((0,), (1,))
    )
    monkeypatch.setattr(pil.imtools, "transpose", lambda image, value: image)
    item.rotate_exif()
    assert item._exif_transposition_reverse == (1,)
    item.rotate_exif(reverse=True)
    item.apply_pil(lambda image: image.convert("L"))
    images = [entry.image for entry in item.layers.values()]
    assert all(image is not None and image.mode == "L" for image in images)


def test_layer_opens_converts_and_applies(tmp_path: Path) -> None:
    path = tmp_path / "float.tiff"
    Image.new("F", (2, 2)).save(path)
    layer = pil.Layer(str(path), load=False)
    assert layer.image is not None
    assert layer.image.mode == "L"
    layer.apply_pil(lambda image, mode: image.convert(mode), "RGB")
    assert layer.image is not None
    assert layer.image.mode == "RGB"


def test_info_close_and_photo_close_remove_cycles() -> None:
    item = photo(Image.new("RGB", (1, 1)))
    item.close()
    assert not hasattr(item, "info")
