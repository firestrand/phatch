from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import pytest
from PIL import Image


@dataclass(frozen=True, slots=True)
class InstalledPhatch:
    command: Path
    environment: dict[str, str]
    work: Path

    def run(
        self,
        *arguments: str,
        path: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = dict(self.environment)
        if path is not None:
            environment["PATH"] = path
        return subprocess.run(
            [str(self.command), *arguments],
            cwd=self.work,
            check=False,
            capture_output=True,
            env=environment,
            text=True,
            timeout=60,
        )

    def start(self, *arguments: str) -> subprocess.Popen[str]:
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        return subprocess.Popen(
            [str(self.command), *arguments],
            cwd=self.work,
            env=self.environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )


def _run_checked(
    arguments: list[str | Path],
    *,
    cwd: Path | None = None,
    environment: dict[str, str],
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        check=True,
        capture_output=True,
        env=environment,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope="module")
def installed_phatch(tmp_path_factory: pytest.TempPathFactory) -> InstalledPhatch:
    project_root = Path(__file__).resolve().parents[2]
    root = tmp_path_factory.mktemp("installed wheel automation Ω")
    distribution = root / "dist"
    environment = {**os.environ, "PIP_DISABLE_PIP_VERSION_CHECK": "1"}
    environment.pop("PYTHONPATH", None)
    _run_checked(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            distribution,
        ],
        cwd=project_root,
        environment=environment,
        timeout=120,
    )
    virtual_environment = root / "venv"
    _run_checked(
        [sys.executable, "-m", "venv", "--system-site-packages", virtual_environment],
        environment=environment,
        timeout=60,
    )
    scripts = virtual_environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    wheel = next(distribution.glob("*.whl"))
    _run_checked(
        [python, "-m", "pip", "install", "--no-deps", wheel],
        environment=environment,
        timeout=120,
    )

    home = root / "isolated home"
    work = root / "work Ω"
    work.mkdir()
    installed_environment = {
        **environment,
        "HOME": str(home),
        "PYTHONPATH": os.pathsep.join(
            path for path in sys.path if "site-packages" in path
        ),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_CONFIG_HOME": str(home / "config"),
        "XDG_DATA_HOME": str(home / "data"),
    }
    imported = _run_checked(
        [python, "-c", "import phatch; print(phatch.__file__)"],
        cwd=work,
        environment=installed_environment,
        timeout=30,
    )
    assert str(project_root) not in imported.stdout
    assert "site-packages" in imported.stdout
    command = scripts / ("phatch.exe" if os.name == "nt" else "phatch")
    return InstalledPhatch(command, installed_environment, work)


