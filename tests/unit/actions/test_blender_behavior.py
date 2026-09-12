from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import UnidentifiedImageError

from phatch.actions import _blender_action as action_module
from phatch.actions import blender
from phatch.lib.process import (
    Command,
    ProcessCancelledError,
    ProcessExitError,
    ProcessTimeoutError,
)

FAILURE_COMMAND = Command(("blender",))
IMAGE_PROCESS_FAILURES = (
    FileNotFoundError("missing output"),
    ProcessExitError(FAILURE_COMMAND, 2, "", "failed"),
    ProcessTimeoutError(FAILURE_COMMAND, 300.0),
    ProcessCancelledError(FAILURE_COMMAND),
    UnidentifiedImageError("corrupt output"),
)


class FakeAction:
    def __init__(self, strings=None, truths=None):
        self.strings = strings or {}
        self.truths = truths or {}
        self.dirty = []

    def __getattr__(self, name):
        if name.endswith("Field"):
            return lambda *args, **kwargs: (args, kwargs)
        raise AttributeError(name)

    def get_field_string(self, name):
        return self.strings[name]

    def is_field_true(self, name):
        return self.truths.get(name, False)

    def set_field_as_string_dirty(self, name, value):
        self.dirty.append((name, value))


def test_blender_option_interfaces_and_object_branches():
    fields = {}
    fake = FakeAction(
        {"Object": "Book", "Page Mapping": "Separate", "Left Page": "left.jpg"}
    )
    objects = blender.BlenderObjects()
    objects.interface(fake, fields)
    assert {
        "Cover Color",
        "Page Mapping",
        "Left Page",
        "Box Color",
        "Box Depth",
        "Lid Rotation",
    } <= set(fields)
    assert objects.get_selected_object(fake).name == "Book"
    with pytest.raises(LookupError):
        objects.get_selected_object(FakeAction({"Object": "Missing"}))
    book = blender.Book()
    assert book.get_relevant(fake)[-1] == "Left Page"
    assert book.get_relevant(FakeAction({"Page Mapping": "Wrap Both"})) == [
        "Cover Color",
        "Page Mapping",
    ]
    values = {"amount_of_input_images": 1, "image_size": ""}
    book.set_args(fake, values)
    assert values["input_image_2"] == "left.jpg"
    assert blender.Box().get_relevant(fake) == ["Box Color", "Box Depth"]
    assert blender.Cd().get_relevant(fake) == ["Lid Rotation"]
    base = blender.BlenderObject()
    assert base.name == "BlenderObject" and base.get_relevant(fake) == []
    base.interface(fake, fields)


def test_camera_floor_and_background_branches():
    fields = {}
    user = FakeAction(
        {"Camera": "User"}, {"Show Floor Options": True, "Use Floor": True}
    )
    camera = blender.Camera()
    floor = blender.Floor()
    background = blender.Background()
    camera.interface(user, fields)
    floor.interface(user, fields)
    background.interface(user, fields)
    assert "Camera Distance" in camera.get_relevant(user)
    preset = FakeAction({"Camera": "Hori -30 Vert 10"})
    assert camera.get_relevant(preset) == ["Camera"]
    values = {"camera": "/tmp/hori_-30_vert_10.png"}
    camera.set_args(user, values)
    assert values["camera_vertical_rotation"] == "10"
    camera.set_args(user, {"camera": "/tmp/user.png"})
    assert "Floor Opacity" in floor.get_relevant(user)
    assert floor.get_relevant(FakeAction(truths={"Show Floor Options": True})) == [
        "Show Floor Options",
        "Use Floor",
    ]
    assert floor.get_relevant(FakeAction()) == ["Show Floor Options"]
    for name, expected in (
        ("Color", "Background Color"),
        ("Transparent", "Auto Crop"),
        ("Gradient", "Gradient Top"),
    ):
        fake = FakeAction(
            {"Background": name}, {"Show Background Options": True, "Stars": True}
        )
        assert expected in background.get_relevant(fake)
    assert background.get_relevant(
        FakeAction(truths={"Transparent Background": True})
    ) == ["Transparent Background", "Auto Crop"]
    assert background.get_relevant(FakeAction()) == [
        "Transparent Background",
        "Show Background Options",
    ]
    values = {
        "background": "Color",
        "background_color": "red",
        "transparent_background": False,
    }
    background.set_args(user, values)
    assert values["gradient_top"] == "red" and values["alpha"] is False
    values = {
        "background": "Gradient",
        "transparent_background": True,
        "use_floor": True,
    }
    background.set_args(user, values)
    assert values["alpha"] is True and values["use_floor"] is False


