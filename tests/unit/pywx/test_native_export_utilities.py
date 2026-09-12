from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import wx
import wx.tools.img2img as wx_img2img
from PIL import Image

from phatch.other.pyWx import img2img, img2py

pytestmark = [pytest.mark.unit, pytest.mark.requires_display]


def _import_generated_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("generated_test_image", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("compressed", [True, False])
def test_crunch_data_roundtrips_binary_payload(compressed: bool) -> None:
    # Given
    payload = bytes(range(256)) * 2

    # When
    encoded = img2py.crunch_data(payload, compressed)
    restored = ast.literal_eval(encoded)
    if compressed:
        restored = img2py.zlib.decompress(restored)

    # Then
    assert restored == payload
    assert all(len(line) <= 78 for line in encoded.splitlines())


def test_generated_python_image_module_roundtrips_png_bytes(
    wx_app: wx.App, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    source = tmp_path / "source.png"
    generated = tmp_path / "generated_image.py"
    Image.new("RGBA", (7, 5), (10, 20, 30, 128)).save(source)

    # When
    img2py.main(["-n", "Sample", "-i", str(source), str(generated)])
    module = _import_generated_module(generated)

    # Then
    assert module.getSampleData().startswith(b"\x89PNG\r\n\x1a\n")
    assert module.getSampleImage().GetSize() == wx.Size(7, 5)
    assert module.getSampleBitmap().IsOk()
    assert module.getSampleIcon().IsOk()
    message = f'Embedded {source} using "Sample" into {generated}'
    assert message in capsys.readouterr().out


def test_catalog_append_keeps_both_exported_images(
    wx_app: wx.App, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    generated = tmp_path / "catalog.py"
    Image.new("RGB", (3, 2), "red").save(first)
    Image.new("RGB", (4, 6), "blue").save(second)

    # When
    img2py.main(["-c", "-i", "-n", "First", str(first), str(generated)])
    img2py.main(["-a", "-c", "-n", "Second", str(second), str(generated)])
    img2py.main(
        ["-a", "-c", "-i", "-n", "First", str(first), str(generated)]
    )
    module = _import_generated_module(generated)

    # Then
    assert module.index == ["First", "Second", "First"]
    assert module.catalog["First"].getImage().GetSize() == wx.Size(3, 2)
    assert module.catalog["First"].getIcon().IsOk()
    assert module.catalog["Second"].getImage().GetSize() == wx.Size(4, 6)
    assert "First already in catalog" in capsys.readouterr().out


@pytest.mark.parametrize("args", [[], ["-h"], ["--invalid"], ["only-one-file"]])
def test_invalid_cli_arguments_print_usage(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    # Given / When
    img2py.main(args)

    # Then
    assert "Convert an image to PNG format" in capsys.readouterr().out


def test_failed_conversion_reports_reason_without_creating_output(
    wx_app: wx.App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    generated = tmp_path / "failed.py"
    monkeypatch.setattr(img2py.img2img, "convert", lambda *args: (False, "bad image"))

    # When
    img2py.main(["missing.png", str(generated)])

    # Then
    assert capsys.readouterr().out.strip() == "bad image"
    assert not generated.exists()


def test_uncompressed_catalog_infers_name_and_preserves_mask_message(
    wx_app: wx.App, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    source = tmp_path / "plain.png"
    generated = tmp_path / "plain_image.py"
    Image.new("RGB", (2, 3), "white").save(source)

    # When
    img2py.main(
        ["-u", "-c", "-m", "#ffffff", str(source), str(generated)]
    )
    module = _import_generated_module(generated)

    # Then
    assert module.index == ["plain"]
    assert module.getplainData().startswith(b"\x89PNG\r\n\x1a\n")
    output = capsys.readouterr().out
    assert "Using filename (plain) for catalog entry" in output
    assert "with mask #ffffff" in output


def test_appending_catalog_to_plain_module_catalogs_new_image(
    wx_app: wx.App, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given
    first = tmp_path / "first.png"
    second = tmp_path / "second.png"
    generated = tmp_path / "mixed.py"
    Image.new("RGB", (2, 2), "red").save(first)
    Image.new("RGB", (3, 3), "blue").save(second)
    img2py.main(["-n", "First", str(first), str(generated)])

    # When
    img2py.main(["-a", "-c", "-n", "Second", str(second), str(generated)])
    module = _import_generated_module(generated)

    # Then
    assert module.index == ["Second"]
    assert module.catalog["Second"].getImage().GetSize() == wx.Size(3, 3)
    assert "originally created without catalog" in capsys.readouterr().out


def test_export_without_name_uses_generic_accessors(
    wx_app: wx.App, tmp_path: Path
) -> None:
    # Given
    source = tmp_path / "generic.png"
    generated = tmp_path / "generic_image.py"
    Image.new("RGB", (5, 4), "green").save(source)

    # When
    img2py.main([str(source), str(generated)])
    module = _import_generated_module(generated)

    # Then
    assert module.getImage().GetSize() == wx.Size(5, 4)
    assert module.getData().startswith(b"\x89PNG\r\n\x1a\n")


def test_main_initializes_wx_when_no_application_is_reported(
    wx_app: wx.App, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    source = tmp_path / "source.png"
    generated = tmp_path / "initialized.py"
    Image.new("RGB", (1, 1), "black").save(source)
    created: list[wx.App] = []
    monkeypatch.setattr(img2py.wx, "GetApp", lambda: None)
    monkeypatch.setattr(
        img2py.wx,
        "PySimpleApp",
        lambda: created.append(wx_app) or wx_app,
    )

    # When
    img2py.main(["-n", "Initialized", str(source), str(generated)])

    # Then
    assert created == [wx_app]
    assert generated.exists()


def test_img2img_exports_current_wx_conversion_entrypoints() -> None:
    # Given / When / Then
    assert img2img.convert is wx_img2img.convert
    assert img2img.main is wx_img2img.main