def _write_action_list(
    path: Path,
    action_id: str = "border",
    fields: dict[str, str] | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "installed wheel automation",
                "actions": [{"id": action_id, "fields": fields or {}}],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.slow
def test_installed_wheel_dry_run_is_read_only_and_supports_unicode_paths(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "actions Ω.phatch"
    image = installed_phatch.work / "input Ω.png"
    _write_action_list(action_list)
    Image.new("RGB", (2, 2)).save(image)
    before = set(installed_phatch.work.rglob("*"))
    completed = installed_phatch.run(
        "--dry-run", "--report-format=json", str(action_list), str(image)
    )

    assert completed.stdout, completed.stderr
    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr
    assert payload.keys() == {
        "conflicts",
        "estimated_work",
        "inputs",
        "invalid_fields",
        "kind",
        "outcome",
        "planned_outputs",
        "report_version",
        "unavailable_capabilities",
        "unsafe_operations",
    }
    assert payload["outcome"] == "success"
    assert payload["inputs"][0].endswith("input Ω.png")
    assert set(installed_phatch.work.rglob("*")) == before


@pytest.mark.slow
def test_installed_wheel_reports_real_processing_failure(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "failure actions.phatch"
    image = installed_phatch.work / "broken input.png"
    _write_action_list(action_list)
    image.write_bytes(b"not an image")

    completed = installed_phatch.run(
        "--no-save", "--report-format=json", str(action_list), str(image)
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 4, completed.stderr
    assert payload["report_version"] == 1
    assert payload["outcome"] == "processing_failure"


@pytest.mark.slow
def test_installed_wheel_reports_real_partial_success(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "partial actions.phatch"
    good = installed_phatch.work / "partial good" / "good.png"
    bad = installed_phatch.work / "partial bad" / "bad.png"
    good.parent.mkdir()
    bad.parent.mkdir()
    (good.parent / "output").mkdir()
    (bad.parent / "output").write_text("blocks directory", encoding="utf-8")
    desktop = Path(installed_phatch.environment["HOME"]) / "Desktop"
    desktop.mkdir(parents=True)
    (desktop / "bad.png").mkdir()
    Image.new("RGB", (2, 2)).save(good)
    Image.new("RGB", (2, 2)).save(bad)
    _write_action_list(
        action_list,
        "save",
        {
            "in": "<folder>/output",
            "file_name": "<filename>",
            "as": "<type>",
        },
    )

    completed = installed_phatch.run(
        "--report-format=json", str(action_list), str(good), str(bad)
    )

    assert completed.stdout, completed.stderr
    payload = json.loads(completed.stdout)
    assert completed.returncode == 1, completed.stderr
    assert payload["outcome"] == "partial_success"
    assert len(payload["files"]) == 2
    assert payload["issues"]


@pytest.mark.slow
def test_installed_wheel_reports_validation_and_unavailable_capability(
    installed_phatch: InstalledPhatch,
) -> None:
    validation = installed_phatch.run("--dry-run", "--report-format=json")
    unavailable_actions = installed_phatch.work / "unavailable Ω.phatch"
    image = installed_phatch.work / "unavailable input.png"
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(unavailable_actions, "blender")
    unavailable = installed_phatch.run(
        "--dry-run",
        "--report-format=json",
        str(unavailable_actions),
        str(image),
        path="",
    )

    assert validation.returncode == 2
    assert json.loads(validation.stdout) == {
        "issues": ["No action list provided."],
        "kind": "error",
        "outcome": "validation_failure",
        "report_version": 1,
    }
    unavailable_payload = json.loads(unavailable.stdout)
    assert unavailable.returncode == 3, unavailable.stderr
    assert unavailable_payload["kind"] == "preflight"
    assert unavailable_payload["outcome"] == "unavailable_capability"
    assert unavailable_payload["unavailable_capabilities"]


@pytest.mark.slow
@pytest.mark.parametrize("kind", ["missing", "empty", "absent"])
def test_installed_wheel_reports_input_validation_without_traceback(
    installed_phatch: InstalledPhatch, kind: str
) -> None:
    action_list = installed_phatch.work / f"{kind} input actions.phatch"
    _write_action_list(action_list)
    empty = installed_phatch.work / f"{kind} empty"
    empty.mkdir()
    paths = {
        "missing": (str(installed_phatch.work / "missing.png"),),
        "empty": (str(empty),),
        "absent": (),
    }[kind]

    completed = installed_phatch.run(
        "--dry-run", "--report-format=json", str(action_list), *paths
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 2
    assert payload["outcome"] == "validation_failure"
    assert "Traceback" not in completed.stderr


@pytest.mark.slow
@pytest.mark.parametrize("value", ["<open>", "=__import__('os')"])
def test_installed_wheel_reports_invalid_field_values_without_traceback(
    installed_phatch: InstalledPhatch, value: str
) -> None:
    action_list = installed_phatch.work / "invalid field actions.phatch"
    image = installed_phatch.work / "invalid field input.png"
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(action_list, "scale", {"canvas_width": value})

    completed = installed_phatch.run(
        "--dry-run", "--report-format=json", str(action_list), str(image)
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 2
    assert payload["outcome"] == "validation_failure"
    assert "Traceback" not in completed.stderr


@pytest.mark.slow
def test_installed_wheel_planned_output_matches_execution_report(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "output parity actions.phatch"
    image = installed_phatch.work / "output parity input.png"
    output = installed_phatch.work / "output parity"
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(
        action_list,
        "save",
        {
            "in": str(output),
            "file_name": "<filename>.thumb",
            "as": "<type>",
        },
    )

    planned = installed_phatch.run(
        "--dry-run", "--report-format=json", str(action_list), str(image)
    )
    executed = installed_phatch.run(
        "--report-format=json", str(action_list), str(image)
    )

    planned_path = json.loads(planned.stdout)["planned_outputs"]
    reported_path = json.loads(executed.stdout)["files"][0]["outputs"]
    assert planned.returncode == 0, planned.stderr
    assert executed.returncode == 0, executed.stderr
    assert planned_path == reported_path


def _assert_installed_output_path_parity(
    installed_phatch: InstalledPhatch,
    action_list_name: str,
    output: str,
) -> None:
    action_list = installed_phatch.work / action_list_name
    image = installed_phatch.work / f"{action_list_name}.png"
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(
        action_list,
        "save",
        {"in": output, "file_name": "<filename>", "as": "<type>"},
    )

    planned = installed_phatch.run(
        "--dry-run", "--report-format=json", str(action_list), str(image)
    )
    executed = installed_phatch.run(
        "--report-format=json", str(action_list), str(image)
    )

    assert planned.returncode == 0, planned.stderr
    assert executed.returncode == 0, executed.stderr
    assert (
        json.loads(planned.stdout)["planned_outputs"]
        == json.loads(executed.stdout)["files"][0]["outputs"]
    )


@pytest.mark.slow
def test_installed_wheel_relative_output_matches_canonical_plan(
    installed_phatch: InstalledPhatch,
) -> None:
    _assert_installed_output_path_parity(
        installed_phatch, "relative-output-parity.phatch", "relative-output"
    )


@pytest.mark.slow
def test_installed_wheel_symlink_alias_output_matches_canonical_plan(
    installed_phatch: InstalledPhatch,
) -> None:
    canonical_output = installed_phatch.work / "canonical-output"
    alias_output = installed_phatch.work / "alias-output"
    canonical_output.mkdir()
    alias_output.symlink_to(canonical_output, target_is_directory=True)

    _assert_installed_output_path_parity(
        installed_phatch, "alias-output-parity.phatch", str(alias_output)
    )


@pytest.mark.slow
def test_installed_wheel_recursive_plan_matches_execution_subfolder(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "recursive parity actions.phatch"
    source_root = installed_phatch.work / "recursive inputs"
    image = source_root / "nested" / "input.png"
    output = installed_phatch.work / "recursive output"
    image.parent.mkdir(parents=True)
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(
        action_list,
        "save",
        {
            "in": f"{output}/<subfolder>",
            "file_name": "<filename>",
            "as": "<type>",
        },
    )

    planned = installed_phatch.run(
        "--dry-run",
        "--recursive",
        "--report-format=json",
        str(action_list),
        str(source_root),
    )
    executed = installed_phatch.run(
        "--recursive", "--report-format=json", str(action_list), str(source_root)
    )

    planned_path = json.loads(planned.stdout)["planned_outputs"]
    reported_path = json.loads(executed.stdout)["files"][0]["outputs"]
    assert planned.returncode == 0, planned.stderr
    assert executed.returncode == 0, executed.stderr
    assert planned_path == reported_path


@pytest.mark.slow
def test_installed_wheel_reports_user_cancellation(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "cancel actions.phatch"
    image = installed_phatch.work / "cancel input.png"
    _write_action_list(action_list, "median")
    Image.new("RGB", (5000, 5000)).save(image)
    process = installed_phatch.start(
        "--no-save", "--report-format=json", str(action_list), str(image)
    )
    time.sleep(0.5)
    if process.poll() is not None:
        stdout, stderr = process.communicate()
        pytest.fail(f"process completed before cancellation: {stdout=} {stderr=}")
    interrupt = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
    process.send_signal(interrupt)
    stdout, stderr = process.communicate(timeout=30)

    assert process.returncode == 130, stderr
    assert json.loads(stdout)["outcome"] == "user_cancellation"


@pytest.mark.slow
def test_parallel_sigint_terminates_workers_and_cleans_stages(
    installed_phatch: InstalledPhatch,
) -> None:
    output = installed_phatch.work / "parallel cancel output"
    action_list = installed_phatch.work / "parallel cancel.phatch"
    inputs = []
    for index in range(8):
        image = installed_phatch.work / f"cancel-parallel-{index}.png"
        Image.new("RGB", (3000, 3000), (index, 30, 60)).save(image)
        inputs.append(image)
    _write_action_list(
        action_list,
        "save",
        {
            "in": str(output),
            "file_name": "<filename>",
            "as": "png",
            "metadata": "no",
            "resolution": "72",
        },
    )
    process = installed_phatch.start(
        "--max-workers",
        "2",
        "--report-format=json",
        str(action_list),
        *(str(path) for path in inputs),
    )
    worker_pids: set[int] = set()
    if os.name == "nt":
        time.sleep(0.5)
    else:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and len(worker_pids) < 2:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"process completed before SIGINT: {stdout=} {stderr=}")
            worker_pids = _spawn_worker_pids(process.pid)
            time.sleep(0.01)
        assert len(worker_pids) >= 2

    interrupted = time.monotonic()
    interrupt = signal.CTRL_BREAK_EVENT if os.name == "nt" else signal.SIGINT
    process.send_signal(interrupt)
    stdout, stderr = process.communicate(timeout=5)
    elapsed = time.monotonic() - interrupted

    assert process.returncode == 130, stderr
    assert json.loads(stdout)["outcome"] == "user_cancellation"
    assert elapsed < 3
    if os.name != "nt":
        remaining_pids = {pid for pid in worker_pids if _pid_exists(pid)}
        assert remaining_pids == set()
    temporary = Path(tempfile.gettempdir())
    assert all(
        not tuple(temporary.glob(f".{input_path.name}.worker-*"))
        for input_path in inputs
    )


@pytest.mark.slow
def test_installed_wheel_resumes_from_recovery_journal(
    installed_phatch: InstalledPhatch,
) -> None:
    action_list = installed_phatch.work / "resume actions.phatch"
    image = installed_phatch.work / "resume input.png"
    output = installed_phatch.work / "resume output"
    journal = installed_phatch.work / "resume journal.jsonl"
    Image.new("RGB", (2, 2)).save(image)
    _write_action_list(
        action_list,
        "save",
        {
            "in": str(output),
            "file_name": "<filename>",
            "as": "<type>",
        },
    )
    arguments = (
        "--resume",
        str(journal),
        "--report-format=json",
        str(action_list),
        str(image),
    )

    first = installed_phatch.run(*arguments)
    second = installed_phatch.run(*arguments)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert journal.is_file()
    assert json.loads(first.stdout)["outcome"] == "success"
    assert json.loads(second.stdout)["outcome"] == "success"


@pytest.mark.slow
def test_installed_wheel_parallel_save_reports_real_worker_pids(
    installed_phatch: InstalledPhatch,
) -> None:
    inputs = []
    for index in range(4):
        image = installed_phatch.work / f"parallel-{index}.png"
        Image.effect_noise((1024, 1024), 48).convert("RGB").save(image)
        inputs.append(image)
    action_list = installed_phatch.work / "parallel-save.phatch"
    output = installed_phatch.work / "parallel-output"
    _write_action_list(
        action_list,
        "save",
        {
            "in": str(output),
            "file_name": "<filename>",
            "as": "png",
            "metadata": "no",
            "resolution": "72",
        },
    )

    completed = installed_phatch.run(
        "--verbose",
        "--max-workers",
        "2",
        "--report-format=json",
        str(action_list),
        *(str(path) for path in inputs),
    )

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr
    assert payload["outcome"] == "success"
    assert [Path(item["source"]).name for item in payload["files"]] == [
        path.name for path in inputs
    ]
    trace = next(
        line
        for line in completed.stderr.splitlines()
        if line.startswith("execution_mode")
    )
    worker_pids = trace.partition("worker_pids=")[2].split(",")
    assert trace.startswith("execution_mode=process")
    assert len(worker_pids) == 2


def _spawn_worker_pids(root_pid: int) -> set[int]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,command="],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = tuple(
        (int(parts[0]), int(parts[1]), parts[2])
        for line in completed.stdout.splitlines()
        if len(parts := line.split(maxsplit=2)) == 3
    )
    descendants = {root_pid}
    while True:
        expanded = descendants | {
            pid for pid, parent_pid, _command in rows if parent_pid in descendants
        }
        if expanded == descendants:
            return {
                pid
                for pid, _parent_pid, command in rows
                if pid in descendants and "multiprocessing.spawn" in command
            }
        descendants = expanded


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
