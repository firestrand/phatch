from types import SimpleNamespace
from unittest.mock import MagicMock

from PIL import Image

from phatch.actions import (
    background,
    color_to_alpha,
    common,
    fit,
    grid,
    perspective,
    round as round_action,
    scale,
    tamogen,
    text,
    time_shift,
    transpose,
)


def test_background_image_fields_are_relevant(monkeypatch):
    action = background.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: background.FILL_CHOICES[1])

    labels = action.get_relevant_field_labels()

    assert "Mark" in labels


def test_background_unknown_fill_has_no_extra_fields(monkeypatch):
    action = background.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: "unknown")

    result = background.background(Image.new("RGBA", (2, 2), (0, 0, 0, 0)), "unknown")

    assert result is None
    assert action.get_relevant_field_labels() == ["Fill"]


def test_color_to_alpha_samples_each_remaining_corner():
    image = Image.new("RGBA", (2, 2), "white")

    results = [color_to_alpha.color_to_alpha(image, select_color_by=option) for option in color_to_alpha.OPTIONS[2:]]

    assert all(result.mode == "RGBA" for result in results)


def test_common_blends_only_partial_amount():
    image = Image.new("RGB", (3, 3), "white")

    partial = common.common(image, 3, 50)
    full = common.common(image, 3, 100)

    assert partial.size == full.size == image.size


def test_fit_automatic_downscale_uses_antialias(monkeypatch):
    action = fit.Action()
    values = {
        "Resolution": 72,
        "Resample Image": "AUTOMATIC",
        "Align Horizontal": 50,
        "Align Vertical": 50,
        "Bleed": 0,
    }
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_size", lambda label, *_args: 5 if label == "Canvas Width" else 4)

    result = action.values({"dpi": 72, "size": (10, 8)})

    assert result["method"] == Image.Resampling.LANCZOS


def test_fit_explicit_resampling_method(monkeypatch):
    action = fit.Action()
    values = {"Resolution": 72, "Resample Image": "BICUBIC", "Align Horizontal": 50, "Align Vertical": 50, "Bleed": 0}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_size", lambda *_args: 20)

    result = action.values({"dpi": 72, "size": (10, 10)})

    assert result["method"] == Image.Resampling.BICUBIC


def test_grid_palette_transparency_and_palette_fallback(monkeypatch):
    transparent = Image.new("P", (2, 2))
    transparent.info["transparency"] = 0
    transparent_result = grid.make_grid(transparent, (2, 1), scale=False)
    fallback = Image.new("P", (2, 2))
    monkeypatch.setattr(grid.imtools, "fit_color_in_palette", lambda *_args: (-1, None))

    fallback_result = grid.make_grid(fallback, (2, 1), line_opacity=255, scale=False)

    assert transparent_result.mode == "P"
    assert fallback_result.mode != "P"


def test_grid_palette_translucent_lines_become_rgba():
    image = Image.new("P", (2, 2))

    result = grid.make_grid(image, (2, 1), line_opacity=128, scale=False)

    assert result.mode == "RGBA"


def test_grid_relevant_fields_accept_blank_widths(monkeypatch):
    action = grid.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: "")

    labels = action.get_relevant_field_labels()

    assert "Line Color" not in labels


def test_perspective_zero_scale_and_user_projection(monkeypatch):
    image = Image.new("RGB", (4, 4), "white")
    action = perspective.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: perspective.OPTIONS[-1])

    result = perspective.perspective(image, 0, 0, 0, 0, 0, 0, 0, 0, "#000000", 100, Image.Resampling.BICUBIC, False, "NONE")

    assert result.size == image.size
    assert action.get_relevant_field_labels()[-len(perspective.FIELDS):] == perspective.FIELDS


