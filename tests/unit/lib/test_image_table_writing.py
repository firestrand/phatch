from __future__ import annotations

from pathlib import Path

import pytest

from phatch.lib import imageTable
from tests.unit.lib.image_table_test_support import (
    FakeMetadataImage,
    initialized_table,
    install_metadata_writer,
    save_image,
)


def table_with_images(tmp_path: Path, amount: int = 2) -> imageTable.Table:
    table = initialized_table()
    for index in range(amount):
        path = save_image(tmp_path / f"image-{index}.png", size=(index + 2, 2))
        table.open_image(str(path), update=False)
    table.update()
    return table


def test_editability_requires_writer_images_and_supported_tag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    table = table_with_images(tmp_path, amount=1)
    key = "Exif_Image_Test"
    table._add_key(key)
    index = table.keys.index(key)

    monkeypatch.setattr(imageTable, "pyexiv2", None)
    assert not table.is_key_editable(key=key)
    assert not table.is_cell_editable(index, 0)

    install_metadata_writer(monkeypatch)
    assert table.is_key_editable(key=key)
    assert not table.is_key_editable(key="plain")
    assert not initialized_table().is_key_editable(key=key)
    assert table.is_cell_editable(index, 0)
    assert not table.is_cell_deletable(index, 0)


def test_add_key_writes_all_images_and_expands_table_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path)

    assert table.add_key("Exif_Image_Test", "value") == ""
    assert table.add_key("Exif_Image_Test", "value") == ""

    assert table.keys.count("Exif_Image_Test") == 1
    assert all(image.info["Exif_Image_Test"] == "value" for image in table.images)
    assert all(
        FakeMetadataImage.values[image.filename]["Exif.Image.Test"] == "value"
        for image in table.images
    )


def test_add_image_key_and_cell_mutations_target_one_real_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path)
    image = table.images[0]

    assert table.add_image_key(image, "Exif_Image_Test", "7") == ""
    row = table.keys.index("Exif_Image_Test")
    assert table.get_cell_value(row, 0) == "7"
    assert not table.is_cell_empty(row, 0)
    assert table.is_cell_deletable(row, 0)
    assert table.set_cell_value(row, 0, "7") is None

    assert table.set_cell_value(row, 0, "next") == ""
    assert table.get_cell_value(row, 0) == "next"
    FakeMetadataImage.values[image.filename]["Exif.Image.Test"] = "next"
    assert table.delete_cell(row, 0) == ""
    assert "Exif_Image_Test" not in image.info
    assert "Exif_Image_Test" not in table.keys


def test_set_key_value_skips_unchanged_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path)
    key = "Exif_Image_Test"
    table.images[0].info[key] = "same"

    assert table.set_key_value(key, "same") == ""

    assert key not in FakeMetadataImage.values.get(table.images[0].filename, {})
    assert FakeMetadataImage.values[table.images[1].filename]["Exif.Image.Test"] == (
        "same"
    )


def test_delete_keys_removes_present_values_and_derived_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path)
    key = "Exif_Image_Test"
    derived = f"{key}.year"
    table.keys = [key, derived, "plain"]
    table.key_amount = 2
    for image in table.images:
        image.info[key] = "old"
        image.info[derived] = 2026
        FakeMetadataImage.values.setdefault(image.filename, {})[
            "Exif.Image.Test"
        ] = "old"

    assert table.delete_keys(0) == ""

    assert key not in table.keys
    assert derived not in table.keys
    assert table.keys == ["plain"]
    assert table.key_amount == 1
    assert all(key not in image.info for image in table.images)


def test_delete_keys_with_no_present_values_is_a_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path, amount=1)
    table.keys = ["Exif_Image_Absent"]
    table.key_amount = 1

    assert table.delete_keys(0) == ""
    assert table.keys == ["Exif_Image_Absent"]


def test_set_key_label_validates_and_keeps_metadata_state_consistent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path, amount=1)
    old_key = "Exif_Image_Old"
    new_key = "Exif_Image_New"
    table.keys = [old_key]
    table.key_amount = 1
    table.images[0].info[old_key] = "kept"
    FakeMetadataImage.values.setdefault(table.images[0].filename, {})[
        "Exif.Image.Old"
    ] = "kept"

    assert "not valid" in table.set_key_label(0, "plain")
    assert table.keys == [old_key]
    assert table.images[0].info[old_key] == "kept"
    assert table.set_key_label(0, new_key) == ""

    assert new_key in table.keys
    assert old_key not in table.keys
    assert table.key_amount == len(table.keys)
    assert table.images[0].info[new_key] == "kept"
    assert old_key not in table.images[0].info
    assert FakeMetadataImage.values[table.images[0].filename] == {
        "Exif.Image.New": "kept"
    }


def test_write_failure_preserves_failed_image_and_updates_other_images(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path)
    key = "Exif_Image_Test"
    table.images[0].info[key] = "old"
    FakeMetadataImage.failing_paths.add(table.images[0].filename)

    log = table.set_key_value(key, "new")

    assert "metadata unavailable" in log
    assert table.images[0].info[key] == "old"
    assert table.images[1].info[key] == "new"
    assert FakeMetadataImage.values[table.images[1].filename]["Exif.Image.Test"] == "new"


def test_failed_rename_reports_error_and_preserves_original_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_metadata_writer(monkeypatch)
    table = table_with_images(tmp_path, amount=1)
    old_key = "Exif_Image_Old"
    table.keys = [old_key]
    table.key_amount = 1
    table.images[0].info[old_key] = "old"
    FakeMetadataImage.failing_paths.add(table.images[0].filename)

    log = table.set_key_label(0, "Exif_Image_New")

    assert "metadata unavailable" in log
    assert old_key in table.keys
    assert "Exif_Image_New" not in table.keys
    assert table.images[0].info[old_key] == "old"
    assert table.key_amount == len(table.keys)
