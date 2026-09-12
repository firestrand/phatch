from pathlib import Path

from phatch.core import api


class InfoFileFake:
    def dump(self, source):
        path = source[0] if isinstance(source, tuple) else source
        return {"path": str(path), "type": Path(path).suffix.lstrip(".")}


def test_explicit_files_bypass_extension_filtering(tmp_path):
    explicit = tmp_path / "notes.txt"
    explicit.write_text("not an image", encoding="utf-8")

    image_infos = api.get_image_infos(
        [str(explicit)], InfoFileFake(), ["jpg"], recursive=False
    )

    assert [info["path"] for info in image_infos] == [str(explicit)]


def test_directory_files_are_filtered_case_insensitively_and_sorted(tmp_path):
    for name in ("third.txt", "second.JPG", "first.jpg"):
        (tmp_path / name).write_text(name, encoding="utf-8")

    image_infos = api.get_image_infos_from_folder(
        str(tmp_path), InfoFileFake(), ["jpg"], recursive=False
    )

    assert [Path(info["path"]).name for info in image_infos] == [
        "first.jpg",
        "second.JPG",
    ]
    assert [info["folderindex"] for info in image_infos] == [0, 1]


def test_duplicate_explicit_paths_remain_in_discovery_result(tmp_path):
    explicit = tmp_path / "photo.jpg"
    explicit.write_bytes(b"photo")

    image_infos = api.get_image_infos(
        [str(explicit), str(explicit)], InfoFileFake(), ["jpg"], recursive=False
    )

    assert [info["path"] for info in image_infos] == [str(explicit), str(explicit)]


def test_any_invalid_path_empties_the_entire_discovery_result(tmp_path, monkeypatch):
    valid = tmp_path / "photo.jpg"
    invalid = tmp_path / "missing.jpg"
    valid.write_bytes(b"photo")
    errors = []
    monkeypatch.setattr(api.send, "frame_show_error", errors.append)

    image_infos = api.get_image_infos(
        [str(valid), str(invalid)], InfoFileFake(), ["jpg"], recursive=False
    )

    assert image_infos == []
    assert str(invalid) in errors[0]
