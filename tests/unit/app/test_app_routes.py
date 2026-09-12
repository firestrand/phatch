from __future__ import annotations

import sys
import builtins
from types import SimpleNamespace

import pytest

from phatch import app
from phatch.console import console as console_module
from phatch.core import api
from phatch.core import settings as settings_module


def test_parse_locale_supports_default_and_explicit_language(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        app.config, "load_locale", lambda name, path, canonical: calls.append(canonical)
    )

    monkeypatch.setattr(sys, "argv", ["phatch"])
    app.parse_locale({"PHATCH_LOCALE_PATH": "/locale"})
    monkeypatch.setattr(sys, "argv", ["phatch", "-l", "fr"])
    app.parse_locale({"PHATCH_LOCALE_PATH": "/locale"})

    assert calls == ["default", "fr"]


def test_parse_locale_rejects_missing_language(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["phatch", "-l"])

    with pytest.raises(SystemExit, match="specify locale"):
        app.parse_locale({"PHATCH_LOCALE_PATH": "/locale"})


def test_parse_options_normalizes_paths_and_filters_templates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        ["phatch", "file:///tmp/holiday%20photo.jpg", "%template"],
    )

    options, paths = app.parse_options()

    assert paths == ["/tmp/holiday photo.jpg"]
    assert options.paths == paths


def test_reexec_with_pythonw_uses_default_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str]]] = []
    monkeypatch.setattr(sys, "version", "2.4")
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "executable", "/usr/bin/python")
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "argv", ["phatch", "image.jpg"])
    monkeypatch.setattr(
        app.os, "execvp", lambda executable, args: calls.append((executable, args))
    )

    app.reexec_with_pythonw()

    assert calls == [("pythonw", ["pythonw", app.__file__, "image.jpg"])]


def test_reexec_with_pythonw_skips_modern_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        app.os, "execvp", lambda executable, args: calls.append(executable)
    )

    app.reexec_with_pythonw("app.py")

    assert calls == []


def test_console_wrapper_forces_console(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[dict[str, str], bool]] = []
    paths = {"PHATCH_LOCALE_PATH": "/locale"}
    monkeypatch.setattr(
        app,
        "main",
        lambda *, config_paths, app_file, force_console: calls.append(
            (config_paths, force_console)
        ),
    )

    app.console(paths)

    assert calls == [(paths, True)]


def test_import_pywx_returns_injected_gui_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_gui = SimpleNamespace()
    import phatch.pyWx as pywx_package

    monkeypatch.setattr(pywx_package, "gui", fake_gui, raising=False)
    monkeypatch.setitem(sys.modules, "phatch.pyWx.gui", fake_gui)

    assert app.import_pyWx() is fake_gui


def test_import_pywx_exits_when_gui_dependencies_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def without_wx(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pyWx" and "gui" in fromlist:
            raise ModuleNotFoundError("wx unavailable", name="wx")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", without_wx)

    with pytest.raises(SystemExit, match="phatch-cli"):
        app.import_pyWx()


def test_import_pywx_propagates_broken_gui_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def fail_gui_helper(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "pyWx" and "gui" in fromlist:
            raise ModuleNotFoundError("broken helper", name="phatch.pyWx.helper")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fail_gui_helper)

    with pytest.raises(ModuleNotFoundError, match="broken helper"):
        app.import_pyWx()


def test_gui_inspect_and_droplet_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, tuple]] = []
    gui = SimpleNamespace(
        main=lambda settings, actionlist, dependencies: calls.append(
            ("main", (settings, actionlist, dependencies))
        ),
        inspect=lambda paths: calls.append(("inspect", (paths,))),
        drop=lambda **values: calls.append(("drop", (values,))),
    )
    monkeypatch.setattr(
        app, "reexec_with_pythonw", lambda value: calls.append(("reexec", (value,)))
    )
    monkeypatch.setattr(app, "import_pyWx", lambda: gui)
    registry = SimpleNamespace()
    monkeypatch.setattr(api, "init", lambda: registry)

    app._gui("app.py", ["actions.phatch"], {"mode": "gui"})
    app._gui("app.py", [], {"mode": "gui"})
    app._inspect("app.py", ["image.jpg"])
    app._droplet("app.py", ["actions.phatch", "image.jpg"], {"mode": "drop"})

    assert [name for name, _ in calls] == [
        "reexec",
        "main",
        "reexec",
        "main",
        "reexec",
        "inspect",
        "reexec",
        "drop",
    ]
    assert calls[1][1][2].action_service_factory().registry is registry
    assert calls[-1][1][0]["dependencies"].action_service_factory().registry is registry


