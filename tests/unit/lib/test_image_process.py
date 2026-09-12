from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, UnidentifiedImageError

from phatch.lib.image_process import ImageProcessPaths, run_image_process
from phatch.lib.process import Command, ProcessResult


class WritingRunner:
    def __init__(self, output: str = "valid") -> None:
        self.output = output
        self.commands: list[Command] = []

    def run(self, command: Command, *, cancelled=None) -> ProcessResult:
        self.commands.append(command)
        output = Path(command.argv[-1])
        if self.output == "valid":
            with Image.open(command.argv[-2]) as source:
                source.save(output, format="PNG")
        elif self.output == "corrupt":
            output.write_bytes(b"not an image")
        return ProcessResult(command, 0, "", "")


def build_copy_command(paths: ImageProcessPaths) -> Command:
    return Command(("fake-convert", str(paths.input), str(paths.output)))


def test_run_image_process_returns_detached_image_after_staging_cleanup() -> None:
    runner = WritingRunner()

    result = run_image_process(
        Image.new("RGBA", (3, 2), (1, 2, 3, 4)), runner, build_copy_command
    )

    assert result.mode == "RGBA"
    assert result.getpixel((0, 0)) == (1, 2, 3, 4)
    assert not Path(runner.commands[0].argv[-1]).exists()


def test_run_image_process_requires_expected_output() -> None:
    with pytest.raises(FileNotFoundError):
        run_image_process(
            Image.new("RGB", (1, 1)), WritingRunner("missing"), build_copy_command
        )


def test_run_image_process_rejects_corrupt_output() -> None:
    with pytest.raises(UnidentifiedImageError):
        run_image_process(
            Image.new("RGB", (1, 1)), WritingRunner("corrupt"), build_copy_command
        )


def test_run_image_process_supports_blender_frame_output() -> None:
    runner = WritingRunner()

    def build_frame_command(paths: ImageProcessPaths) -> Command:
        frame = paths.output.parent / "0001.png"
        return Command(("fake-blender", str(paths.input), str(frame)))

    result = run_image_process(
        Image.new("RGB", (2, 2), "red"),
        runner,
        build_frame_command,
        output_relative=Path("render/0001.png"),
    )

    assert result.size == (2, 2)