def test_blender_action_init_interface_apply_and_command(monkeypatch):
    action = blender.Action()
    tools = SimpleNamespace(
        executable=Mock(return_value=Path("/blender")), runner=Mock()
    )
    action.init(tools)
    fields = {}
    action.interface(fields)
    assert "Render Width" in fields and "Camera" in fields
    values = {
        "render_width": 10,
        "render_height": 20,
        "image_size": "Fit Image",
        "box_color": "white",
        "box_depth": 3,
        "background": "Gradient",
        "transparent_background": False,
        "gradient_top": "black",
        "gradient_bottom": "white",
        "alpha": False,
        "stars": False,
        "stars_color": "white",
        "mist": False,
        "use_floor": True,
        "floor_color": "black",
        "floor_reflection": 1,
        "floor_opacity": 1,
        "camera": "/tmp/hori_0_vert_0.png",
        "camera_roll": 0,
        "camera_vertical_rotation": 0,
        "camera_horizontal_rotation": 0,
        "camera_lens_angle": 51,
        "camera_distance": 2,
    }
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: values.copy())
    monkeypatch.setattr(
        action,
        "get_field_string",
        lambda name: "Box" if name == "Object" else "Wrap Both",
    )
    monkeypatch.setattr(action, "get_field", lambda *args: False)
    result_image = object()

    def run(image, runner, command_builder, **kwargs):
        paths = action_module.ImageProcessPaths(
            Path("."), Path("input.bmp"), Path("render/0001.png")
        )
        assert command_builder(paths).argv[0] == "/blender"
        return result_image

    monkeypatch.setattr(action_module, "run_image_process", run)
    layer = SimpleNamespace(image=object())
    photo = SimpleNamespace(
        info={"size": (10, 20), "mode": "RGB"}, get_layer=lambda: layer
    )
    assert action.apply(photo, {}, {}) is photo and layer.image is result_image
    assert action.construct_command(values)[0] == "/blender"


def test_blender_action_relevant_fields_and_transparent_autocrop(monkeypatch):
    action = blender.Action()
    image_size = SimpleNamespace(dirty=False, set_choices=Mock())
    camera = SimpleNamespace(selected_object=None, dialog=None, init_dictionary=Mock())
    monkeypatch.setattr(
        action,
        "_get_field",
        lambda name: image_size if name == "Image Size" else camera,
    )
    monkeypatch.setattr(action, "get_field_string", lambda name: "Box")
    selected = SimpleNamespace(
        image_size_choices=("Fit Image",), get_relevant=lambda owner: ["Box Color"]
    )
    monkeypatch.setattr(
        action,
        "_objects",
        SimpleNamespace(get_selected_object=lambda owner: selected),
    )
    monkeypatch.setattr(
        action, "_camera", SimpleNamespace(get_relevant=lambda owner: ["Camera"])
    )
    monkeypatch.setattr(
        action,
        "_background",
        SimpleNamespace(get_relevant=lambda owner: ["Transparent Background"]),
    )
    monkeypatch.setattr(
        action,
        "_floor",
        SimpleNamespace(get_relevant=lambda owner: ["Show Floor Options"]),
    )
    assert "Box Color" in action.get_relevant_field_labels()
    assert image_size.dirty and camera.init_dictionary.called

    monkeypatch.setattr(
        action, "_external_tools", SimpleNamespace(runner=object()), raising=False
    )
    monkeypatch.setattr(
        action,
        "_imtools",
        SimpleNamespace(auto_crop=Mock(return_value="cropped")),
        raising=False,
    )
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: {})
    monkeypatch.setattr(action, "get_field", lambda *args: True)
    monkeypatch.setattr(
        action_module, "run_image_process", lambda *args, **kwargs: "raw"
    )
    layer = SimpleNamespace(image=object())
    photo = SimpleNamespace(
        info={"size": (10, 10), "mode": "RGBA"}, get_layer=lambda: layer
    )
    action.apply(photo, {}, {})
    assert layer.image == "cropped"


@pytest.mark.parametrize("failure", IMAGE_PROCESS_FAILURES)
def test_blender_apply_preserves_layer_and_skips_crop_on_process_failure(
    monkeypatch, failure
):
    action = blender.Action()
    monkeypatch.setattr(
        action, "_external_tools", SimpleNamespace(runner=object()), raising=False
    )
    auto_crop = Mock()
    monkeypatch.setattr(
        action, "_imtools", SimpleNamespace(auto_crop=auto_crop), raising=False
    )
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: {})
    monkeypatch.setattr(action, "get_field", lambda *args: True)

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(action_module, "run_image_process", fail)
    original = object()
    layer = SimpleNamespace(image=original)
    photo = SimpleNamespace(
        info={"size": (10, 10), "mode": "RGB"}, get_layer=lambda: layer
    )

    with pytest.raises(type(failure)):
        action.apply(photo, {}, {})

    assert layer.image is original
    auto_crop.assert_not_called()


def test_blender_apply_preserves_layer_when_auto_crop_fails(monkeypatch):
    action = blender.Action()
    monkeypatch.setattr(
        action, "_external_tools", SimpleNamespace(runner=object()), raising=False
    )
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: {})
    monkeypatch.setattr(action, "get_field", lambda *args: True)
    monkeypatch.setattr(
        action_module, "run_image_process", lambda *args, **kwargs: object()
    )

    def fail_crop(image):
        raise RuntimeError("crop failed")

    monkeypatch.setattr(
        action, "_imtools", SimpleNamespace(auto_crop=fail_crop), raising=False
    )
    original = object()
    layer = SimpleNamespace(image=original)
    photo = SimpleNamespace(
        info={"size": (10, 10), "mode": "RGB"}, get_layer=lambda: layer
    )

    with pytest.raises(RuntimeError, match="crop failed"):
        action.apply(photo, {}, {})

    assert layer.image is original
