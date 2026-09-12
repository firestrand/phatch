import io
import json
from pathlib import Path

import pytest
from PIL import Image

from phatch.services.automation_cli import run_automation_cli
from phatch.services.parallel_image_jobs import ImageJobFailure, execute_image_jobs
from phatch.services.parallel_save import build_image_jobs
from phatch.services.parallel_save_spec import SaveJobSpec
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import ExitCode


def _write_save_action(path: Path, output: Path, extension: str, **fields: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "parallel Save regression",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": extension,
                            "metadata": "no",
                            "resolution": "72",
                            "tiff_compression": "none",
                            **fields,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("format_name", "extension"), [("GIF", "gif"), ("WEBP", "webp"), ("TIFF", "tiff")]
)
def test_animation_frames_match_with_one_and_two_workers(
    tmp_path: Path, format_name: str, extension: str
) -> None:
    # Given
    source = tmp_path / f"source.{extension}"
    first = Image.new("RGB", (24, 16), "red")
    second = Image.new("RGB", (24, 16), "blue")
    first.save(
        source,
        format=format_name,
        save_all=True,
        append_images=[second],
        duration=[30, 40],
        loop=0,
    )

    frame_counts = []
    for workers in (1, 2):
        output = tmp_path / f"output-{workers}"
        action_list = tmp_path / f"save-{workers}.phatch"
        _write_save_action(action_list, output, extension)

        # When
        status = run_automation_cli(
            (
                "--max-workers",
                str(workers),
                "--report-format=json",
                str(action_list),
                str(source),
            ),
            io.StringIO(),
            io.StringIO(),
        )

        # Then
        assert status == ExitCode.SUCCESS
        with Image.open(output / source.name) as saved:
            frame_counts.append(int(getattr(saved, "n_frames", 1)))
    assert frame_counts == [2, 2]


def test_mixed_dimension_tiff_is_rejected_by_decoded_memory_budget(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "mixed.tiff"
    Image.new("RGB", (8, 8), "red").save(
        source,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (2048, 2048), "blue")],
        compression="raw",
    )
    destination = tmp_path / "output.tiff"
    preflight = PreflightResult((source,), (destination,), (), (), (), (), 1)
    spec = SaveJobSpec(85, False, "none", 72, False)
    jobs = build_image_jobs(spec, preflight)

    # When
    result = execute_image_jobs(jobs, 1, memory_budget_bytes=1024 * 1024)

    # Then
    assert isinstance(result.results[0], ImageJobFailure)
    assert "memory budget" in result.results[0].reason
    assert not jobs[0].stage.exists()


def test_worker_revalidates_retained_frames_before_decode(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "changed.tiff"
    first = Image.new("RGB", (8, 8), "red")
    first.save(
        source,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (8, 8), "blue")],
    )
    destination = tmp_path / "output.tiff"
    preflight = PreflightResult((source,), (destination,), (), (), (), (), 1)
    jobs = build_image_jobs(SaveJobSpec(85, False, "none", 72, False), preflight)
    first.save(
        source,
        format="TIFF",
        save_all=True,
        append_images=[Image.new("RGB", (512, 512), "blue")],
    )

    # When
    result = execute_image_jobs(jobs, 1, memory_budget_bytes=1024 * 1024)

    # Then
    assert isinstance(result.results[0], ImageJobFailure)
    assert "memory budget" in result.results[0].reason
    assert not jobs[0].stage.exists()


def test_legacy_jpeg_target_size_produces_bounded_file(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "noise.png"
    Image.effect_noise((1024, 1024), 64).convert("RGB").save(source)
    output = tmp_path / "output"
    action_list = tmp_path / "jpeg-target.phatch"
    _write_save_action(
        action_list,
        output,
        "jpg",
        jpeg_quality="95",
        jpeg_size_maximum="100 kb",
        jpeg_size_tolerance="4 kb",
    )

    # When
    status = run_automation_cli(
        (
            "--max-workers",
            "2",
            "--report-format=json",
            str(action_list),
            str(source),
        ),
        io.StringIO(),
        io.StringIO(),
    )

    # Then
    destination = output / "noise.jpg"
    assert status == ExitCode.SUCCESS
    assert destination.is_file()
    assert 96 * 1024 <= destination.stat().st_size <= 104 * 1024
