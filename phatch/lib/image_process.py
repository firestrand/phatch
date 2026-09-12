from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from phatch.lib import imtools
from phatch.lib.process import Command, ProcessRunner


@dataclass(frozen=True, slots=True)
class ImageProcessPaths:
    root: Path
    input: Path
    output: Path


CommandBuilder = Callable[[ImageProcessPaths], Command]


def run_image_process(
    image: Image.Image,
    runner: ProcessRunner,
    command_builder: CommandBuilder,
    *,
    input_suffix: str = ".tif",
    output_relative: Path = Path("output.png"),
    input_mode: str | None = None,
) -> Image.Image:
    with TemporaryDirectory(prefix="phatch-image-process-") as directory:
        root = Path(directory)
        paths = ImageProcessPaths(
            root=root,
            input=root / f"input{input_suffix}",
            output=root / output_relative,
        )
        paths.output.parent.mkdir(parents=True, exist_ok=True)
        prepared = image if input_mode is None else imtools.convert(image, input_mode)
        imtools.save_safely(prepared, paths.input)
        runner.run(command_builder(paths))
        if not paths.output.is_file():
            raise FileNotFoundError(paths.output)
        with Image.open(paths.output) as output:
            output.load()
            return output.copy()
