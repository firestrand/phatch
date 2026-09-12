from __future__ import annotations

import builtins
import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

if "_" not in builtins.__dict__:
    builtins.__dict__["_"] = lambda value: value


def droplet_module():
    return importlib.import_module("phatch.windows.droplet")


class FakeShortcutWriter:
    def __init__(self) -> None:
        self.specs = []

    def create(self, spec):
        self.specs.append(spec)
        return SimpleNamespace(path=spec.destination)


class FakeRegistrar:
    def __init__(self) -> None:
        self.registered = []
        self.removed = []

    def register(self, verb):
        self.registered.append(verb)
        return SimpleNamespace(targets=("folder", ".jpg"))

    def remove(self, verb):
        self.removed.append(verb)
        return SimpleNamespace(targets=(".jpg",))


def test_import_is_hermetic_without_wx_winreg_or_pywin32(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("wx", "winreg", "win32com", "win32com.client"):
        monkeypatch.delitem(sys.modules, name, raising=False)
    module = droplet_module()
    assert module.__name__ == "phatch.windows.droplet"
    assert "win32com.client" not in sys.modules


def test_launcher_prefers_installed_gui_then_pythonw_legacy(tmp_path: Path) -> None:
    module = droplet_module()
    gui = tmp_path / "phatch-gui.exe"
    python = tmp_path / "python.exe"
    pythonw = tmp_path / "pythonw.exe"
    legacy = tmp_path / "phatch.py"
    for path in (gui, python, pythonw, legacy):
        path.write_text("x", encoding="utf-8")

    installed = module.resolve_launcher(gui, python, legacy)
    gui.unlink()
    fallback = module.resolve_launcher(gui, python, legacy)

    assert installed.argv == (str(gui),)
    assert fallback.argv == (str(pythonw), str(legacy))


def test_launcher_reports_missing_routes(tmp_path: Path) -> None:
    module = droplet_module()
    with pytest.raises(module.DropletLauncherError):
        module.resolve_launcher(
            tmp_path / "gui.exe", tmp_path / "python.exe", tmp_path / "legacy.py"
        )


@pytest.mark.parametrize(
    ("creator", "expected"),
    [
        ("recent", ("-d", "recent")),
        ("inspector", ("-n",)),
    ],
)
def test_droplet_routes_use_argv(
    creator: str, expected: tuple[str, ...], tmp_path: Path
) -> None:
    module = droplet_module()
    writer = FakeShortcutWriter()
    launcher = module.Launcher((r"C:\Phatch\phatch-gui.exe",))

    getattr(module, f"create_phatch_{creator}_droplet")(
        str(tmp_path), writer=writer, launcher=launcher, icon=Path("icon.ico")
    )

    assert writer.specs[0].arguments == expected


def test_action_list_routes_preserve_path_and_description(tmp_path: Path) -> None:
    module = droplet_module()
    writer = FakeShortcutWriter()
    action_list = tmp_path / "holiday edits.phatch"
    module.create_phatch_droplet(
        str(action_list),
        str(tmp_path),
        writer=writer,
        launcher=module.Launcher(("gui.exe",)),
        icon=Path("icon.ico"),
    )
    assert writer.specs[0].arguments == ("-d", str(action_list))
    assert writer.specs[0].destination.name == "holiday edits.lnk"


def test_explorer_routes_construct_operation_at_call_time(tmp_path: Path) -> None:
    module = droplet_module()
    registrar = FakeRegistrar()
    action_list = tmp_path / "edit.phatch"

    result = module.create_phatch_explorer_action(
        str(action_list),
        registrar=registrar,
        launcher=module.Launcher(("gui.exe",)),
        extensions=(".jpg",),
    )

    assert result == "folder, jpg"
    assert registrar.registered[0].argv == ("gui.exe", "-d", str(action_list))
    assert registrar.registered[0].action_list == str(action_list)


def test_menu_reports_adapter_error_once(monkeypatch: pytest.MonkeyPatch) -> None:
    module = droplet_module()
    frame = SimpleNamespace(
        show_info=lambda message: pytest.fail(message),
        show_error=lambda message: errors.append(message),
    )
    errors: list[str] = []

    def fail():
        raise module.DropletLauncherError("failed")

    module.menu_file_export_explorer(frame, fail)
    assert errors == [module.EXTENSIONS_INSTALL_UNSUCCESFUL]


def test_operation_defaults_are_constructed_lazily(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = droplet_module()
    writer = FakeShortcutWriter()
    monkeypatch.setattr(module, "_launcher", lambda: module.Launcher(("gui.exe",)))
    monkeypatch.setattr(module, "_icon", lambda: Path("default.ico"))
    monkeypatch.setattr(module, "ShortcutWriter", lambda: writer)

    module.create_droplet("Recent", ("-d", "recent"), str(tmp_path))

    assert writer.specs[0].description == "Recent"
    assert writer.specs[0].icon_path == Path("default.ico")


def test_capability_message_is_shown_once(monkeypatch: pytest.MonkeyPatch) -> None:
    module = droplet_module()
    messages: list[str] = []
    frame = SimpleNamespace(show_info=messages.append)
    unavailable = SimpleNamespace(status=module.CapabilityStatus.UNAVAILABLE)
    available = SimpleNamespace(status=module.CapabilityStatus.AVAILABLE)
    monkeypatch.setattr(
        module, "Pywin32CapabilityProbe", lambda **kwargs: lambda: unavailable
    )
    assert module.win32_missing(frame)
    monkeypatch.setattr(
        module, "Pywin32CapabilityProbe", lambda **kwargs: lambda: available
    )
    assert not module.win32_missing(frame)
    assert messages == [module.WIN32_MISSING]


def test_all_explorer_operations_and_removal_use_expected_routes() -> None:
    module = droplet_module()
    registrar = FakeRegistrar()
    launcher = module.Launcher(("gui.exe",))

    recent = module.create_phatch_recent_explorer_action(
        registrar=registrar, launcher=launcher, extensions=(".jpg",)
    )
    inspector = module.create_phatch_inspect_explorer_action(
        registrar=registrar, launcher=launcher, extensions=(".jpg",)
    )
    module.remove_phatch_explorer_actions(
        "edit.phatch", registrar=registrar, extensions=(".jpg",)
    )

    assert recent == inspector == "folder, jpg"
    assert registrar.registered[0].argv == ("gui.exe", "-d", "recent")
    assert registrar.registered[1].argv == ("gui.exe", "-n")
    assert [verb.identity for verb in registrar.removed] == [
        "recent",
        "inspector",
        "action-list",
    ]


def test_menu_module_preserves_callbacks_and_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = droplet_module()
    menu_module = importlib.import_module("phatch.windows.droplet_menu")
    installed: list[tuple[str, str]] = []

    class Menu:
        def __init__(self) -> None:
            self.separators: list[int] = []

        def InsertSeparator(self, position: int) -> None:
            self.separators.append(position)

    class Frame:
        def __init__(self) -> None:
            self.menu_file_export = Menu()
            self.menu_item = []

        def install_menu_item(self, menu, name, label, method, tooltip, style):
            installed.append((name, label))
            assert callable(method)
            return len(installed)

    monkeypatch.setattr(
        menu_module.importlib,
        "import_module",
        lambda name: SimpleNamespace(ITEM_NORMAL=7),
    )
    frame = Frame()

    module.install(frame)

    assert [name for name, _ in installed] == [
        "menu_file_export_explorer_remove",
        "menu_file_export_explorer_inspector",
        "menu_file_export_explorer_recent",
        "menu_file_export_explorer_actionlist",
        "menu_file_export_droplet_inspector",
        "menu_file_export_droplet_recent",
        "menu_file_export_droplet_actionlist",
    ]
    assert frame.menu_file_export.separators == [4, 3]


def test_menu_callbacks_dispatch_once(monkeypatch: pytest.MonkeyPatch) -> None:
    menu_module = importlib.import_module("phatch.windows.droplet_menu")
    calls: list[tuple] = []
    frame = SimpleNamespace(
        filename="edit.phatch",
        is_save_not_ok=lambda: False,
        menu_file_export_droplet=lambda *args: calls.append(args),
        show_info=lambda message: calls.append(("info", message)),
        show_error=lambda message: calls.append(("error", message)),
    )
    monkeypatch.setattr(menu_module, "win32_missing", lambda frame: False)
    monkeypatch.setattr(
        menu_module,
        "remove_phatch_explorer_actions",
        lambda actionlist: calls.append(("remove", actionlist)),
    )
    monkeypatch.setattr(
        menu_module,
        "menu_file_export_explorer",
        lambda *args: calls.append(args),
    )

    menu_module.on_menu_file_export_droplet_actionlist(frame, None)
    menu_module.on_menu_file_export_droplet_recent(frame, None)
    menu_module.on_menu_file_export_droplet_inspector(frame, None)
    menu_module.on_menu_file_export_explorer_actionlist(frame, None)
    menu_module.on_menu_file_export_explorer_recent(frame, None)
    menu_module.on_menu_file_export_explorer_inspector(frame, None)
    menu_module.on_menu_file_export_explorer_remove(frame, None)

    assert len(calls) == 8


def test_menu_error_success_empty_and_skip_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menu_module = importlib.import_module("phatch.windows.droplet_menu")
    calls: list[tuple[str, str]] = []
    frame = SimpleNamespace(
        filename="edit.phatch",
        is_save_not_ok=lambda: True,
        menu_file_export_droplet=lambda *args: pytest.fail(str(args)),
        show_info=lambda message: calls.append(("info", message)),
        show_error=lambda message: calls.append(("error", message)),
        install_menu_item=lambda *args: 1,
    )
    monkeypatch.setattr(menu_module, "win32_missing", lambda frame: True)
    menu_module.on_menu_file_export_droplet_actionlist(frame, None)
    menu_module.on_menu_file_export_droplet_recent(frame, None)
    menu_module.on_menu_file_export_droplet_inspector(frame, None)
    menu_module.on_menu_file_export_explorer_actionlist(frame, None)
    menu_module.menu_file_export_explorer(frame, lambda: "jpg")
    menu_module.menu_file_export_explorer(frame, lambda: "")
    menu_module.install_menu_item(
        frame, None, "menu_file_export_explorer_recent", "label", style=3
    )
    assert calls == [
        ("info", menu_module.EXTENSIONS_INSTALL_SUCCESFUL + "jpg"),
        ("error", menu_module.EXTENSIONS_INSTALL_UNSUCCESFUL),
    ]


def test_remove_menu_reports_registry_error_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    menu_module = importlib.import_module("phatch.windows.droplet_menu")
    errors: list[str] = []
    frame = SimpleNamespace(filename="edit.phatch", show_error=errors.append)
    monkeypatch.setattr(
        menu_module,
        "remove_phatch_explorer_actions",
        lambda actionlist: (_ for _ in ()).throw(menu_module.ExplorerVerbError()),
    )
    menu_module.on_menu_file_export_explorer_remove(frame, None)
    assert errors == [menu_module.EXTENSIONS_INSTALL_UNSUCCESFUL]
