from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from tests.integration.test_installed_wheel_automation import InstalledPhatch

pytest_plugins = ("tests.integration.test_installed_wheel_automation",)


def _write_save_action(path: Path, output: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": 3,
                "description": "parallel orientation regression",
                "actions": [
                    {
                        "id": "save",
                        "fields": {
                            "in": str(output),
                            "file_name": "<filename>",
                            "as": "jpg",
                            "metadata": "no",
                            "resolution": "72",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_oriented_jpeg(path: Path, orientation: int) -> None:
    image = Image.new("RGB", (80, 40))
    image.paste((240, 20, 20), (0, 0, 40, 20))
    image.paste((20, 220, 20), (40, 0, 80, 20))
    image.paste((20, 20, 240), (0, 20, 40, 40))
    image.paste((235, 220, 20), (40, 20, 80, 40))
    exif = Image.Exif()
    exif[274] = orientation
    image.save(path, format="JPEG", quality=95, subsampling=0, exif=exif)


def _assert_color_close(actual: tuple[int, ...], expected: tuple[int, ...]) -> None:
    assert all(
        abs(channel - target) <= 35
        for channel, target in zip(actual, expected, strict=True)
    )


@pytest.mark.slow
@pytest.mark.parametrize(
    ("execution", "workers"), [("process", 1), ("process", 2), ("serial", 2)]
)
@pytest.mark.parametrize(
    ("orientation", "expected_size", "expected_corners"),
    [
        (
            2,
            (80, 40),
            ((20, 220, 20), (240, 20, 20), (235, 220, 20), (20, 20, 240)),
        ),
        (
            6,
            (40, 80),
            ((20, 20, 240), (240, 20, 20), (235, 220, 20), (20, 220, 20)),
        ),
    ],
)
def test_installed_parallel_save_applies_exif_orientation_before_stripping_metadata(
    installed_phatch: InstalledPhatch,
    execution: str,
    workers: int,
    orientation: int,
    expected_size: tuple[int, int],
    expected_corners: tuple[tuple[int, ...], ...],
) -> None:
    case_name = f"orientation-{orientation}-{execution}-{workers}"
    source = installed_phatch.work / f"{case_name}.jpg"
    output = installed_phatch.work / f"{case_name}-output"
    action_list = installed_phatch.work / f"{case_name}.phatch"
    _write_oriented_jpeg(source, orientation)
    _write_save_action(action_list, output)
    original_bytes = source.read_bytes()

    arguments = [
        "--verbose",
        "--max-workers",
        str(workers),
        "--report-format=json",
    ]
    if execution == "serial":
        arguments.extend(
            ("--resume", str(installed_phatch.work / f"{case_name}.jsonl"))
        )
    completed = installed_phatch.run(*arguments, str(action_list), str(source))

    assert completed.returncode == 0, completed.stderr
    assert source.read_bytes() == original_bytes
    with Image.open(source) as original:
        assert original.size == (80, 40)
        assert original.getexif()[274] == orientation
    with Image.open(output / source.name) as saved:
        assert saved.size == expected_size
        assert saved.getexif().get(274) is None
        width, height = saved.size
        corners = (
            saved.getpixel((5, 5)),
            saved.getpixel((width - 6, 5)),
            saved.getpixel((5, height - 6)),
            saved.getpixel((width - 6, height - 6)),
        )
        for actual, expected in zip(corners, expected_corners, strict=True):
            _assert_color_close(actual, expected)
    trace = next(
        line
        for line in completed.stderr.splitlines()
        if line.startswith("execution_mode")
    )
    if execution == "serial":
        assert trace.startswith("execution_mode=serial")
    else:
        assert trace.startswith("execution_mode=process")
        assert trace.partition("worker_pids=")[2]
