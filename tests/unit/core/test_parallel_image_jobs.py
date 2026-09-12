from pathlib import Path

from PIL import Image

from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobFailure,
    ImageJobSuccess,
    _execute_image_job,
    execute_image_jobs,
)


def _jobs(tmp_path: Path, count: int = 3) -> tuple[ImageJob, ...]:
    jobs = []
    for index in range(count):
        source = tmp_path / f"source-{index}.png"
        Image.new("RGB", (32, 24), (index, 10, 20)).save(source)
        jobs.append(
            ImageJob(
                index=index,
                source=source,
                destination=tmp_path / f"output-{index}.png",
                stage=tmp_path / f"stage-{index}.png",
                format_name="PNG",
                pixel_count=32 * 24,
            )
        )
    return tuple(jobs)


def test_worker_counts_preserve_order_and_logical_results(tmp_path: Path) -> None:
    # Given
    jobs = _jobs(tmp_path)

    # When
    serial = execute_image_jobs(jobs, max_workers=1)
    for job in jobs:
        job.stage.unlink()
    parallel = execute_image_jobs(jobs, max_workers=2)

    # Then
    assert [result.index for result in serial.results] == [0, 1, 2]
    assert [result.index for result in parallel.results] == [0, 1, 2]
    assert all(isinstance(result, ImageJobSuccess) for result in parallel.results)
    assert len(parallel.worker_pids) >= 1
    assert parallel.coordinator_pid not in parallel.worker_pids


def test_worker_failure_does_not_discard_other_results(tmp_path: Path) -> None:
    # Given
    jobs = list(_jobs(tmp_path, 2))
    jobs[1].source.write_bytes(b"not an image")

    # When
    result = execute_image_jobs(tuple(jobs), max_workers=2)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    assert isinstance(result.results[1], ImageJobFailure)
    assert jobs[0].stage.is_file()
    assert not jobs[1].stage.exists()


def test_worker_entrypoint_returns_failure_for_invalid_image(tmp_path: Path) -> None:
    job = _jobs(tmp_path, 1)[0]
    job.source.write_bytes(b"not an image")

    result = _execute_image_job(job)

    assert isinstance(result, ImageJobFailure)
    assert not job.stage.exists()


def test_worker_entrypoint_preserves_requested_metadata(tmp_path: Path) -> None:
    job = _jobs(tmp_path, 1)[0]
    Image.new("RGB", (32, 24), "navy").save(
        job.source,
        icc_profile=b"test-profile",
        exif=b"Exif\x00\x00test",
    )
    preserving = ImageJob(
        job.index,
        job.source,
        job.destination,
        job.stage,
        job.format_name,
        job.pixel_count,
        preserve_metadata=True,
    )

    result = _execute_image_job(preserving)

    assert isinstance(result, ImageJobSuccess)
    with Image.open(job.stage) as output:
        assert output.info["icc_profile"] == b"test-profile"
        assert output.info["exif"] == b"Exif\x00\x00test"


def test_memory_guard_rejects_job_before_decode(tmp_path: Path) -> None:
    # Given
    job = _jobs(tmp_path, 1)[0]
    guarded = ImageJob(
        index=job.index,
        source=job.source,
        destination=job.destination,
        stage=job.stage,
        format_name=job.format_name,
        pixel_count=job.pixel_count,
        max_pixels=job.pixel_count - 1,
    )

    # When
    result = execute_image_jobs((guarded,), max_workers=1)

    # Then
    assert isinstance(result.results[0], ImageJobFailure)
    assert "pixel limit" in result.results[0].reason
    assert not guarded.stage.exists()


def test_memory_guard_checks_decoded_dimensions_not_only_job_estimate(
    tmp_path: Path,
) -> None:
    # Given
    job = _jobs(tmp_path, 1)[0]
    guarded = ImageJob(
        job.index,
        job.source,
        job.destination,
        job.stage,
        job.format_name,
        1,
        max_pixels=100,
    )

    # When
    result = execute_image_jobs((guarded,), 1)

    # Then
    assert isinstance(result.results[0], ImageJobFailure)
    assert not guarded.stage.exists()


def test_animation_and_codec_options_are_applied_in_real_worker(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "animated.gif"
    first = Image.new("RGB", (10, 8), "red")
    second = Image.new("RGB", (10, 8), "blue")
    first.save(
        source,
        save_all=True,
        append_images=[second],
        duration=[30, 70],
        loop=1,
    )
    job = ImageJob(
        0,
        source,
        tmp_path / "output.gif",
        tmp_path / "stage.gif",
        "GIF",
        80,
        frame_count=2,
        retains_animation=True,
    )

    # When
    result = execute_image_jobs((job,), 1)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    with Image.open(job.stage) as decoded:
        assert decoded.n_frames == 2
        assert decoded.info["loop"] == 1


def test_jpeg_worker_converts_alpha_and_applies_quality(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "alpha.png"
    Image.new("RGBA", (12, 9), (10, 20, 30, 40)).save(source)
    job = ImageJob(
        0,
        source,
        tmp_path / "output.jpg",
        tmp_path / "stage.jpg",
        "JPEG",
        108,
        quality=72,
    )

    # When
    result = execute_image_jobs((job,), 1)

    # Then
    assert isinstance(result.results[0], ImageJobSuccess)
    assert result.results[0].mode == "RGB"
