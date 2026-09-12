from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import scripts.windows_window_probe as windows_window_probe
from scripts import portable_smoke


@pytest.mark.parametrize(
    ("failed_argument", "message"),
    [
        ("--capabilities", "capability report failed"),
        ("--dry-run", "preflight failed"),
        ("--max-workers", "parallel processing failed"),
    ],
)
def test_portable_console_rejects_unsuccessful_structured_outcomes(
    tmp_path: Path, monkeypatch, failed_argument: str, message: str
) -> None:
    # Given: a frozen console returning one unsuccessful structured operation
    root = tmp_path / "root"
    work = tmp_path / "work"
    root.mkdir()
    work.mkdir()

    def run(executable, arguments, *, work, environment):
        del executable, work, environment
        outcome = "failed" if failed_argument in arguments else "success"
        return subprocess.CompletedProcess([], 0, f'{{"outcome": "{outcome}"}}', "")

    monkeypatch.setattr(portable_smoke, "_run", run)

    # When/Then: smoke fails at the exact unsuccessful public operation
    with pytest.raises(RuntimeError, match=message):
        portable_smoke._exercise_console(root, work, {})


def test_portable_console_requires_outputs_and_recovery_journal(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: successful reports that fail to produce durable outputs
    root = tmp_path / "root"
    work = tmp_path / "work"
    root.mkdir()
    work.mkdir()
    monkeypatch.setattr(
        portable_smoke,
        "_run",
        lambda executable, arguments, *, work, environment: subprocess.CompletedProcess(
            [],
            0,
            '{"outcome": "success"}',
            "execution_mode=process effective_workers=2 worker_pids=41,42",
        ),
    )

    # When/Then: missing output and journal evidence fails the smoke
    with pytest.raises(RuntimeError, match="output or recovery journal"):
        portable_smoke._exercise_console(root, work, {})


def test_portable_console_requires_distinct_worker_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "root"
    work = tmp_path / "work"
    root.mkdir()
    work.mkdir()
    monkeypatch.setattr(
        portable_smoke,
        "_run",
        lambda executable, arguments, *, work, environment: subprocess.CompletedProcess(
            [], 0, '{"outcome": "success"}', ""
        ),
    )

    with pytest.raises(RuntimeError, match="distinct worker evidence"):
        portable_smoke._exercise_console(root, work, {})


class FakeGuiProcess:
    def __init__(
        self,
        *,
        poll_result: int | None = None,
        returncode: int = 0,
        wait_timeout_once: bool = False,
    ) -> None:
        self.pid = 42
        self.poll_result = poll_result
        self.returncode = returncode
        self.terminated = False
        self.killed = False
        self.wait_calls = 0
        self.wait_timeout_once = wait_timeout_once

    def poll(self) -> int | None:
        return self.poll_result

    def wait(self, timeout: int) -> None:
        del timeout
        self.wait_calls += 1
        if self.wait_timeout_once:
            self.wait_timeout_once = False
            raise subprocess.TimeoutExpired("Phatch-GUI.exe", 10)
        self.poll_result = self.returncode

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


def _windows(monkeypatch, process: FakeGuiProcess) -> None:
    monkeypatch.setattr(portable_smoke, "IS_WINDOWS", True)
    monkeypatch.setattr(
        portable_smoke.subprocess, "Popen", lambda *args, **kwargs: process
    )


def test_portable_gui_closes_cleanly_on_native_windows(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a live GUI process whose visible window is discoverable
    process = FakeGuiProcess()
    _windows(monkeypatch, process)
    monkeypatch.setattr(
        portable_smoke,
        "_close_windows_process_window",
        lambda item, expected_title: True,
    )

    # When: native GUI smoke opens and closes the application
    portable_smoke._exercise_gui(tmp_path, tmp_path, {})

    # Then: the clean process is not forcibly terminated
    assert process.terminated is False


@pytest.mark.parametrize(
    ("process", "window_found", "message"),
    [
        (FakeGuiProcess(poll_result=3, returncode=3), False, "before opening"),
        (FakeGuiProcess(returncode=5), True, "GUI exited 5"),
    ],
)
def test_portable_gui_rejects_early_and_unclean_exit(
    tmp_path: Path,
    monkeypatch,
    process: FakeGuiProcess,
    window_found: bool,
    message: str,
) -> None:
    # Given: a native GUI process with an invalid lifecycle result
    _windows(monkeypatch, process)
    monkeypatch.setattr(
        portable_smoke,
        "_close_windows_process_window",
        lambda item, expected_title: window_found,
    )

    # When/Then: the lifecycle violation fails explicitly
    with pytest.raises(RuntimeError, match=message):
        portable_smoke._exercise_gui(tmp_path, tmp_path, {})


def test_portable_gui_times_out_and_terminates_hidden_window(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a live process that never presents a visible window
    process = FakeGuiProcess()
    _windows(monkeypatch, process)
    times = iter((0.0, 0.0, 31.0))
    monkeypatch.setattr(portable_smoke.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(portable_smoke.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(
        portable_smoke,
        "_close_windows_process_window",
        lambda item, expected_title: False,
    )

    # When/Then: bounded startup terminates the process and reports timeout
    with pytest.raises(RuntimeError, match="did not open"):
        portable_smoke._exercise_gui(tmp_path, tmp_path, {})
    assert process.terminated is True


def test_portable_gui_terminates_process_when_window_inspection_fails(
    tmp_path: Path, monkeypatch
) -> None:
    process = FakeGuiProcess()
    _windows(monkeypatch, process)
    monkeypatch.setattr(
        portable_smoke,
        "_close_windows_process_window",
        lambda item, expected_title: (_ for _ in ()).throw(
            RuntimeError("unexpected GUI window")
        ),
    )

    with pytest.raises(RuntimeError, match="unexpected GUI window"):
        portable_smoke._exercise_gui(tmp_path, tmp_path, {})

    assert process.terminated is True
    assert process.wait_calls == 1


def test_portable_gui_kills_process_when_termination_does_not_finish(
    tmp_path: Path, monkeypatch
) -> None:
    process = FakeGuiProcess(wait_timeout_once=True)
    _windows(monkeypatch, process)
    monkeypatch.setattr(
        portable_smoke,
        "_close_windows_process_window",
        lambda item, expected_title: (_ for _ in ()).throw(
            RuntimeError("unexpected GUI window")
        ),
    )

    with pytest.raises(RuntimeError, match="unexpected GUI window"):
        portable_smoke._exercise_gui(tmp_path, tmp_path, {})

    assert process.terminated is True
    assert process.killed is True
    assert process.wait_calls == 2


@pytest.mark.parametrize(
    ("windows", "message"),
    [
        (
            (windows_window_probe.VisibleWindow(1, "Phatch error", "#32770", 0, 0),),
            "unexpected GUI window.*#32770",
        ),
        (
            (
                windows_window_probe.VisibleWindow(
                    1, "actions - Phatch", "wxDialog", 0, 0x10CF0000
                ),
            ),
            "unexpected GUI window.*wxDialog",
        ),
        (
            (
                windows_window_probe.VisibleWindow(
                    1, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
                ),
                windows_window_probe.VisibleWindow(2, "Phatch error", "wxDialog", 1, 0),
            ),
            "unexpected GUI window.*wxDialog",
        ),
    ],
)
def test_portable_gui_rejects_dialog_only_and_mixed_windows(
    windows: tuple[windows_window_probe.VisibleWindow, ...], message: str
) -> None:
    with pytest.raises(RuntimeError, match=message):
        windows_window_probe.select_main_window(windows, "actions - Phatch")


def test_portable_gui_accepts_only_expected_unowned_main_frame() -> None:
    main = windows_window_probe.VisibleWindow(
        7, "actions - Phatch", "wxWindowNR", 0, 0x10CF0000
    )

    assert windows_window_probe.select_main_window((main,), "actions - Phatch") == 7


@pytest.mark.parametrize("leak", ["home", "log"])
def test_portable_main_rejects_state_or_logged_traceback(
    tmp_path: Path, monkeypatch, leak: str
) -> None:
    # Given: a complete portable root whose smoke leaves prohibited evidence
    root = tmp_path / "root"
    (root / "portable-data").mkdir(parents=True)
    (root / "Phatch.exe").write_bytes(b"exe")
    (root / "Phatch-GUI.exe").write_bytes(b"exe")

    def console(root: Path, work: Path, environment: dict[str, str]) -> None:
        del work
        if leak == "home":
            home = Path(environment["HOME"])
            home.mkdir()
            (home / "state").write_text("state", encoding="utf-8")
        else:
            logs = root / "portable-data" / "cache" / "logs"
            logs.mkdir(parents=True)
            (logs / "phatch.log").write_text("Traceback", encoding="utf-8")

    monkeypatch.setattr(portable_smoke, "_exercise_console", console)
    monkeypatch.setattr(portable_smoke, "_exercise_gui", lambda *args: None)

    # When/Then: portable isolation and clean logs are mandatory
    with pytest.raises(RuntimeError, match=r"outside|logged an error"):
        portable_smoke.main((str(root),))


def test_portable_main_requires_observable_portable_state(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: a complete portable root whose applications create no state
    root = tmp_path / "root"
    (root / "portable-data").mkdir(parents=True)
    (root / "portable-data" / ".keep").write_text("", encoding="utf-8")
    (root / "Phatch.exe").write_bytes(b"exe")
    (root / "Phatch-GUI.exe").write_bytes(b"exe")
    monkeypatch.setattr(portable_smoke, "_exercise_console", lambda *args: None)
    monkeypatch.setattr(portable_smoke, "_exercise_gui", lambda *args: None)

    # When/Then: missing portable state fails the isolation smoke
    with pytest.raises(RuntimeError, match="did not create portable state"):
        portable_smoke.main((str(root),))
