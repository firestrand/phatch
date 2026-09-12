from __future__ import annotations

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

import scripts.windows_window_probe as windows_window_probe
from scripts import distribution_smoke, portable_smoke


def test_distribution_smoke_builds_from_one_sdist_and_uses_clean_environment(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: one source artifact and observable build/install/smoke boundaries
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    (source_dir / "Phatch.tar.gz").write_bytes(b"source")
    commands: list[tuple[str, ...]] = []

    def unpack(archive: Path, destination: Path) -> None:
        del archive
        (destination / "Phatch-0.3.0").mkdir()

    def run(arguments, *, cwd=None) -> None:
        del cwd
        commands.append(tuple(str(argument) for argument in arguments))
        if "--wheel" in arguments:
            output_dir.mkdir(exist_ok=True)
            (output_dir / "Phatch.whl").write_bytes(b"wheel")

    monkeypatch.setattr(distribution_smoke.shutil, "unpack_archive", unpack)
    monkeypatch.setattr(distribution_smoke, "_run", run)

    # When: the cross-platform distribution harness executes
    result = distribution_smoke.main((str(source_dir), str(output_dir)))

    # Then: it builds, creates a venv, installs the wheel, and smokes entries/resources
    assert result == 0
    assert len(commands) == 7
    assert "build" in commands[0]
    assert "venv" in commands[1]
    assert commands[2][0] == "uv"
    assert "--help" in commands[3]
    assert "ResourceProvider" in commands[5][-1]
    assert "phatch.actions" in commands[6][-1]


def test_distribution_smoke_ignores_preexisting_wheels(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: an output directory containing a stale wheel before the build
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    output_dir.mkdir()
    (source_dir / "Phatch.tar.gz").write_bytes(b"source")
    stale = output_dir / "stale.whl"
    stale.write_bytes(b"stale")
    installed: list[Path] = []

    def unpack(archive: Path, destination: Path) -> None:
        del archive
        (destination / "Phatch-0.3.0").mkdir()

    def run(arguments, *, cwd=None) -> None:
        del cwd
        if "--wheel" in arguments:
            (output_dir / "fresh.whl").write_bytes(b"fresh")
        if arguments[:3] == ["uv", "pip", "install"]:
            installed.append(Path(arguments[-1]))

    monkeypatch.setattr(distribution_smoke.shutil, "unpack_archive", unpack)
    monkeypatch.setattr(distribution_smoke, "_run", run)

    # When: the distribution smoke builds and installs
    distribution_smoke.main((str(source_dir), str(output_dir)))

    # Then: only the wheel produced by this invocation is installed
    assert installed == [Path(f"{output_dir / 'fresh.whl'}[gui,windows]")]


@pytest.mark.parametrize("source_count", [0, 2])
def test_distribution_smoke_rejects_ambiguous_source_artifacts(
    tmp_path: Path, source_count: int
) -> None:
    # Given: a source directory that does not contain exactly one sdist
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    for index in range(source_count):
        (source_dir / f"Phatch-{index}.tar.gz").write_bytes(b"source")

    # When/Then: the CLI rejects ambiguity before extraction
    with pytest.raises(SystemExit, match="2"):
        distribution_smoke.main((str(source_dir), str(tmp_path / "output")))


def test_distribution_smoke_rejects_ambiguous_extracted_roots(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: one sdist that expands to two source roots
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    (source_dir / "Phatch.tar.gz").write_bytes(b"source")

    def unpack(archive: Path, destination: Path) -> None:
        del archive
        (destination / "one").mkdir()
        (destination / "two").mkdir()

    monkeypatch.setattr(distribution_smoke.shutil, "unpack_archive", unpack)

    # When/Then: the CLI rejects the malformed source artifact
    with pytest.raises(SystemExit, match="2"):
        distribution_smoke.main((str(source_dir), str(tmp_path / "output")))


def test_distribution_smoke_rejects_missing_new_wheel(
    tmp_path: Path, monkeypatch
) -> None:
    source_dir = tmp_path / "source"
    output_dir = tmp_path / "output"
    source_dir.mkdir()
    (source_dir / "Phatch.tar.gz").write_bytes(b"source")

    def unpack(archive: Path, destination: Path) -> None:
        del archive
        (destination / "Phatch-0.3.0").mkdir()

    monkeypatch.setattr(distribution_smoke.shutil, "unpack_archive", unpack)
    monkeypatch.setattr(distribution_smoke, "_run", lambda arguments, **kwargs: None)

    with pytest.raises(SystemExit, match="2"):
        distribution_smoke.main((str(source_dir), str(output_dir)))


def test_distribution_smoke_selects_windows_installed_commands(tmp_path: Path) -> None:
    # Given: a clean Windows virtual environment path
    environment = tmp_path / "clean install"

    # When: the harness resolves its installed command boundaries
    python, phatch, phatch_gui = distribution_smoke._installed_commands(
        environment, windows=True
    )

    # Then: both commands use native Windows executable names
    assert python == environment / "Scripts" / "python.exe"
    assert phatch == environment / "Scripts" / "phatch.exe"
    assert phatch_gui == environment / "Scripts" / "phatch-gui.exe"


def test_distribution_smoke_script_exposes_help(monkeypatch) -> None:
    # Given: the distribution smoke script's executable boundary
    script = Path(distribution_smoke.__file__)
    monkeypatch.setattr(sys, "argv", [str(script), "--help"])

    # When/Then: direct execution exposes argparse help and exits successfully
    with pytest.raises(SystemExit) as exit_info:
        runpy.run_path(str(script), run_name="__main__")
    assert exit_info.value.code == 0


def test_portable_process_runner_and_action_list_use_real_boundaries(
    tmp_path: Path,
) -> None:
    # Given: the current interpreter and a portable action-list destination
    action_list = tmp_path / "actions.phatch"
    output = tmp_path / "output"

    # When: the runner executes success/failure and the list is serialized
    completed = portable_smoke._run(
        Path(sys.executable),
        ("-c", "print('ok')"),
        work=tmp_path,
        environment={},
    )
    portable_smoke._write_action_list(action_list, output)
    with pytest.raises(RuntimeError, match="exited 7"):
        portable_smoke._run(
            Path(sys.executable),
            ("-c", "raise SystemExit(7)"),
            work=tmp_path,
            environment={},
        )

    # Then: subprocess output and the Save action contract are real
    assert completed.stdout.strip() == "ok"
    payload = json.loads(action_list.read_text(encoding="utf-8"))
    assert payload["actions"][0]["id"] == "save"
    assert payload["actions"][0]["fields"]["in"] == str(output)


def test_portable_console_exercises_capabilities_preflight_workers_and_resume(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a portable root and observable public executable calls
    root = tmp_path / "Phatch"
    work = tmp_path / "work"
    root.mkdir()
    work.mkdir()
    calls: list[tuple[str, ...]] = []

    def run(executable, arguments, *, work, environment):
        del executable, environment
        calls.append(arguments)
        if "--max-workers" in arguments:
            output = work / "processed output Ω"
            output.mkdir()
            for index in range(4):
                (output / f"input Ω {index}.png").write_bytes(b"png")
        if "--resume" in arguments:
            Path(arguments[1]).write_text("journal", encoding="utf-8")
        stderr = (
            "execution_mode=process requested_workers=2 "
            "effective_workers=2 worker_pids=41,42"
            if "--max-workers" in arguments
            else ""
        )
        return subprocess.CompletedProcess([], 0, '{"outcome": "success"}', stderr)

    monkeypatch.setattr(portable_smoke, "_run", run)

    # When: console artifact smoke executes
    portable_smoke._exercise_console(root, work, {})

    # Then: help, capability, preflight, parallel, and two resume calls ran
    assert len(calls) == 6
    assert calls[0] == ("--help",)
    assert sum("--resume" in call for call in calls) == 2
    assert any("--max-workers" in call for call in calls)
    assert any("--verbose" in call for call in calls)


def test_portable_gui_requires_windows_and_closes_matching_window(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a non-Windows host and a fake Windows window enumeration API
    with pytest.raises(RuntimeError, match="native Windows"):
        portable_smoke._exercise_gui(tmp_path, tmp_path, {})
    posted: list[int] = []

    class Function:
        def __init__(self, implementation):
            self.implementation = implementation
            self.argtypes = None
            self.restype = None

        def __call__(self, *arguments):
            return self.implementation(*arguments)

    def process_id(window, output):
        del window
        output._obj.value = 73
        return 1

    def window_text(window, output, size):
        del window, size
        output.value = "actions - Phatch"
        return len(output.value)

    def class_name(window, output, size):
        del window, size
        output.value = "wxWindowNR"
        return len(output.value)

    class User32:
        def __init__(self):
            self.EnumWindows = Function(self._enum_windows)
            self.GetWindowThreadProcessId = Function(process_id)
            self.IsWindowVisible = Function(lambda window: window == 41)
            self.GetWindowTextLengthW = Function(lambda window: 16)
            self.GetWindowTextW = Function(window_text)
            self.GetClassNameW = Function(class_name)
            self.GetWindow = Function(lambda window, command: 0)
            self.GetWindowLongPtrW = Function(lambda window, index: 0x10CF0000)
            self.PostMessageW = Function(self._post_message)

        @staticmethod
        def _enum_windows(callback, parameter):
            callback(41, parameter)
            return 1

        @staticmethod
        def _post_message(window, message, first, second):
            del message, first, second
            posted.append(window)
            return 1

    class Process:
        pid = 73

    user32 = User32()
    monkeypatch.setattr(windows_window_probe, "_load_user32", lambda: user32)
    monkeypatch.setattr(
        windows_window_probe, "_windows_callback_type", lambda: lambda fn: fn
    )

    # When: the process-owned visible window is located
    found = portable_smoke._close_windows_process_window(Process(), "actions - Phatch")
    Process.pid = 74
    absent = portable_smoke._close_windows_process_window(Process(), "actions - Phatch")

    # Then: only that real process boundary receives a close message
    assert found is True
    assert absent is False
    assert posted == [41]
    assert user32.EnumWindows.argtypes is not None
    assert user32.GetWindowLongPtrW.restype is windows_window_probe.ctypes.c_ssize_t


def test_portable_main_rejects_missing_root_and_uses_selected_data(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # Given: one invalid root and one complete portable layout
    root = tmp_path / "Phatch Ω"
    portable_data = root / "portable-data"
    portable_data.mkdir(parents=True)
    (root / "Phatch.exe").write_bytes(b"exe")
    (root / "Phatch-GUI.exe").write_bytes(b"exe")
    calls: list[str] = []

    def console(root: Path, work: Path, environment: dict[str, str]) -> None:
        del work, environment
        calls.append("console")
        state = root / "portable-data" / "config" / "state"
        state.parent.mkdir(parents=True)
        state.write_text("state", encoding="utf-8")

    monkeypatch.setattr(
        portable_smoke,
        "_exercise_console",
        console,
    )
    monkeypatch.setattr(
        portable_smoke,
        "_exercise_gui",
        lambda root, work, environment: calls.append("gui"),
    )

    # When: invalid and valid layouts cross the CLI boundary
    with pytest.raises(SystemExit, match="2"):
        portable_smoke.main((str(tmp_path / "missing"),))
    result = portable_smoke.main((str(root),))

    # Then: only the complete layout exercises both public interfaces
    assert result == 0
    assert calls == ["console", "gui"]
    assert "portable console" in capsys.readouterr().out
