#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run scripts/portable_smoke.py PORTABLE_ROOT

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Final, Protocol

import scripts.windows_window_probe as windows_window_probe
from scripts.portable_state import PortableStateSnapshot

PNG: Final = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAFElEQVR4nGP8z8DAwMDA"
    "xMDAwMAAAAwBAQDJ/pLvAAAAAElFTkSuQmCC"
)
TIMEOUT_SECONDS: Final = 60
STORAGE_ENVIRONMENT_VARIABLES: Final = (
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "XDG_CONFIG_HOME",
    "XDG_DATA_HOME",
    "XDG_CACHE_HOME",
    "XDG_STATE_HOME",
)
PORTABLE_STATE_ROOTS: Final = frozenset(("config", "data", "cache"))
IS_WINDOWS: Final = os.name == "nt"


class ProcessIdentity(Protocol):
    pid: int


def _run(
    executable: Path,
    arguments: tuple[str, ...],
    *,
    work: Path,
    environment: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [str(executable), *arguments],
        cwd=work,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{executable.name} exited {completed.returncode}: {completed.stderr}"
        )
    return completed


def _write_action_list(path: Path, output: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "portable smoke",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "png",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _exercise_console(root: Path, work: Path, environment: dict[str, str]) -> None:
    console = root / "Phatch.exe"
    action_list = work / "actions Ω.phatch"
    output = work / "processed output Ω"
    journal = work / "resume journal Ω.jsonl"
    inputs = tuple(work / f"input Ω {index}.png" for index in range(4))
    for image in inputs:
        image.write_bytes(PNG)
    _write_action_list(action_list, output)
    _run(console, ("--help",), work=work, environment=environment)
    capabilities = _run(
        console,
        ("--capabilities", "--report-format=json"),
        work=work,
        environment=environment,
    )
    if json.loads(capabilities.stdout)["outcome"] != "success":
        raise RuntimeError("capability report failed")
    dry_run = _run(
        console,
        ("--dry-run", "--report-format=json", str(action_list), str(inputs[0])),
        work=work,
        environment=environment,
    )
    if json.loads(dry_run.stdout)["outcome"] != "success":
        raise RuntimeError("preflight failed")
    parallel = _run(
        console,
        (
            "--max-workers",
            "2",
            "--verbose",
            "--report-format=json",
            str(action_list),
            *(str(image) for image in inputs),
        ),
        work=work,
        environment=environment,
    )
    if json.loads(parallel.stdout)["outcome"] != "success":
        raise RuntimeError("parallel processing failed")
    trace = re.search(
        r"execution_mode=process .*effective_workers=(\d+) worker_pids=([0-9,]+)",
        parallel.stderr,
    )
    if (
        trace is None
        or int(trace.group(1)) < 2
        or len(set(trace.group(2).split(","))) < 2
    ):
        raise RuntimeError("parallel processing lacks distinct worker evidence")
    resume_arguments = (
        "--resume",
        str(journal),
        "--report-format=json",
        str(action_list),
        str(inputs[0]),
    )
    _run(console, resume_arguments, work=work, environment=environment)
    _run(console, resume_arguments, work=work, environment=environment)
    if not journal.is_file() or len(tuple(output.glob("*.png"))) != len(inputs):
        raise RuntimeError("portable output or recovery journal is missing")


def _close_windows_process_window(
    process: ProcessIdentity, expected_title: str
) -> bool:
    return windows_window_probe.close_process_main_window(process, expected_title)


def _exercise_gui(root: Path, work: Path, environment: dict[str, str]) -> None:
    if not IS_WINDOWS:
        raise RuntimeError("portable GUI smoke requires native Windows")
    gui = root / "Phatch-GUI.exe"
    action_list = work / "actions Ω.phatch"
    process = subprocess.Popen(
        [str(gui), str(action_list)], cwd=work, env=environment, text=True
    )
    expected_title = f"{action_list.stem} - Phatch"
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"GUI exited before opening: {process.returncode}")
            if _close_windows_process_window(process, expected_title):
                process.wait(timeout=30)
                if process.returncode != 0:
                    raise RuntimeError(f"GUI exited {process.returncode}")
                return
            time.sleep(0.1)
        raise RuntimeError(
            f"expected GUI main frame {expected_title!r} did not open within 30 seconds"
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("portable_root", type=Path)
    options = parser.parse_args(arguments)
    root = options.portable_root.resolve()
    portable_data = root / "portable-data"
    required = (root / "Phatch.exe", root / "Phatch-GUI.exe", portable_data)
    if not all(path.exists() for path in required):
        parser.error("portable root is missing executables or portable-data")
    initial_state = PortableStateSnapshot.capture(portable_data)
    with tempfile.TemporaryDirectory(prefix="phatch portable smoke Ω ") as temporary:
        work = Path(temporary) / "work with spaces Ω"
        work.mkdir()
        environment = dict(os.environ)
        poisoned_paths = tuple(
            Path(temporary) / f"outside {name.lower()}"
            for name in STORAGE_ENVIRONMENT_VARIABLES
        )
        environment.update(
            {
                name: str(path)
                for name, path in zip(
                    STORAGE_ENVIRONMENT_VARIABLES, poisoned_paths, strict=True
                )
            }
        )
        environment.pop("PYTHONPATH", None)
        _exercise_console(root, work, environment)
        _exercise_gui(root, work, environment)
        if any(path.exists() for path in poisoned_paths):
            raise RuntimeError("portable application wrote outside portable-data")
        if not initial_state.is_unchanged():
            raise RuntimeError(
                "portable application modified pre-existing portable state"
            )
        created_files = initial_state.created_files()
        runtime_state = tuple(
            relative
            for relative in created_files
            if relative.parts
            and relative.parts[0] in PORTABLE_STATE_ROOTS
            and relative.name != ".keep"
        )
        if not runtime_state:
            raise RuntimeError("portable application did not create portable state")
        for relative in runtime_state:
            log = portable_data / relative
            if relative.parts[:2] != ("cache", "logs") or log.suffix != ".log":
                continue
            if "traceback" in log.read_text(encoding="utf-8", errors="replace").lower():
                raise RuntimeError(f"portable application logged an error: {log.name}")
        initial_state.clean_created(created_files)
    print(
        "portable console, GUI, resources, paths, preflight, process, and resume passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