def test_init_fonts_initializes_paths_before_font_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from phatch.lib import fonts

    calls: list[str] = []
    monkeypatch.setattr(
        app.config, "verify_app_user_paths", lambda: calls.append("paths")
    )
    monkeypatch.setattr(
        fonts, "font_dictionary", lambda force: calls.append(f"fonts:{force}")
    )

    app._init_fonts()

    assert calls == ["paths", "fonts:True"]


@pytest.mark.parametrize(
    ("paths", "expected_actionlist", "expected_paths"),
    [
        (["actions.phatch", "image.jpg"], "actions.phatch", ["image.jpg"]),
        (["image.jpg"], "", ["image.jpg"]),
    ],
)
def test_console_route_initializes_api_and_splits_actionlist(
    paths: list[str],
    expected_actionlist: str,
    expected_paths: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, list[str], SimpleNamespace]] = []
    registry = SimpleNamespace()
    monkeypatch.setattr(api, "init", lambda: registry)
    monkeypatch.setattr(
        console_module,
        "main",
        lambda *, actionlist, paths, settings, registry: calls.append(
            (actionlist, paths, registry)
        ),
    )

    app._console(paths, {})

    assert calls == [(expected_actionlist, expected_paths, registry)]


@pytest.mark.parametrize(
    ("mode", "paths", "expected"),
    [
        ("inspect", ["image.jpg"], "inspect"),
        ("fonts", [], "fonts"),
        ("droplet", [], "droplet"),
        ("console", ["actions.phatch", "image.jpg"], "console"),
        ("gui", [], "gui"),
    ],
)
def test_main_dispatches_each_application_mode(
    mode: str,
    paths: list[str],
    expected: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    options = SimpleNamespace()
    values = {
        "verbose": mode == "console",
        "safe": True,
        "image_inspector": mode == "inspect",
        "init_fonts": mode == "fonts",
        "droplet": mode == "droplet",
        "console": mode == "console",
        "interactive": False,
    }
    monkeypatch.setattr(
        app.config, "init_config_paths", lambda: {"PHATCH_LOCALE_PATH": "/locale"}
    )
    monkeypatch.setattr(app, "parse_locale", lambda config_paths: None)
    monkeypatch.setattr(app, "parse_options", lambda: (options, list(paths)))
    monkeypatch.setattr(
        settings_module, "create_settings", lambda config_paths, parsed: dict(values)
    )
    monkeypatch.setattr(app.config, "check_fonts", lambda: calls.append("check-fonts"))
    monkeypatch.setattr(
        app, "_inspect", lambda app_file, values: calls.append("inspect")
    )
    monkeypatch.setattr(app, "_init_fonts", lambda: calls.append("fonts"))
    monkeypatch.setattr(
        app, "_droplet", lambda app_file, values, settings: calls.append("droplet")
    )
    monkeypatch.setattr(
        app, "_console", lambda values, settings: calls.append("console")
    )
    monkeypatch.setattr(
        app, "_gui", lambda app_file, values, settings: calls.append("gui")
    )

    app.main()

    assert expected in calls


def test_main_promotes_image_path_to_droplet(monkeypatch: pytest.MonkeyPatch) -> None:
    options = SimpleNamespace()
    values = {
        "verbose": False,
        "image_inspector": False,
        "init_fonts": False,
        "droplet": False,
        "console": False,
        "interactive": False,
    }
    dispatched: list[list[str]] = []
    monkeypatch.setattr(app, "parse_locale", lambda config_paths: None)
    monkeypatch.setattr(app, "parse_options", lambda: (options, ["image.jpg"]))
    monkeypatch.setattr(
        settings_module, "create_settings", lambda config_paths, parsed: values
    )
    monkeypatch.setattr(app.config, "check_fonts", lambda: None)
    monkeypatch.setattr(
        app, "_droplet", lambda app_file, paths, settings: dispatched.append(paths)
    )

    app.main({"PHATCH_LOCALE_PATH": "/locale"}, "app.py")

    assert dispatched == [["recent", "image.jpg"]]


def test_main_force_console_overrides_created_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    options = SimpleNamespace()
    values = {
        "verbose": False,
        "image_inspector": False,
        "init_fonts": False,
        "droplet": False,
        "console": False,
        "interactive": False,
    }
    dispatched: list[dict[str, bool]] = []
    monkeypatch.setattr(app, "parse_locale", lambda config_paths: None)
    monkeypatch.setattr(app, "parse_options", lambda: (options, ["actions.phatch"]))
    monkeypatch.setattr(
        settings_module, "create_settings", lambda config_paths, parsed: values
    )
    monkeypatch.setattr(app.config, "check_fonts", lambda: None)
    monkeypatch.setattr(
        app, "_console", lambda paths, settings: dispatched.append(settings)
    )

    app.main({"PHATCH_LOCALE_PATH": "/locale"}, "app.py", force_console=True)

    assert dispatched[0]["console"] is True
