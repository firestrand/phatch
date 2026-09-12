from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

from phatch.linux import droplet, thunar


class FakeFrame:
    def __init__(self) -> None:
        self.filename = "/tmp/My List.phatch"
        self.menu_file_export = FakeMenu()
        self.menu_item: list[tuple[FakeMenu, list[str]]] = []
        self.installed: list[str] = []
        self.exports: list[tuple] = []
        self.info: list[str] = []
        self.errors: list[str] = []
        self.save_blocked = False

    def install_menu_item(self, menu, name, label, method, tooltip, style):
        self.installed.append(name)
        return name

    def menu_file_export_droplet(self, *args) -> None:
        self.exports.append(args)

    def is_save_not_ok(self) -> bool:
        return self.save_blocked

    def show_info(self, message: str) -> None:
        self.info.append(message)

    def show_error(self, message: str) -> None:
        self.errors.append(message)


class FakeMenu:
    def __init__(self) -> None:
        self.separators: list[int] = []

    def InsertSeparator(self, position: int) -> None:
        self.separators.append(position)


def test_thunar_action_writes_real_xml_backup_and_is_idempotent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    actions = tmp_path / "uca.xml"
    actions.write_text("<actions></actions>", encoding="utf-8")
    monkeypatch.setattr(thunar, "THUNAR_USER_ACTIONS", str(actions))

    assert (
        thunar.create_thunar_action(
            "Batch Photos",
            'phatch -d "/tmp/list.phatch" %F',
            "Process photos",
            types="<directories/><image-files/>",
            icon="phatch",
        )
        is True
    )

    output = actions.read_text(encoding="utf-8")
    assert "<name>Batch Photos</name>" in output
    assert '<command>phatch -d "/tmp/list.phatch" %F</command>' in output
    backup = Path(str(actions) + thunar.BACKUP)
    assert backup.read_text(encoding="utf-8") == "<actions></actions>"
    before = actions.stat().st_mtime_ns
    assert (
        thunar.create_thunar_action(
            "Batch Photos",
            'phatch -d "/tmp/list.phatch" %F',
            "Process photos",
            types="<directories/><image-files/>",
            icon="phatch",
        )
        is True
    )
    assert actions.stat().st_mtime_ns == before

    assert (
        thunar.create_thunar_action(
            "Inspect Photos", "phatch -n %F", "Inspect metadata", icon="phatch"
        )
        is True
    )
    assert backup.read_text(encoding="utf-8") == "<actions></actions>"


def test_thunar_missing_configuration_has_no_filesystem_side_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    actions = tmp_path / "missing.xml"
    monkeypatch.setattr(thunar, "THUNAR_USER_ACTIONS", str(actions))
    assert thunar.thunar_exists() is False
    assert thunar.create_thunar_action("Name", "command", "description") is False
    assert list(tmp_path.iterdir()) == []


def test_thunar_direct_entrypoint_bootstraps_legacy_import_path() -> None:
    original_path = list(sys.path)
    try:
        namespace = runpy.run_path(thunar.__file__, run_name="__main__")
        assert namespace["_"] is str
        assert sys.path[0] == "../.."
    finally:
        sys.path[:] = original_path


def test_droplet_and_thunar_wrappers_construct_expected_shortcuts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    desktop_calls: list[dict[str, str]] = []
    thunar_calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        droplet, "create_droplet", lambda **values: desktop_calls.append(values)
    )
    monkeypatch.setattr(
        droplet,
        "create_thunar_action",
        lambda **values: thunar_calls.append(values) or True,
    )
    monkeypatch.setattr(droplet.system, "filename_to_title", lambda path: "My List")
    monkeypatch.setattr(
        droplet.ct,
        "COMMAND",
        {
            "DROP": 'phatch -d "%s" %%F',
            "RECENT": "phatch recent %F",
            "INSPECTOR": "phatch -n %F",
        },
    )

    droplet.create_phatch_droplet("/tmp/list.phatch", "/tmp/Desktop", "action")
    droplet.create_phatch_recent_droplet("/tmp/Desktop")
    droplet.create_phatch_inspector_droplet("/tmp/Desktop", "inspect")
    droplet.create_phatch_thunar_action("/tmp/list.phatch", "description", "action")
    droplet.create_phatch_recent_thunar_action()
    droplet.create_phatch_inspect_thunar_action("inspect")

    assert desktop_calls[0] == {
        "name": "My List",
        "command": 'phatch -d "/tmp/list.phatch" %F',
        "folder": "/tmp/Desktop",
        "icon": "action",
    }
    assert [call["types"] for call in thunar_calls] == [
        "<directories/><image-files/>",
        "<directories/><image-files/>",
        "<image-files/>",
    ]
    assert thunar_calls[0]["command"] == 'phatch -d "/tmp/list.phatch" %F'


