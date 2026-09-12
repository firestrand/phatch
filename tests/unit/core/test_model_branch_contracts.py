from types import SimpleNamespace
from unittest.mock import MagicMock

from phatch.core import models


class OffsetAction(models.OffsetMixin, models.Action):
    def interface(self, fields):
        models.OffsetMixin.interface(self, fields)


class LosslessAction(models.LosslessSaveMixin, models.Action):
    def interface(self, fields):
        return None


class StampAction(models.StampMixin, models.Action):
    def interface(self, fields):
        return None


def test_action_is_done_handles_missing_invalid_and_valid_outputs(monkeypatch, tmp_path):
    action = models.Action()
    photo = SimpleNamespace(info={})
    monkeypatch.setattr(action, "is_done_info", lambda _info: (_ for _ in ()).throw(KeyError("missing")), raising=False)
    assert action.is_done(photo) is False
    missing = tmp_path / "missing.png"
    monkeypatch.setattr(action, "is_done_info", lambda _info: (tmp_path, missing, "png"), raising=False)
    assert action.is_done(photo) is False
    missing.touch()
    monkeypatch.setattr(models.openImage, "verify_image", lambda *_args: True)
    assert action.is_done(photo) is True


def test_ensure_path_falls_back_to_desktop_after_creation_error(monkeypatch, tmp_path):
    action = models.Action()
    photo = SimpleNamespace(log=lambda message: logs.append(message))
    logs = []
    monkeypatch.setattr(models, "DESKTOP_FOLDER", str(tmp_path / "desktop"))
    ensure_path = MagicMock(side_effect=[OSError("denied"), None])
    monkeypatch.setattr(action, "ensure_path", ensure_path)

    result = action.ensure_path_or_desktop("blocked", photo, "blocked/image.jpg")

    assert result == str(tmp_path / "desktop" / "image.jpg")
    assert len(logs) == 2


def test_ensure_path_can_be_forced_to_desktop(monkeypatch, tmp_path):
    action = models.Action()
    monkeypatch.setattr(models, "DESKTOP_FOLDER", str(tmp_path))
    monkeypatch.setattr(action, "ensure_path", lambda _folder: None)

    result = action.ensure_path_or_desktop("ignored", SimpleNamespace(), "folder/image.jpg", desktop=True)

    assert result == str(tmp_path / "image.jpg")


def test_blender_fields_build_paths_and_user_option(monkeypatch):
    field = models.Action.BlenderRotationField("default")
    field.selected_object = "Sphere"
    monkeypatch.setattr(models, "files_dictionary", lambda **_kwargs: {})

    field.init_dictionary()

    assert field.get_path().endswith("preview/rotation/sphere")
    assert field.dictionary["User"].endswith("user.png")


def test_perspective_field_initializes_dictionary(monkeypatch):
    monkeypatch.setattr(models, "files_dictionary", lambda **kwargs: {"paths": kwargs["paths"]})
    field = models.Action.PerspectiveField("Left")

    field.init_dictionary()

    assert field.dictionary["paths"] == [models.PATHS["PHATCH_PERSPECTIVE_PATH"]]


def test_offset_relevant_fields_cover_custom_corner_and_center(monkeypatch):
    action = OffsetAction()
    monkeypatch.setattr(action, "get_field_string", lambda _label: action.CUSTOM)
    assert "Horizontal Offset" in action.get_relevant_field_labels()
    monkeypatch.setattr(action, "get_field_string", lambda _label: action.POSITION[1])
    assert action.get_relevant_field_labels()[-1] == "Offset"
    monkeypatch.setattr(action, "get_field_string", lambda _label: action.CENTER)
    assert action.get_relevant_field_labels() == ["Orientation", "Position"]


def test_offset_values_translate_center_and_corners(monkeypatch):
    action = OffsetAction()
    written = {}
    monkeypatch.setattr(action, "set_field_as_string", lambda label, value: written.__setitem__(label, value))
    monkeypatch.setattr(models.Action, "values", lambda self, info, pixel_fields=None, exclude=None: {"pixels": pixel_fields, "exclude": exclude})
    selections = iter([action.CENTER, action.POSITION[1], "5%", action.POSITION[4], "5%", action.CUSTOM])
    monkeypatch.setattr(action, "get_field_string", lambda _label: next(selections))

    center = action.values({"size": (100, 80)})
    action.values({"size": (100, 80)})
    action.values({"size": (100, 80)})
    custom = action.values({"size": (100, 80)})

    assert center["pixels"] == {"Horizontal Offset": 100, "Vertical Offset": 80}
    assert custom["exclude"] == ["Position", "Offset"]
    assert written["Horizontal Justification"] == action.RIGHT


def test_stamp_relevant_fields_include_offsets_only_for_offset_method(monkeypatch):
    action = StampAction()
    monkeypatch.setattr(action, "get_field_string", lambda label: action.METHODS[0] if label == "Method" else action.CENTER)

    labels = action.get_relevant_field_labels()

    assert "Position" in labels


def test_lossless_save_helpers(monkeypatch, tmp_path):
    action = LosslessAction()
    photo = SimpleNamespace(append_to_report=lambda filename: reports.append(filename))
    reports = []
    values = {"File Name": "image", "In": str(tmp_path)}
    monkeypatch.setattr(action, "get_field", lambda label, _info=None: values[label])
    monkeypatch.setattr(action, "ensure_path_or_desktop", lambda _folder, _photo, filename: filename)

    filename = action.get_lossless_filename(photo, {"type": "jpg"})

    assert filename.endswith("image.jpg")
    assert reports == []
    assert action.is_done(photo) is False
    assert action.is_overwrite_existing_images_forced() is True


def test_crop_fields_and_values_cover_default_and_explicit_action(monkeypatch):
    crop = models.CropMixin()
    all_action = SimpleNamespace(get_field_string=lambda _label: "All")
    custom_action = SimpleNamespace(get_field_string=lambda _label: "Custom")
    auto_action = SimpleNamespace(get_field_string=lambda _label: "Auto")
    assert crop.get_relevant_field_labels(all_action) == ["Mode", "All"]
    assert "Top" in crop.get_relevant_field_labels(custom_action)
    assert crop.get_relevant_field_labels(auto_action) == ["Mode"]
    monkeypatch.setattr(models.Action, "values", lambda self, info, pixel_fields=None, exclude=None: pixel_fields)
    action = models.Action()

    values = crop.values({"size": (100, 80)}, action=action)

    assert values["Left"] == 100
    assert values["Top"] == 80
