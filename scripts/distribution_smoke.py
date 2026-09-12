#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["build>=1.3"]
# ///

# How to run: uv run scripts/distribution_smoke.py SDIST_DIR OUTPUT_DIR

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Final

TIMEOUT_SECONDS: Final = 180


def _run(arguments: list[str | Path], *, cwd: Path | None = None) -> None:
    subprocess.run(arguments, cwd=cwd, check=True, timeout=TIMEOUT_SECONDS)


def _installed_commands(environment: Path, *, windows: bool) -> tuple[Path, Path, Path]:
    scripts = environment / ("Scripts" if windows else "bin")
    python = scripts / ("python.exe" if windows else "python")
    phatch = scripts / ("phatch.exe" if windows else "phatch")
    phatch_gui = scripts / ("phatch-gui.exe" if windows else "phatch-gui")
    return python, phatch, phatch_gui


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("sdist_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    options = parser.parse_args(arguments)
    sdists = tuple(options.sdist_dir.glob("*.tar.gz"))
    if len(sdists) != 1:
        parser.error(f"expected one sdist, found {len(sdists)}")
    options.output_dir.mkdir(parents=True, exist_ok=True)
    existing_wheels = frozenset(options.output_dir.glob("*.whl"))
    with tempfile.TemporaryDirectory(prefix="phatch sdist Ω ") as raw_temporary:
        temporary = Path(raw_temporary)
        shutil.unpack_archive(sdists[0], temporary)
        sources = tuple(path for path in temporary.iterdir() if path.is_dir())
        if len(sources) != 1:
            parser.error(f"expected one extracted source root, found {len(sources)}")
        _run(
            [
                sys.executable,
                "-m",
                "build",
                "--wheel",
                "--outdir",
                options.output_dir.resolve(),
            ],
            cwd=sources[0],
        )
        environment = temporary / "clean install Ω"
        _run([sys.executable, "-m", "venv", environment])
        python, phatch, phatch_gui = _installed_commands(
            environment, windows=os.name == "nt"
        )
        wheels = tuple(set(options.output_dir.glob("*.whl")) - existing_wheels)
        if len(wheels) != 1:
            parser.error(f"expected one newly built wheel, found {len(wheels)}")
        wheel = wheels[0]
        _run(["uv", "pip", "install", "--python", python, f"{wheel}[gui,windows]"])
        work = temporary / "unrelated work Ω"
        work.mkdir()
        _run([phatch, "--help"], cwd=work)
        _run([phatch_gui, "--help"], cwd=work)
        _run(
            [
                python,
                "-c",
                "from phatch.resources.provider import ResourceProvider; "
                "assert ResourceProvider().read_bytes('data/geek.txt')",
            ],
            cwd=work,
        )
        _run(
            [
                python,
                "-c",
                "import importlib,pkgutil,phatch.actions; "
                "[importlib.import_module(info.name) for info in "
                "pkgutil.iter_modules(phatch.actions.__path__, 'phatch.actions.') "
                "if not info.name.endswith('.common')]",
            ],
            cwd=work,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
