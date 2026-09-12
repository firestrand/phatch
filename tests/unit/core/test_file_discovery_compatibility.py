from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from phatch.core import api
from phatch.lib import metadata

MetadataSource = str | tuple[str, str]
MetadataValue = str | int


class InfoFileRecorder:
    __slots__ = ("calls", "type_override")

    def __init__(self, type_override: str | None = None) -> None:
        self.calls: list[MetadataSource] = []
        self.type_override = type_override

    def dump(self, source: MetadataSource) -> dict[str, MetadataValue]:
        self.calls.append(source)
        path = source[0] if isinstance(source, tuple) else source
        file_type = self.type_override or Path(path).suffix.lstrip(".")
        return {"path": path, "type": file_type, "marker": "preserved"}


def test_public_discovery_signatures_remain_legacy_compatible() -> None:
    assert tuple(inspect.signature(api.filter_image_infos).parameters) == (
        "folder",
        "extensions",
        "files",
        "root",
        "info_file",
    )
    assert tuple(inspect.signature(api.get_image_infos_from_folder).parameters) == (
        "folder",
        "info_file",
        "extensions",
        "recursive",
    )
    assert tuple(inspect.signature(api.get_image_infos).parameters) == (
        "paths",
        "info_file",
        "extensions",
        "recursive",
    )


def test_metadata_dump_keeps_direct_and_tuple_sources(tmp_path: Path) -> None:
    # Given
    explicit = tmp_path / "explicit.txt"
    folder = tmp_path / "folder"
    nested = folder / "photo.JPG"
    explicit.write_text("explicit", encoding="utf-8")
    folder.mkdir()
    nested.write_text("nested", encoding="utf-8")
    info_file = InfoFileRecorder()

    # When
    image_infos = api.get_image_infos(
        [str(explicit), str(folder)], info_file, ["jpg"], recursive=False
    )

    # Then
    assert info_file.calls == [str(explicit), (str(nested), str(folder))]
    assert [info["marker"] for info in image_infos] == ["preserved", "preserved"]
    assert image_infos[1]["folderindex"] == 0


def test_folder_filtering_remains_based_on_metadata_type(tmp_path: Path) -> None:
    # Given
    disguised = tmp_path / "photo.data"
    disguised.write_text("photo", encoding="utf-8")
    info_file = InfoFileRecorder(type_override="JPG")

    # When
    image_infos = api.filter_image_infos(
        str(tmp_path), ["jpg"], [disguised.name], str(tmp_path), info_file
    )

    # Then
    assert [info["path"] for info in image_infos] == [str(disguised)]
    assert info_file.calls == [(str(disguised), str(tmp_path))]


def test_recursive_metadata_preserves_root_subfolder_and_folder_indices(
    tmp_path: Path,
) -> None:
    # Given
    root = tmp_path / "source"
    first_folder = root / "first"
    second_folder = root / "second"
    first_folder.mkdir(parents=True)
    second_folder.mkdir()
    for path in (
        first_folder / "b.jpg",
        first_folder / "A.JPG",
        second_folder / "c.jpg",
    ):
        path.write_text("image", encoding="utf-8")
    info_file = metadata.InfoFile(vars=["path", "folder", "root", "subfolder", "type"])

    # When
    image_infos = api.get_image_infos_from_folder(
        str(root), info_file, ["jpg"], recursive=True
    )

    # Then
    by_path = {info["path"]: info for info in image_infos}
    assert [info["folderindex"] for info in image_infos] == [0, 1, 0]
    assert by_path[str(first_folder / "A.JPG")]["folder"] == str(root)
    assert by_path[str(first_folder / "A.JPG")]["root"] == str(root.parent)
    assert by_path[str(first_folder / "A.JPG")]["subfolder"] == "first"
    assert by_path[str(second_folder / "c.jpg")]["subfolder"] == "second"


def test_invalid_path_reports_exact_error_after_prior_enrichment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Given
    valid = tmp_path / "valid.jpg"
    invalid = tmp_path / "missing.jpg"
    valid.write_text("valid", encoding="utf-8")
    info_file = InfoFileRecorder()
    errors: list[str] = []
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    # When
    image_infos = api.get_image_infos(
        [str(valid), str(invalid)], info_file, ["jpg"], recursive=False
    )

    # Then
    assert image_infos == []
    assert info_file.calls == [str(valid)]
    assert errors == [f'Sorry, "{invalid}" is not a valid path.']
