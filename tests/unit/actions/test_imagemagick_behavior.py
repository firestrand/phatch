from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import UnidentifiedImageError

from phatch.actions import _imagemagick_action as action_module
from phatch.actions import imagemagick
from phatch.lib.image_process import ImageProcessPaths
from phatch.lib.process import (
    Command,
    ProcessCancelledError,
    ProcessExitError,
    ProcessTimeoutError,
)

FAILURE_COMMAND = Command(("convert",))
IMAGE_PROCESS_FAILURES = (
    FileNotFoundError("missing output"),
    ProcessExitError(FAILURE_COMMAND, 2, "", "failed"),
    ProcessTimeoutError(FAILURE_COMMAND, 60.0),
    ProcessCancelledError(FAILURE_COMMAND),
    UnidentifiedImageError("corrupt output"),
)


@pytest.mark.parametrize("effect", ["Bullet", "Sigmoidal Contrast", "Blur"])
def test_apply_builds_command_and_replaces_layer_after_success(monkeypatch, effect):
    action = imagemagick.Action()
    action._convert = Path("/convert")
    action._external_tools = SimpleNamespace(runner=object())
    values = {
        "color": "red",
        "contrast_factor": 100,
        "contrast_treshold": 50,
        "blur_radius": 1,
        "blur_sigma": 2,
    }
    monkeypatch.setattr(action, "get_field", lambda *args: effect)
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: values)
    rendered = object()

    def run(image, runner, command_builder):
        paths = ImageProcessPaths(Path("."), Path("in.png"), Path("out.png"))
        command = command_builder(paths)
        assert command.argv[0] == "/convert"
        return rendered

    monkeypatch.setattr(action_module, "run_image_process", run)
    layer = SimpleNamespace(image=object())
    photo = SimpleNamespace(info={"size": (20, 10)}, get_layer=lambda: layer)

    assert action.apply(photo, {}, {}) is photo
    assert layer.image is rendered
    if effect == "Bullet":
        assert values["shade"] == "120x30"
    elif effect == "Sigmoidal Contrast":
        assert values["contrast_factor"] == 10


@pytest.mark.parametrize("failure", IMAGE_PROCESS_FAILURES)
def test_apply_preserves_layer_when_image_process_fails(monkeypatch, failure):
    action = imagemagick.Action()
    action._convert = Path("/convert")
    action._external_tools = SimpleNamespace(runner=object())
    monkeypatch.setattr(action, "get_field", lambda *args: "Blur")
    monkeypatch.setattr(action, "values", lambda *args, **kwargs: {})

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr(action_module, "run_image_process", fail)
    original = object()
    layer = SimpleNamespace(image=original)
    photo = SimpleNamespace(info={"size": (20, 10)}, get_layer=lambda: layer)

    with pytest.raises(type(failure)):
        action.apply(photo, {}, {})

    assert layer.image is original
