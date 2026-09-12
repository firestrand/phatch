from collections.abc import Callable
from concurrent.futures import Future
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path

import pytest
from PIL import Image

from phatch.services import parallel_image_jobs, parallel_image_pool
from phatch.services.parallel_image_jobs import (
    ESTIMATED_BYTES_PER_PIXEL,
    ESTIMATED_FRAME_OVERHEAD_BYTES,
    ImageJob,
    ImageJobFailure,
    ImageJobSuccess,
    execute_image_jobs,
)


def _job(tmp_path: Path, index: int = 0) -> ImageJob:
    source = tmp_path / f"source-{index}.png"
    Image.new("RGB", (8, 6), (index, 20, 30)).save(source)
    return ImageJob(
        index,
        source,
        tmp_path / f"output-{index}.png",
        tmp_path / f"stage-{index}.png",
        "PNG",
        48,
    )


class _RecordingExecutor:
    def __init__(
        self,
        outcomes: list[Future[ImageJobSuccess | ImageJobFailure] | BaseException],
    ) -> None:
        self.outcomes = outcomes
        self.submitted = 0
        self.shutdown_calls: list[tuple[bool, bool]] = []
        self.initializer_present = False

    def submit(
        self,
        function: Callable[[ImageJob], ImageJobSuccess | ImageJobFailure],
        job: ImageJob,
    ) -> Future[ImageJobSuccess | ImageJobFailure]:
        outcome = self.outcomes[self.submitted]
        self.submitted += 1
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def shutdown(self, wait: bool, *, cancel_futures: bool) -> None:
        self.shutdown_calls.append((wait, cancel_futures))


class _ExecutorConstructorProbe:
    initializer = None
    start_method = ""

    def __init__(
        self,
        *,
        max_workers: int,
        mp_context,
        initializer,
        initargs: tuple[Path],
    ) -> None:
        type(self).initializer = initializer
        type(self).start_method = mp_context.get_start_method()


def _completed(
    result: ImageJobSuccess | ImageJobFailure,
) -> Future[ImageJobSuccess | ImageJobFailure]:
    future: Future[ImageJobSuccess | ImageJobFailure] = Future()
    future.set_result(result)
    return future


def _failed(error: BaseException) -> Future[ImageJobSuccess | ImageJobFailure]:
    future: Future[ImageJobSuccess | ImageJobFailure] = Future()
    future.set_exception(error)
    return future


def test_submit_broken_pool_becomes_structured_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    jobs = (_job(tmp_path, 0), _job(tmp_path, 1))
    executor = _RecordingExecutor([BrokenProcessPool("submit failed")])
    monkeypatch.setattr(
        parallel_image_pool,
        "_create_executor",
        lambda _workers, _registry: executor,
        raising=False,
    )

    # When
    result = execute_image_jobs(jobs, 2)

    # Then
    assert all(isinstance(item, ImageJobFailure) for item in result.results)
    assert executor.shutdown_calls == [(True, True)]


def test_submit_pool_failure_preserves_already_completed_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    jobs = (_job(tmp_path, 0), _job(tmp_path, 1))
    success = ImageJobSuccess(
        0,
        jobs[0].source,
        jobs[0].destination,
        jobs[0].stage,
        8,
        6,
        "RGB",
        "PNG",
        1234,
    )
    executor = _RecordingExecutor(
        [_completed(success), BrokenProcessPool("submit failed")]
    )
    monkeypatch.setattr(
        parallel_image_pool,
        "_create_executor",
        lambda _workers, _registry: executor,
    )

    # When
    result = execute_image_jobs(jobs, 2)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    assert isinstance(result.results[1], ImageJobFailure)


