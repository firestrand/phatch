import os
import signal
import tempfile
import threading
import time
from functools import partial
from pathlib import Path

import pytest
from PIL import Image

from phatch.services import parallel_image_pool
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobFailure,
    ImageJobSuccess,
    execute_image_jobs,
)


def _job(tmp_path: Path, index: int, size: tuple[int, int]) -> ImageJob:
    source = tmp_path / f"source-{index}.png"
    Image.new("RGB", size, (index, 20, 30)).save(source)
    return ImageJob(
        index,
        source,
        tmp_path / f"output-{index}.png",
        tmp_path / f"stage-{index}.png",
        "PNG",
        size[0] * size[1],
    )


def test_single_frame_output_does_not_decode_later_frames(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "truncated-animation.gif"
    first = Image.new("RGB", (12, 9), "red")
    second = Image.new("RGB", (12, 9), "blue")
    first.save(source, save_all=True, append_images=[second])
    encoded = source.read_bytes()
    frame_markers = [index for index, value in enumerate(encoded) if value == 0x2C]
    source.write_bytes(encoded[: frame_markers[1]] + b";")
    job = ImageJob(
        0,
        source,
        tmp_path / "output.png",
        tmp_path / "stage.png",
        "PNG",
        108,
        frame_count=2,
        retains_animation=False,
    )

    # When
    result = execute_image_jobs((job,), 1)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)


@pytest.mark.skipif(os.name == "nt", reason="POSIX process-kill probe")
def test_real_worker_crash_preserves_completed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    jobs = [_job(tmp_path, 0, (8, 6))]
    jobs.extend(_job(tmp_path, index, (3500, 3500)) for index in range(1, 3))
    real_temporary_directory = tempfile.TemporaryDirectory

    monkeypatch.setattr(
        parallel_image_pool.tempfile,
        "TemporaryDirectory",
        partial(real_temporary_directory, dir=tmp_path),
    )
    killed = threading.Event()

    def kill_after_first_result() -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            registries = tuple(tmp_path.glob("phatch-worker-pids-*"))
            if jobs[0].stage.exists() and registries:
                markers = tuple(registries[0].iterdir())
                if markers:
                    os.kill(int(markers[0].name), signal.SIGKILL)
                    killed.set()
                    return
            time.sleep(0.01)

    killer = threading.Thread(target=kill_after_first_result)
    killer.start()

    # When
    result = execute_image_jobs(tuple(jobs), 2)
    killer.join(timeout=10)

    # Then
    assert killed.is_set()
    assert isinstance(result.results[0], ImageJobSuccess)
    assert any(isinstance(item, ImageJobFailure) for item in result.results[1:])
