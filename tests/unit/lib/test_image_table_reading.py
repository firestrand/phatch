from __future__ import annotations

import os
from pathlib import Path

import pytest
from PIL import Image

from phatch.lib import imageTable
from tests.unit.lib.image_table_test_support import initialized_table, save_image


def test_table_image_reads_real_thumbnail_pixels_and_metadata(tmp_path: Path) -> None:
    source = save_image(tmp_path / "wide.png")

    table_image = imageTable.TableImage(str(source))

    assert table_image.label == "wide.png"
    assert table_image.thumb.mode == "RGB"
    assert table_image.thumb.size == (128, 43)
    assert table_image.thumb.getpixel((0, 0)) == (11, 22, 33)
    assert table_image.info["format"] == "PNG"
    assert table_image.info["mode"] == "RGB"
    assert table_image.info["size"] == (300, 100)
    assert table_image.info["size[0]"] == 300


def test_table_image_detects_rewrite_and_survives_missing_source(
    tmp_path: Path,
) -> None:
    source = save_image(tmp_path / "changing.png", size=(4, 3))
    table_image = imageTable.TableImage(str(source))
    original_time = table_image.time
    os.utime(source, (original_time + 2, original_time + 2))

    assert table_image.is_modified()
    assert table_image.update_if_modified()
    assert not table_image.update_if_modified()

    source.unlink()
    assert table_image.get_time() == table_image.time


def test_open_image_rejects_missing_path() -> None:
    table = initialized_table()

    with pytest.raises(OSError):
        table.open_image("missing.png")


def test_open_images_loads_files_and_folders_and_reports_invalid(
    tmp_path: Path,
) -> None:
    direct = save_image(tmp_path / "direct.png", size=(3, 2), color=(1, 2, 3))
    folder = tmp_path / "folder"
    folder.mkdir()
    nested = save_image(folder / "nested.png", size=(2, 3), color=(4, 5, 6))
    (folder / "broken.txt").write_text("not an image", encoding="utf-8")
    invalid = tmp_path / "absent"
    table = initialized_table()

    rejected = table.open_images([str(direct), str(folder), str(invalid)])

    assert rejected == [str(invalid)]
    assert table.get_image_amount() == 2
    assert {table.get_image_filename(0), table.get_image_filename(1)} == {
        str(direct),
        str(nested),
    }
    assert table.get_key_amount() > 0


def test_open_folder_and_delete_image_use_real_files(tmp_path: Path) -> None:
    folder = tmp_path / "images"
    folder.mkdir()
    first = save_image(folder / "one.png", size=(2, 2))
    second = save_image(folder / "two.png", size=(3, 3))
    table = initialized_table()

    assert table.open_folder(str(folder)) == []
    assert {table.get_image_filename(0), table.get_image_filename(1)} == {
        str(first),
        str(second),
    }

    table.delete_images(0)
    assert table.get_image_amount() == 1


def test_layout_transposes_dynamic_row_and_column_access(tmp_path: Path) -> None:
    source = save_image(tmp_path / "layout.png", size=(5, 4))
    table = initialized_table()
    table.open_image(str(source))
    key = table.get_key_label(0)

    assert table.get_row_amount() == table.get_key_amount()
    assert table.get_col_amount() == 1
    assert table.get_row_label(0) == key
    assert table.get_col_label(0) == "layout.png"
    assert table.get_cell_value(0, 0) == table.images[0].info[key]

    table.transpose()
    assert table.get_row_amount() == 1
    assert table.get_col_amount() == table.get_key_amount()
    assert table.get_row_label(0) == "layout.png"
    assert table.get_col_label(0) == key
    assert table.get_cell_value(0, 0) == table.images[0].info[key]


def test_layout_reports_unsupported_attribute_and_read_only_image_label(
    tmp_path: Path,
) -> None:
    table = initialized_table()
    table.open_image(str(save_image(tmp_path / "label.png", size=(2, 2))))

    assert not table.is_image_editable(table.images[0])
    attribute = "missing_operation"
    with pytest.raises(AttributeError, match="missing_operation"):
        getattr(table, attribute)
    with pytest.raises(Exception, match="Unable to change label"):
        table.set_image_label(0, "renamed")


def test_key_sorting_selection_and_filtering_cover_each_layout_branch() -> None:
    table = initialized_table()
    table.keys = [
        "Exif_Image.Make",
        "plain",
        "Exif_Image.Canon",
        "Iptc_Core_Title",
        "Exif_Photo_Model",
    ]
    table.key_amount = len(table.keys)

    assert table._sort_keys(table.keys) == [
        "Exif_Image.Make",
        "Exif_Photo_Model",
        "Iptc_Core_Title",
        "plain",
        "Exif_Image.Canon",
    ]

    table.set_tag(imageTable.SELECT)
    assert table.keys[: table.key_amount] == ["plain"]
    table.set_filter("PL")
    assert table.keys[: table.key_amount] == ["plain"]

    table.set_tag("Exif")
    assert table.keys[: table.key_amount] == [
        "Exif_Image.Make",
        "Exif_Photo_Model",
        "Exif_Image.Canon",
    ]
    table.set_tag(imageTable.ALL)
    assert table.key_amount == len(table.keys)


def test_actual_thumbnail_is_detached_from_source_file(tmp_path: Path) -> None:
    source = save_image(tmp_path / "detached.png", size=(8, 6), color=(7, 8, 9))
    table_image = imageTable.TableImage(str(source))
    source.unlink()

    output = tmp_path / "thumb.png"
    table_image.thumb.save(output)

    with Image.open(output) as thumb:
        assert thumb.mode == "RGB"
        assert thumb.size == (8, 6)
        assert thumb.getpixel((0, 0)) == (7, 8, 9)