def test_executor_uses_spawn_and_codec_initializer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    monkeypatch.setattr(
        parallel_image_pool, "ProcessPoolExecutor", _ExecutorConstructorProbe
    )

    # When
    parallel_image_pool._create_executor(2, tmp_path)

    # Then
    assert _ExecutorConstructorProbe.start_method == "spawn"
    assert (
        _ExecutorConstructorProbe.initializer is parallel_image_jobs._initialize_worker
    )


def test_future_failure_preserves_unrelated_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    jobs = (_job(tmp_path, 0), _job(tmp_path, 1))
    success = ImageJobSuccess(
        0,
        jobs[0].source,
        jobs[0].destination,
        jobs[0].stage,
        8,
        6,
        "RGB",
        "PNG",
        1234,
    )
    executor = _RecordingExecutor(
        [_completed(success), _failed(RuntimeError("worker failed"))]
    )
    monkeypatch.setattr(
        parallel_image_pool,
        "_create_executor",
        lambda _workers, _registry: executor,
        raising=False,
    )

    # When
    result = execute_image_jobs(jobs, 2)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    assert isinstance(result.results[1], ImageJobFailure)
    assert "worker failed" in result.results[1].reason


def test_keyboard_interrupt_uses_non_waiting_cancel_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given
    jobs = (_job(tmp_path, 0), _job(tmp_path, 1))
    executor = _RecordingExecutor(
        [
            _failed(KeyboardInterrupt()),
            _completed(parallel_image_jobs._execute_image_job(jobs[1])),
        ]
    )
    monkeypatch.setattr(
        parallel_image_pool,
        "_create_executor",
        lambda _workers, _registry: executor,
        raising=False,
    )

    # When / Then
    with pytest.raises(KeyboardInterrupt):
        execute_image_jobs(jobs, 2)
    assert executor.shutdown_calls == [(False, True)]


def test_animation_over_memory_budget_is_rejected_before_decode(tmp_path: Path) -> None:
    # Given
    job = _job(tmp_path)
    animation = ImageJob(
        job.index,
        job.source,
        job.destination,
        job.stage,
        job.format_name,
        job.pixel_count,
        frame_count=3,
        retains_animation=True,
    )
    estimate = (
        job.pixel_count * 3 * ESTIMATED_BYTES_PER_PIXEL
        + 3 * ESTIMATED_FRAME_OVERHEAD_BYTES
    )

    # When
    result = execute_image_jobs((animation,), 1, memory_budget_bytes=estimate - 1)

    # Then
    assert isinstance(result.results[0], ImageJobFailure)
    assert "memory budget" in result.results[0].reason
    assert not animation.stage.exists()


def test_metadata_disabled_strips_profiles_and_writes_resolution(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "source.png"
    exif = Image.Exif()
    exif[315] = "metadata fixture"
    Image.new("RGB", (8, 6), "green").save(
        source,
        dpi=(96, 96),
        icc_profile=b"test-profile",
        exif=exif.tobytes(),
    )
    job = ImageJob(
        0,
        source,
        tmp_path / "output.png",
        tmp_path / "stage.png",
        "PNG",
        48,
        resolution=144,
        preserve_metadata=False,
    )

    # When
    result = execute_image_jobs((job,), 1)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    with Image.open(job.stage) as output:
        assert "icc_profile" not in output.info
        assert "exif" not in output.info
        assert output.info["dpi"] == pytest.approx((144, 144), abs=0.1)


def test_malformed_exif_returns_job_failure_without_publishing(tmp_path: Path) -> None:
    source = tmp_path / "malformed.png"
    Image.new("RGB", (8, 6), "green").save(source, exif=b"Exif\x00\x00test")
    destination = tmp_path / "output.png"
    destination.write_bytes(b"previous output")
    job = ImageJob(0, source, destination, tmp_path / "stage.png", "PNG", 48)

    result = execute_image_jobs((job,), 1)

    assert isinstance(result.results[0], ImageJobFailure)
    assert "TIFF" in result.results[0].reason
    assert destination.read_bytes() == b"previous output"
    assert not job.stage.exists()
