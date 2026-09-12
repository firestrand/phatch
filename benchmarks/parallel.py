# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["Pillow>=11.3.0,<12"]
# ///

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True, slots=True)
class Workload:
    name: str
    width: int
    height: int
    files: int


@dataclass(frozen=True, slots=True)
class Measurement:
    workload: str
    sample: int
    requested_workers: int
    elapsed_seconds: float
    peak_memory_bytes: int
    input_files: int
    pixels_per_file: int
    worker_trace: str


@dataclass(frozen=True, slots=True)
class BenchmarkFailure(RuntimeError):
    stdout: str
    stderr: str

    def __str__(self) -> str:
        return f"benchmark failed: {self.stdout}\n{self.stderr}"


WORKLOADS = (
    Workload("small", 512, 512, 8),
    Workload("medium", 1536, 1536, 5),
    Workload("large", 3072, 3072, 3),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    local_command = Path.cwd() / ".venv" / "bin" / "phatch"
    parser.add_argument(
        "--phatch",
        default=shutil.which("phatch") or local_command,
    )
    parser.add_argument("--samples", type=_positive_integer, default=3)
    options = parser.parse_args()
    if not options.phatch:
        parser.error("phatch executable is not installed in PATH")
    cpu_workers = os.cpu_count() or 1
    with tempfile.TemporaryDirectory(prefix="phatch-benchmark-") as raw_root:
        root = Path(raw_root)
        worker_counts = tuple(dict.fromkeys((1, min(2, cpu_workers), cpu_workers)))
        configurations = [
            (workload, workers, sample)
            for sample in range(1, options.samples + 1)
            for workload in WORKLOADS
            for workers in worker_counts
        ]
        random.Random(20260910).shuffle(configurations)
        measurements = [
            _measure(Path(options.phatch), root, workload, workers, sample)
            for workload, workers, sample in configurations
        ]
    print(
        json.dumps(
            {
                "schema_version": 1,
                "cpu_count": cpu_workers,
                "random_seed": 20260910,
                "samples": options.samples,
                "memory_scope": "coordinator plus descendant worker RSS",
                "measurements": [asdict(measurement) for measurement in measurements],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _measure(
    executable: Path,
    root: Path,
    workload: Workload,
    workers: int,
    sample: int,
) -> Measurement:
    case = root / workload.name
    case.mkdir(exist_ok=True)
    inputs = tuple(
        _create_input(case, workload, index) for index in range(workload.files)
    )
    output = case / f"output-{sample}-{workers}"
    action_list = case / f"save-{sample}-{workers}.phatch"
    action_list.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "parallel benchmark",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "jpg",
                            "jpeg_quality": "85",
                            "jpeg_size_maximum": "0 kb",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    started = time.perf_counter()
    process = subprocess.Popen(
        [
            str(executable),
            "--verbose",
            "--max-workers",
            str(workers),
            "--report-format=json",
            str(action_list),
            *(str(path) for path in inputs),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    peak_memory = 0
    while process.poll() is None:
        peak_memory = max(peak_memory, _process_tree_rss(process.pid))
        time.sleep(0.01)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter() - started
    if process.returncode != 0:
        raise BenchmarkFailure(stdout, stderr)
    trace = next(
        line for line in stderr.splitlines() if line.startswith("execution_mode=")
    )
    return Measurement(
        workload.name,
        sample,
        workers,
        elapsed,
        peak_memory,
        workload.files,
        workload.width * workload.height,
        trace,
    )


def _positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("samples must be at least one")
    return parsed


def _create_input(case: Path, workload: Workload, index: int) -> Path:
    path = case / f"input-{index}.png"
    if not path.exists():
        noise = Image.effect_noise((workload.width, workload.height), 48)
        noise.convert("RGB").save(path)
    return path


def _process_tree_rss(root_pid: int) -> int:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,ppid=,rss="],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = tuple(
        tuple(int(value) for value in line.split())
        for line in completed.stdout.splitlines()
    )
    descendants = {root_pid}
    changed = True
    while changed:
        expanded = descendants | {
            pid for pid, parent_pid, _rss in rows if parent_pid in descendants
        }
        changed = expanded != descendants
        descendants = expanded
    return sum(rss_kib * 1024 for pid, _parent, rss_kib in rows if pid in descendants)


if __name__ == "__main__":
    raise SystemExit(main())
