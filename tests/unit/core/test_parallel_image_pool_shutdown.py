from concurrent.futures import Future
from pathlib import Path

from phatch.services import parallel_image_pool, parallel_worker_bootstrap
from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobFailure,
    ImageJobResult,
    ImageJobSuccess,
)


def _job(tmp_path: Path, index: int) -> ImageJob:
    return ImageJob(
        index,
        tmp_path / f"source-{index}.png",
        tmp_path / f"output-{index}.png",
        tmp_path / f"stage-{index}.png",
        "PNG",
        1,
    )


def test_spawn_bootstrap_imports_as_package_module() -> None:
    assert parallel_worker_bootstrap.__name__ == (
        "phatch.services.parallel_worker_bootstrap"
    )


def test_finished_results_skips_pending_future(tmp_path: Path) -> None:
    # Given
    pending: Future[ImageJobResult] = Future()

    # When
    results = parallel_image_pool._finished_results({pending: _job(tmp_path, 0)})

    # Then
    assert results == ()


def test_finished_results_converts_cancelled_future(tmp_path: Path) -> None:
    # Given
    cancelled: Future[ImageJobResult] = Future()
    cancelled.cancel()

    # When
    results = parallel_image_pool._finished_results({cancelled: _job(tmp_path, 0)})

    # Then
    assert len(results) == 1
    assert isinstance(results[0], ImageJobFailure)
    assert results[0].reason == "image worker failed: "
    assert results[0].worker_pid == 0


def test_finished_results_returns_successful_future(tmp_path: Path) -> None:
    job = _job(tmp_path, 0)
    success: Future[ImageJobResult] = Future()
    expected = ImageJobSuccess(
        0, job.source, job.destination, job.stage, 1, 1, "RGB", "PNG", 123
    )
    success.set_result(expected)

    assert parallel_image_pool._finished_results({success: job}) == (expected,)


def test_finished_results_converts_failed_future(tmp_path: Path) -> None:
    job = _job(tmp_path, 0)
    failed: Future[ImageJobResult] = Future()
    failed.set_exception(RuntimeError("worker failed"))

    results = parallel_image_pool._finished_results({failed: job})

    assert len(results) == 1
    assert isinstance(results[0], ImageJobFailure)
    assert results[0].reason == "image worker failed: worker failed"
