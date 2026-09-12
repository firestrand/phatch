# Phatch - Photo Batch Processor
# Copyright (C) 2007-2008 www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
# Phatch recommends SPE (http://pythonide.stani.be) for editing python files.

# Follows PEP8

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from PIL import Image

from phatch.lib import openImage
from phatch.lib.system import ensure_path

from . import api
from .config import USER_PREVIEW_PATH
from .execution_types import ExecutionIssue


class PreviewRegistry(Protocol):
    def labels(self) -> tuple[str, ...]: ...

    def create(self, label: str) -> object | ExecutionIssue: ...


@dataclass(frozen=True, slots=True)
class BoundPreviewAction:
    label: str
    initialize: Callable[[], object]
    render: Callable[[Image.Image], object]


def _bind_preview_action(action: object) -> BoundPreviewAction:
    label = getattr(action, "label", None)
    initialize = getattr(action, "init", None)
    render = getattr(action, "apply_pil", None)
    if not isinstance(label, str) or not callable(initialize) or not callable(render):
        raise TypeError("Preview actions require label, init, and apply_pil")
    return BoundPreviewAction(label, initialize, render)


def generate(
    source: str,
    registry: PreviewRegistry,
    size: tuple[int, int] = (48, 48),
    path: str = USER_PREVIEW_PATH,
    force: bool = True,
) -> None:
    source_image = openImage.open(source)
    if source_image is None:
        raise OSError(f"Could not open preview source: {source}")
    source_image.thumbnail(size, Image.Resampling.LANCZOS)
    ensure_path(path)
    for label in registry.labels():
        created = registry.create(label)
        if isinstance(created, ExecutionIssue):
            raise RuntimeError(created.message)
        action = _bind_preview_action(created)
        filename = os.path.join(path, action.label + ".png")
        if os.path.exists(filename) and not force:
            continue
        action.initialize()
        result = action.render(source_image.copy())
        if not isinstance(result, Image.Image):
            raise TypeError("Preview action must return an image")
        result.thumbnail(size, Image.Resampling.LANCZOS)
        result.save(filename)


def main() -> None:
    action_registry = api.init()
    generate(
        "/home/stani/sync/python/phatch/icons/lenna/lenna_new.png", action_registry
    )


if __name__ == "__main__":
    main()
