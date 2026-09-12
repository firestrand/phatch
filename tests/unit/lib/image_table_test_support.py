from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest
from PIL import Image

from phatch.lib import imageTable


def save_image(
    path: Path,
    *,
    size: tuple[int, int] = (300, 100),
    color: tuple[int, int, int] = (11, 22, 33),
) -> Path:
    Image.new("RGB", size, color).save(path)
    return path


def initialized_table() -> imageTable.Table:
    table = imageTable.Table()
    table.set_tag(imageTable.ALL)
    table.set_filter("")
    return table


class FakeMetadataImage:
    values: ClassVar[dict[str, dict[str, str]]] = {}
    failing_paths: ClassVar[set[str]] = set()

    def __init__(self, filename: str) -> None:
        with Image.open(filename) as source:
            source.verify()
        self.filename = filename
        self.values.setdefault(filename, {})

    def readMetadata(self) -> None:
        if self.filename in self.failing_paths:
            raise OSError("metadata unavailable")

    def writeMetadata(self) -> None:
        return None

    def __setitem__(self, key: str, value: str) -> None:
        self.values[self.filename][key] = value

    def __delitem__(self, key: str) -> None:
        del self.values[self.filename][key]


def install_metadata_writer(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeMetadataImage.values = {}
    FakeMetadataImage.failing_paths = set()
    monkeypatch.setattr(
        imageTable,
        "pyexiv2",
        SimpleNamespace(Image=FakeMetadataImage),
    )
