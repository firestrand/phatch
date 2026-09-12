from __future__ import annotations

import builtins
import importlib
import subprocess
import sys
from importlib import util
from types import ModuleType

import pytest

import phatch.lib.pyWx as lib_pywx_package
import phatch.pyWx as pywx_package
from phatch.pyWx import dialog_service


def test_dialog_service_imports_when_wx_is_unavailable() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.modules['wx'] = None; "
            "from phatch.pyWx.dialog_service import DialogDependencies; "
            "print(DialogDependencies.__name__)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "DialogDependencies"


def test_dialog_service_imports_without_preinstalled_gettext_fallback() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import builtins; builtins.__dict__.pop('_', None); "
            "from phatch.core import ct; "
            "from phatch.pyWx.dialog_service import DialogDependencies; "
            "print(DialogDependencies.__name__)",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "DialogDependencies"


def test_headless_fallback_dependencies_are_instance_safe(monkeypatch) -> None:
    original_import = importlib.import_module

    def without_wx(name: str, package: str | None = None) -> ModuleType:
        if name == "wx" or name.startswith("wx."):
            raise ModuleNotFoundError("wx unavailable", name="wx")
        return original_import(name, package)

    monkeypatch.setattr(importlib, "import_module", without_wx)
    spec = util.spec_from_file_location(
        "headless_dialog_service", dialog_service.__file__
    )
    assert spec is not None and spec.loader is not None
    loaded = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, loaded)
    spec.loader.exec_module(loaded)

    first = loaded.DialogDependencies()
    second = loaded.DialogDependencies()

    assert first.wx is not second.wx
    assert first.wx_lib_dialogs is not second.wx_lib_dialogs
    assert first.dialogs is not second.dialogs
    assert first.graphics is not second.graphics
    assert first.images is not second.images
    assert first.list_data is second.list_data
    assert first.notify is second.notify
    assert first.system is second.system
    assert first.api is second.api


def test_imported_wx_dependencies_remain_shared_module_defaults(
    monkeypatch,
) -> None:
    fake_graphics = ModuleType("phatch.lib.pyWx.graphics")
    fake_dialogs = ModuleType("phatch.pyWx.dialogs")
    fake_images = ModuleType("phatch.pyWx.images")
    fake_images.__dict__["ICON_PHATCH_64"] = None
    fake_wx = ModuleType("wx")
    fake_wx_lib = ModuleType("wx.lib")
    fake_wx_dialogs = ModuleType("wx.lib.dialogs")
    fake_wx.__dict__["lib"] = fake_wx_lib
    fake_wx_lib.__dict__["dialogs"] = fake_wx_dialogs
    monkeypatch.setattr(lib_pywx_package, "graphics", fake_graphics, raising=False)
    monkeypatch.setattr(pywx_package, "dialogs", fake_dialogs, raising=False)
    monkeypatch.setattr(pywx_package, "images", fake_images, raising=False)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    monkeypatch.setitem(sys.modules, "wx.lib", fake_wx_lib)
    monkeypatch.setitem(sys.modules, "wx.lib.dialogs", fake_wx_dialogs)
    monkeypatch.delitem(__import__("builtins").__dict__, "_", raising=False)
    spec = util.spec_from_file_location(
        "dialog_service_with_wx", dialog_service.__file__
    )
    assert spec is not None and spec.loader is not None
    loaded = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, loaded)

    spec.loader.exec_module(loaded)

    first = loaded.DialogDependencies()
    second = loaded.DialogDependencies()
    assert first.wx is second.wx is fake_wx
    assert first.wx_lib_dialogs is second.wx_lib_dialogs is fake_wx_dialogs
    assert first.dialogs is second.dialogs is fake_dialogs
    assert first.graphics is second.graphics is fake_graphics
    assert first.images is second.images is fake_images


def test_broken_gui_helper_import_is_not_treated_as_headless(monkeypatch) -> None:
    fake_graphics = ModuleType("phatch.lib.pyWx.graphics")
    fake_wx = ModuleType("wx")
    fake_wx_lib = ModuleType("wx.lib")
    fake_wx_dialogs = ModuleType("wx.lib.dialogs")
    fake_wx.__dict__["lib"] = fake_wx_lib
    fake_wx_lib.__dict__["dialogs"] = fake_wx_dialogs
    monkeypatch.setattr(lib_pywx_package, "graphics", fake_graphics, raising=False)
    monkeypatch.setitem(sys.modules, "phatch.lib.pyWx.graphics", fake_graphics)
    monkeypatch.setitem(sys.modules, "wx", fake_wx)
    monkeypatch.setitem(sys.modules, "wx.lib", fake_wx_lib)
    monkeypatch.setitem(sys.modules, "wx.lib.dialogs", fake_wx_dialogs)
    original_import = builtins.__import__

    def fail_helper(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "phatch.pyWx" and "dialogs" in fromlist:
            raise ImportError("broken dialog helper")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_helper)
    spec = util.spec_from_file_location(
        "dialog_service_with_broken_helper", dialog_service.__file__
    )
    assert spec is not None and spec.loader is not None
    loaded = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, loaded)

    with pytest.raises(ImportError, match="broken dialog helper"):
        spec.loader.exec_module(loaded)