def test_nautilus_wrappers_construct_text_extension_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, str]] = []
    monkeypatch.setattr(
        droplet, "create_nautilus_extension", lambda **values: calls.append(values)
    )
    monkeypatch.setattr(droplet.system, "title", lambda name: "My List")

    droplet.create_phatch_nautilus_action("/tmp/My List.phatch")
    droplet.create_phatch_recent_nautilus_action()
    droplet.create_phatch_inspect_nautilus_action()

    assert calls[0]["name"] == "phatch_actionlist_My List"
    assert calls[0]["command"] == 'phatch -d "/tmp/My List.phatch" %s &'
    assert calls[1]["name"] == "phatch_recent"
    assert calls[2]["name"] == "phatch_image_inspector"


def test_menu_action_reports_success_and_actual_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = FakeFrame()
    monkeypatch.setattr(droplet, "_", lambda value: value, raising=False)
    droplet.menu_action(frame, "Thunar", "", lambda: None)

    def fail() -> None:
        raise OSError("permission denied")

    droplet.menu_action(frame, "Thunar", "", fail)
    assert "restart Thunar" in frame.info[0]
    assert "permission denied" in frame.errors[0]


@pytest.mark.parametrize(
    ("has_thunar", "has_nautilus", "system_install", "expected", "separators"),
    [
        (False, False, False, 3, [3]),
        (True, False, False, 6, [3, 3]),
        (False, True, False, 6, [3, 3]),
        (False, True, True, 4, [1, 3]),
        (True, True, False, 9, [3, 3, 3]),
    ],
)
def test_install_dispatches_only_available_platform_integrations(
    monkeypatch: pytest.MonkeyPatch,
    has_thunar: bool,
    has_nautilus: bool,
    system_install: bool,
    expected: int,
    separators: list[int],
) -> None:
    frame = FakeFrame()
    monkeypatch.setattr(droplet, "thunar_exists", lambda: has_thunar)
    monkeypatch.setattr(droplet, "nautilus_exists", lambda: has_nautilus)
    monkeypatch.setattr(droplet, "SYSTEM_INSTALL", system_install)

    droplet.install(frame)

    assert len(frame.installed) == expected
    assert frame.menu_file_export.separators == separators
    assert ("menu_file_export_nautilus_recent" in frame.installed) is (
        has_nautilus and not system_install
    )


def test_menu_handlers_dispatch_and_honor_save_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    frame = FakeFrame()
    calls: list[tuple] = []
    monkeypatch.setattr(
        droplet, "menu_action", lambda *args, **kwargs: calls.append(args)
    )

    droplet.on_menu_file_export_droplet_actionlist(frame, None)
    droplet.on_menu_file_export_droplet_recent(frame, None)
    droplet.on_menu_file_export_droplet_inspector(frame, None)
    droplet.on_menu_file_export_thunar_actionlist(frame, None)
    droplet.on_menu_file_export_thunar_recent(frame, None)
    droplet.on_menu_file_export_thunar_inspector(frame, None)
    droplet.on_menu_file_export_nautilus_actionlist(frame, None)
    droplet.on_menu_file_export_nautilus_recent(frame, None)
    droplet.on_menu_file_export_nautilus_inspector(frame, None)
    assert len(frame.exports) == 3
    assert len(calls) == 6

    frame.save_blocked = True
    droplet.on_menu_file_export_droplet_actionlist(frame, None)
    droplet.on_menu_file_export_thunar_actionlist(frame, None)
    droplet.on_menu_file_export_nautilus_actionlist(frame, None)
    assert len(frame.exports) == 3
    assert len(calls) == 6