def test_round_cross_cache_and_corner_field_modes(monkeypatch):
    cache = {}
    first = round_action.create_rounded_rectangle((10, 10), cache, 2, pos=round_action.CROSS_POS)
    second = round_action.create_rounded_rectangle((10, 10), cache, 2, pos=round_action.CROSS_POS)
    action = round_action.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: "true")
    same_labels = action.get_relevant_field_labels()
    monkeypatch.setattr(action, "get_field_string", lambda _label: "false")
    separate_labels = action.get_relevant_field_labels()

    assert first is second
    assert "Method" in same_labels
    assert "Top Left Corner" in separate_labels


def test_scale_automatic_downscale_and_unchanged_size(monkeypatch):
    action = scale.Action()
    photo = SimpleNamespace(info={"dpi": 72, "size": (10, 10)}, resize=MagicMock())
    values = {"Resolution": 72, "Scale Down Only": False, "Constrain Proportions": True, "Resample Image": "AUTOMATIC"}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_size", lambda *_args: 5)
    action.apply(photo, None, {})
    monkeypatch.setattr(action, "get_field_size", lambda *_args: 10)

    action.apply(photo, None, {})

    photo.resize.assert_called_once()


def test_scale_automatic_upscale_without_proportions(monkeypatch):
    action = scale.Action()
    photo = SimpleNamespace(info={"dpi": 72, "size": (10, 10)}, resize=MagicMock())
    values = {"Resolution": 72, "Scale Down Only": False, "Constrain Proportions": False, "Resample Image": "AUTOMATIC"}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_size", lambda *_args: 20)

    action.apply(photo, None, {})

    photo.resize.assert_called_once_with((20, 20), Image.Resampling.BICUBIC)


def test_tamogen_transparency_and_folder_fields(monkeypatch):
    image = Image.new("RGBA", (2, 2), (0, 0, 0, 0))
    monkeypatch.setattr(tamogen._tamogen, "mosaic", lambda image, *_args: image)
    action = tamogen.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: tamogen.FOLDER)

    result = tamogen.mosaic(image, tamogen.FOLDER)

    assert result.mode == "RGBA"
    assert "Fill Folder" in action.get_relevant_field_labels()


def test_tamogen_unknown_selection_has_only_shared_fields(monkeypatch):
    action = tamogen.Action()
    monkeypatch.setattr(action, "get_field_string", lambda _label: "unknown")

    labels = action.get_relevant_field_labels()

    assert "Fill Image" not in labels
    assert "Fill Folder" not in labels


def test_transpose_action_applies_non_orientation_method(monkeypatch):
    action = transpose.Action()
    layer = SimpleNamespace(image=Image.new("RGB", (2, 3)))
    photo = SimpleNamespace(info={}, get_layer=lambda: layer)
    values = {"Method": "ROTATE_90", "Amount": 100}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])

    result = action.apply(photo, None, {})

    assert result is photo
    assert layer.image.size == (3, 2)


def test_time_shift_uses_component_date_and_relevant_exif_field(monkeypatch):
    action = time_shift.Action()
    info = {"year": 2020, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}
    photo = SimpleNamespace(info=info)
    values = {"Change": time_shift.OPTIONS[1], "Use exif datetime": False, "Seconds": 0, "Minutes": 0, "Hours": 0, "Days": 0, "Months": 0, "Years": 0}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_string", lambda _label: time_shift.OPTIONS[2])

    result = action.apply(photo, None, {})

    assert result is photo
    assert "Use exif datetime" in action.get_relevant_field_labels()


def test_time_shift_metadata_only_does_not_modify_file_date(monkeypatch):
    action = time_shift.Action()
    info = {"year": 2020, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}
    photo = SimpleNamespace(info=info)
    values = {"Change": time_shift.OPTIONS[0], "Use exif datetime": False, "Seconds": 0, "Minutes": 0, "Hours": 0, "Days": 0, "Months": 0, "Years": 0}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "get_field_string", lambda _label: time_shift.OPTIONS[0])

    action.apply(photo, None, {})

    assert not hasattr(photo, "modify_date")
    assert "Use exif datetime" not in action.get_relevant_field_labels()
