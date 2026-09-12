from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from phatch import app
from phatch import phatch as legacy_entrypoint


def entrypoint_module():
    return importlib.import_module("phatch.entrypoints")


class TestFrame:
    def get_setting(self, name: str) -> str:
        return name


class TestGuiModule:
    Frame = TestFrame


def gui_module() -> TestGuiModule:
    return TestGuiModule()


def test_compatibility_wrapper_runs_outside_checkout(tmp_path: Path) -> None:
    # Given: the absolute path to the source-checkout compatibility wrapper
    wrapper = Path(__file__).resolve().parents[3] / "bin" / "phatch"
    dependency_paths = [path for path in sys.path if "site-packages" in path]
    environment = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(dependency_paths),
    }

    # When: it is launched from an unrelated working directory
    completed = subprocess.run(
        [sys.executable, "-S", str(wrapper), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    # Then: it locates the checkout package and delegates to the console entry point
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.startswith("usage: Phatch")


def test_console_entrypoint_forces_console_without_importing_gui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the packaged console adapter
    monkeypatch.delitem(sys.modules, "wx", raising=False)
    module = entrypoint_module()
    calls: list[tuple[bool, bool]] = []
    monkeypatch.setattr(
        app,
        "main",
        lambda *, config_paths, force_console=False: calls.append(
            (force_console, Path(config_paths["PHATCH_DATA_PATH"]).is_dir())
        ),
    )

    # When: the installed console script invokes its adapter
    result = module.console_main()

    # Then: console mode is selected without loading wx
    assert result == 0
    assert len(calls) == 1
    assert calls[0][0] is True
    assert calls[0][1] is True
    assert "wx" not in sys.modules


def test_console_entrypoint_enables_frozen_process_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the public console adapter with observable frozen-process setup
    module = entrypoint_module()
    from phatch.services import automation_cli

    calls: list[str] = []
    monkeypatch.setattr(
        module.multiprocessing, "freeze_support", lambda: calls.append("freeze")
    )
    monkeypatch.setattr(
        module, "configure_portable_data", lambda: calls.append("portable")
    )
    monkeypatch.setattr(automation_cli, "is_automation_request", lambda arguments: True)
    monkeypatch.setattr(automation_cli, "run_automation_cli", lambda arguments: 0)

    # When: the executable entry point starts
    result = module.console_main()

    # Then: child-process and portable paths are configured before dispatch
    assert result == 0
    assert calls == ["freeze", "portable"]


def test_frozen_portable_data_uses_existing_user_path_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: a frozen executable beside an explicitly selected portable-data folder
    module = entrypoint_module()
    executable = tmp_path / "Phatch portable Ω" / "Phatch.exe"
    data = executable.parent / "portable-data"
    data.mkdir(parents=True)
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(executable))
    for name in (
        "PHATCH_USER_CONFIG_DIR",
        "PHATCH_USER_DATA_DIR",
        "PHATCH_USER_CACHE_DIR",
    ):
        monkeypatch.setenv(name, str(tmp_path / "outside" / name))

    # When: portable startup configures application storage
    module.configure_portable_data()

    # Then: existing path injection points keep every write under portable-data
    assert os.environ["PHATCH_USER_CONFIG_DIR"] == str(data / "config")
    assert os.environ["PHATCH_USER_DATA_DIR"] == str(data / "data")
    assert os.environ["PHATCH_USER_CACHE_DIR"] == str(data / "cache")


def test_frozen_without_portable_data_preserves_default_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Given: a frozen executable without the portable-data opt-in folder
    module = entrypoint_module()
    executable = tmp_path / "installed" / "Phatch.exe"
    monkeypatch.setattr(module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(module.sys, "executable", str(executable))
    names = (
        "PHATCH_USER_CONFIG_DIR",
        "PHATCH_USER_DATA_DIR",
        "PHATCH_USER_CACHE_DIR",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)

    # When: frozen startup checks for portable storage
    module.configure_portable_data()

    # Then: normal platform paths remain selected
    assert all(name not in os.environ for name in names)


def test_structured_console_maps_keyboard_interrupt_to_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = entrypoint_module()
    from phatch.services import automation_cli

    monkeypatch.setattr(sys, "argv", ["phatch", "--dry-run", "--report-format", "json"])
    monkeypatch.setattr(
        automation_cli,
        "run_automation_cli",
        lambda arguments: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    result = module.console_main()

    captured = capsys.readouterr()
    assert result == 130
    assert '"outcome": "user_cancellation"' in captured.out
    assert "Cancelled by user." in captured.err


def test_structured_console_maps_equals_form_interrupt_to_json_cancellation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = entrypoint_module()
    from phatch.services import automation_cli

    monkeypatch.setattr(sys, "argv", ["phatch", "--report-format=json"])
    monkeypatch.setattr(
        automation_cli,
        "run_automation_cli",
        lambda arguments: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    result = module.console_main()

    captured = capsys.readouterr()
    assert result == 130
    assert '"outcome": "user_cancellation"' in captured.out


def test_gui_entrypoint_defers_gui_import_to_application_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the packaged GUI adapter
    module = entrypoint_module()
    calls: list[tuple[bool, str]] = []
    monkeypatch.setattr(module, "probe_gui", gui_module)
    monkeypatch.setattr(
        app,
        "main",
        lambda *, config_paths, force_console=False: calls.append(
            (force_console, config_paths["PHATCH_DATA_PATH"])
        ),
    )

    # When: the installed GUI script invokes its adapter
    result = module.gui_main()

    # Then: dispatch remains lazy and GUI mode is selected
    assert result == 0
    assert len(calls) == 1
    assert calls[0][0] is False


def test_gui_entrypoint_probes_dependency_before_stateful_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: observable dependency, configuration, and dispatch seams
    module = entrypoint_module()
    calls: list[str] = []
    monkeypatch.setattr(module.util, "find_spec", lambda name: name)
    monkeypatch.setattr(
        app,
        "import_pyWx",
        lambda: calls.append("probe") or gui_module(),
    )
    monkeypatch.setattr(
        module.config,
        "init_config_paths",
        lambda paths: calls.append("config") or paths,
    )
    monkeypatch.setattr(
        app,
        "main",
        lambda *, config_paths, force_console=False: calls.append("dispatch"),
    )

    # When: the installed GUI command starts
    result = module.gui_main()

    # Then: wx is validated before configuration and dispatch runs exactly once
    assert result == 0
    assert calls == ["probe", "config", "dispatch"]


def test_gui_entrypoint_reports_missing_extra_without_stateful_startup(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Given: no wx dependency and a stateful seam that must remain unreachable
    module = entrypoint_module()
    monkeypatch.setattr(module.util, "find_spec", lambda name: None)
    monkeypatch.setattr(
        module.config,
        "init_config_paths",
        lambda paths: (_ for _ in ()).throw(AssertionError("state initialized")),
    )

    # When: the installed GUI command starts
    result = module.gui_main()

    # Then: it returns one stable failure with actionable stderr and no traceback
    captured = capsys.readouterr()
    assert result == 1
    assert "Phatch[gui]" in captured.err
    assert "Traceback" not in captured.err


def test_gui_entrypoint_without_wx_creates_no_user_state(tmp_path: Path) -> None:
    # Given: an isolated, initially absent user home and no importable site packages
    home = tmp_path / "isolated-home"
    environment = {
        **os.environ,
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_CONFIG_HOME": str(home / "config"),
        "PYTHONPATH": str(Path(__file__).resolve().parents[3]),
    }

    # When: the real GUI command boundary runs without wx
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from phatch import entrypoints; "
                "entrypoints.util.find_spec = lambda name: None; "
                "raise SystemExit(entrypoints.gui_main())"
            ),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    # Then: it fails concisely without creating any user state
    assert completed.returncode == 1
    assert "Phatch[gui]" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert not home.exists()


def test_gui_probe_reports_actionable_missing_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an environment without wxPython
    monkeypatch.delitem(sys.modules, "phatch.pyWx.gui", raising=False)
    module = entrypoint_module()
    monkeypatch.setattr(module.util, "find_spec", lambda name: None)

    # When: the non-window-opening GUI probe runs
    with pytest.raises(module.GuiDependencyError, match=r"Phatch\[gui\]"):
        module.probe_gui()

    # Then: no GUI package was imported
    assert "phatch.pyWx.gui" not in sys.modules


def test_gui_probe_imports_adapter_without_opening_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: an available GUI dependency and a bounded import adapter
    module = entrypoint_module()
    imports: list[bool] = []
    expected = gui_module()
    monkeypatch.setattr(module.util, "find_spec", lambda name: name)
    monkeypatch.setattr(
        app,
        "import_pyWx",
        lambda: imports.append(True) or expected,
    )

    # When: the GUI probe runs
    result = module.probe_gui()

    # Then: only the import seam is exercised
    assert result is expected
    assert imports == [True]


def test_legacy_entrypoint_delegates_to_packaged_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the compatibility bootstrap and an injected packaged mapping
    paths = {"PHATCH_DATA_PATH": "/package/data"}
    monkeypatch.setattr(legacy_entrypoint, "direct_config_paths", lambda: paths)
    monkeypatch.setattr(
        legacy_entrypoint.config,
        "init_config_paths",
        lambda config_paths: config_paths,
    )

    # When: legacy startup initializes paths
    result = legacy_entrypoint.init_config_paths()

    # Then: it delegates to the package resource mapping
    assert result is paths


def test_legacy_main_calls_application_entrypoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given: the compatibility module with application dispatch isolated
    calls: list[tuple[dict[str, str], str]] = []
    monkeypatch.setattr(
        legacy_entrypoint,
        "init_config_paths",
        lambda: {"PHATCH_DATA_PATH": "/package/data"},
    )
    monkeypatch.setattr(
        app,
        "main",
        lambda paths, app_file: calls.append((paths, app_file)),
    )

    # When: legacy main is invoked
    legacy_entrypoint.main()

    # Then: it calls the same packaged application entrypoint
    assert calls == [
        ({"PHATCH_DATA_PATH": "/package/data"}, legacy_entrypoint.__file__)
    ]
