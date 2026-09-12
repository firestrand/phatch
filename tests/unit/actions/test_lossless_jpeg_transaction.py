from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image

from phatch.actions import _lossless_jpeg_transaction as transaction
from phatch.actions._lossless_jpeg_transaction import (
    InvalidJpegOutputError,
    LosslessJpegRequest,
    LosslessProcessPaths,
    run_lossless_jpeg,
)
from phatch.lib.process import Command, ProcessExitError, ProcessResult
from phatch.lib.subprocess_runner import StdlibProcessRunner


def write_fake_tool(path: Path) -> None:
    path.write_text(
        "from pathlib import Path\n"
        "import shutil, sys\n"
        "mode, source, output = sys.argv[1:]\n"
        "if mode == 'fail':\n"
        "    Path(output).write_bytes(b'partial')\n"
        "    raise SystemExit(7)\n"
        "shutil.copyfile(source, output)\n",
        encoding="utf-8",
    )


def command_for(script: Path, mode: str):
    def build(paths: LosslessProcessPaths) -> Command:
        return Command(
            (sys.executable, str(script), mode, str(paths.source), str(paths.output))
        )

    return build


def test_lossless_transaction_replaces_only_after_valid_jpeg(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "destination.jpg"
    script = tmp_path / "fake tool.py"
    Image.new("RGB", (2, 3), "red").save(source)
    destination.write_bytes(b"old destination")
    write_fake_tool(script)

    run_lossless_jpeg(
        LosslessJpegRequest(source, destination, preserve_timestamp=False),
        StdlibProcessRunner(),
        command_for(script, "valid"),
    )

    with Image.open(destination) as result:
        assert result.format == "JPEG"
        assert result.size == (2, 3)


def test_lossless_transaction_preserves_source_and_destination_on_child_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "destination.jpg"
    script = tmp_path / "fake tool.py"
    Image.new("RGB", (2, 3), "red").save(source)
    source_before = source.read_bytes()
    destination.write_bytes(b"old destination")
    write_fake_tool(script)

    with pytest.raises(ProcessExitError):
        run_lossless_jpeg(
            LosslessJpegRequest(source, destination, preserve_timestamp=False),
            StdlibProcessRunner(),
            command_for(script, "fail"),
        )

    assert source.read_bytes() == source_before
    assert destination.read_bytes() == b"old destination"


def test_lossless_transaction_preserves_source_timestamp_for_in_place_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.jpg"
    script = tmp_path / "fake tool.py"
    Image.new("RGB", (2, 3), "red").save(source)
    expected_ns = 946684800_123456789
    source.touch()
    source.chmod(0o600)
    os.utime(source, ns=(expected_ns, expected_ns))
    write_fake_tool(script)

    run_lossless_jpeg(
        LosslessJpegRequest(source, source, preserve_timestamp=True),
        StdlibProcessRunner(),
        command_for(script, "valid"),
    )

    assert source.stat().st_mtime_ns == expected_ns


def test_transaction_rejects_non_jpeg_output(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "destination.jpg"
    Image.new("RGB", (2, 2)).save(source)
    destination.write_bytes(b"old")
    paths_seen: list[LosslessProcessPaths] = []

    def build(paths: LosslessProcessPaths) -> Command:
        paths_seen.append(paths)
        return Command(("fake",))

    class Runner:
        def run(
            self,
            command: Command,
            *,
            cancelled: Callable[[], bool] | None = None,
        ) -> ProcessResult:
            Image.new("RGB", (1, 1)).save(paths_seen[0].output, "PNG")
            return ProcessResult(command, 0, "", "")

    with pytest.raises(InvalidJpegOutputError, match="PNG"):
        run_lossless_jpeg(
            LosslessJpegRequest(source, destination, False), Runner(), build
        )
    assert destination.read_bytes() == b"old"


def test_final_staging_is_removed_when_replace_fails(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "destination.jpg"
    script = tmp_path / "tool.py"
    Image.new("RGB", (2, 2)).save(source)
    write_fake_tool(script)

    def fail_replace(*args):
        raise OSError("replace")

    monkeypatch.setattr(transaction.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace"):
        run_lossless_jpeg(
            LosslessJpegRequest(source, destination, False),
            StdlibProcessRunner(),
            command_for(script, "valid"),
        )
    assert not list(tmp_path.glob(".destination.jpg.*.tmp"))


def test_final_staging_is_removed_after_fsync_error(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "output.jpg"
    destination = tmp_path / "destination.jpg"
    source.write_bytes(b"jpeg")

    def fail_fsync(descriptor):
        raise OSError("fsync")

    monkeypatch.setattr(transaction.os, "fsync", fail_fsync)
    with pytest.raises(OSError, match="fsync"):
        transaction._copy_to_final_staging(source, destination)
    assert not list(tmp_path.glob(".destination.jpg.*.tmp"))
