from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import UnidentifiedImageError

from phatch.actions import lossless_jpeg
from phatch.lib.process import (
    Command,
    ProcessCancelledError,
    ProcessExitError,
    ProcessTimeoutError,
)

FAILURE_COMMAND = Command(("jpegtran",))
LOSSLESS_FAILURES = (
    FileNotFoundError("missing output"),
    ProcessExitError(FAILURE_COMMAND, 2, "", "failed"),
    ProcessTimeoutError(FAILURE_COMMAND, 60.0),
    ProcessCancelledError(FAILURE_COMMAND),
    UnidentifiedImageError("corrupt output"),
)


def make_exif_values(transformation):
    return {
        "transformation": transformation,
        "angle": "90 degrees",
        "direction": lossless_jpeg.HORIZONTAL,
        "update_jpeg": False,
        "update_exif_thumbnail": False,
        "update_orientation_tag": False,
        "preserve_timestamp": True,
    }


@pytest.mark.parametrize(
    "transformation",
    [
        lossless_jpeg.AUTOMATIC,
        lossless_jpeg.THUMB,
        lossless_jpeg.ROTATE,
        lossless_jpeg.FLIP,
        lossless_jpeg.TRANSPOSE,
        lossless_jpeg.TRANSVERSE,
    ],
)
def test_exiftran_builds_each_transformation(transformation):
    action = SimpleNamespace(
        values=lambda info: make_exif_values(transformation),
    )

    arguments = lossless_jpeg.Exiftran().get_command_line_args(
        action, SimpleNamespace(info={})
    )

    assert arguments
    assert "-ni" in arguments
    assert "-nt" in arguments
    assert "-no" in arguments
    assert "-p" in arguments


@pytest.mark.parametrize(
    ("transformation", "expected"),
    [
        (lossless_jpeg.ROTATE, "Angle"),
        (lossless_jpeg.FLIP, "Direction"),
        (lossless_jpeg.THUMB, "Preserve Timestamp"),
        (lossless_jpeg.AUTOMATIC, "Show Advanced Options"),
    ],
)
def test_exiftran_selects_relevant_fields(transformation, expected):
    values = {
        "Transformation": transformation,
        "Show Advanced Options": False,
    }
    action = SimpleNamespace(get_field_string=values.__getitem__)

    labels = lossless_jpeg.Exiftran().get_relevant_field_labels(action)

    assert expected in labels


def test_exiftran_includes_advanced_fields_and_argv():
    values = {
        "Transformation": lossless_jpeg.AUTOMATIC,
        "Show Advanced Options": "yes",
    }
    action = SimpleNamespace(
        get_field_string=values.__getitem__,
        values=lambda info: make_exif_values(lossless_jpeg.AUTOMATIC),
    )
    utility = lossless_jpeg.Exiftran()

    labels = utility.get_relevant_field_labels(action)
    argv = utility.build_argv(
        Path("exiftran"),
        action,
        SimpleNamespace(info={}),
        Path("input.jpg"),
        Path("output.jpg"),
    )

    assert "Update JPEG" in labels
    assert argv[:3] == ("exiftran", "-i", "input.jpg")
    assert argv[-2:] == ("-o", "output.jpg")


def test_exiftran_omits_disabled_advanced_options():
    values = make_exif_values(lossless_jpeg.AUTOMATIC)
    values.update(
        {
            "update_jpeg": True,
            "update_exif_thumbnail": True,
            "update_orientation_tag": True,
            "preserve_timestamp": False,
        }
    )
    action = SimpleNamespace(values=lambda info: values)

    assert lossless_jpeg.Exiftran().get_command_line_args(
        action, SimpleNamespace(info={})
    ) == ["-a"]


def make_jpeg_values(transformation, mode="Custom"):
    return {
        "transformation_": transformation,
        "copy": "All",
        "mode": mode,
        "left": 1,
        "top": 2,
        "right": 3,
        "bottom": 4,
        "all": 5,
        "width": 20,
        "height": 10,
        "angle_": "90 degrees",
        "direction_": lossless_jpeg.HORIZONTAL,
    }


@pytest.mark.parametrize(
    "transformation",
    [
        lossless_jpeg.COPY,
        lossless_jpeg.CROP,
        lossless_jpeg.ROTATE,
        lossless_jpeg.FLIP,
        lossless_jpeg.GRAYSCALE,
        lossless_jpeg.TRANSPOSE,
        lossless_jpeg.TRANSVERSE,
    ],
)
def test_jpegtran_builds_each_transformation(monkeypatch, transformation):
    values = make_jpeg_values(transformation)
    monkeypatch.setattr(
        lossless_jpeg.models.CropMixin,
        "values",
        lambda self, info, action: values,
    )
    photo = SimpleNamespace(
        info={"size": (20, 10)},
        get_flattened_image=lambda: SimpleNamespace(getbbox=lambda: (1, 2, 9, 8)),
    )

    arguments = lossless_jpeg.Jpegtran().get_command_line_args(SimpleNamespace(), photo)

    assert arguments


@pytest.mark.parametrize("mode", ["Auto", "All"])
def test_jpegtran_builds_crop_modes(monkeypatch, mode):
    values = make_jpeg_values(lossless_jpeg.CROP, mode=mode)
    monkeypatch.setattr(
        lossless_jpeg.models.CropMixin,
        "values",
        lambda self, info, action: values,
    )
    photo = SimpleNamespace(
        info={"size": (20, 10)},
        get_flattened_image=lambda: SimpleNamespace(getbbox=lambda: (1, 2, 9, 8)),
    )

    arguments = lossless_jpeg.Jpegtran().get_command_line_args(SimpleNamespace(), photo)

    assert str(arguments).startswith("-crop")


@pytest.mark.parametrize(
    ("transformation", "expected"),
    [
        (lossless_jpeg.COPY, "Copy"),
        (lossless_jpeg.ROTATE, "Angle "),
        (lossless_jpeg.FLIP, "Direction "),
        (lossless_jpeg.GRAYSCALE, None),
    ],
)
def test_jpegtran_selects_relevant_fields(monkeypatch, transformation, expected):
    monkeypatch.setattr(
        lossless_jpeg.models.CropMixin,
        "get_relevant_field_labels",
        lambda self, action: ["Crop"],
    )
    action = SimpleNamespace(get_field_string=lambda label: transformation)

    labels = lossless_jpeg.Jpegtran().get_relevant_field_labels(action)

    assert (expected is None and labels == ["Transformation "]) or expected in labels


def test_jpegtran_formats_exact_argv(monkeypatch):
    utility = lossless_jpeg.Jpegtran()
    monkeypatch.setattr(
        utility, "get_command_line_args", lambda action, photo: ["-copy"]
    )

    argv = utility.build_argv(
        Path("jpegtran"),
        SimpleNamespace(),
        SimpleNamespace(),
        Path("input.jpg"),
        Path("output.jpg"),
    )

    assert argv == ("jpegtran", "-copy", "-outfile", "output.jpg", "input.jpg")


def test_action_interface_and_utility_dispatch(monkeypatch):
    action = lossless_jpeg.Action()
    action.interface(action._fields)
    utility = next(iter(action.utilities.values()))
    photo = SimpleNamespace(info={}, call=lambda command: None)
    calls = []
    monkeypatch.setattr(action, "get_field", lambda label, info: utility.name)
    monkeypatch.setattr(
        action, "call", lambda photo, info, selected: calls.append(selected)
    )

    result = action.apply(photo, setting={}, cache={})

    assert result is photo
    assert calls == [utility]


def test_utility_mixin_relevant_fields(monkeypatch):
    action = lossless_jpeg.Action()
    utility = next(iter(action.utilities.values()))
    monkeypatch.setattr(action, "get_field_string", lambda label: utility.name)
    monkeypatch.setattr(
        utility,
        "get_relevant_field_labels",
        lambda selected: ["Transformation"],
    )
    labels = lossless_jpeg.UtilityMixin.get_relevant_field_labels(action)

    assert labels == ["Utility", "Transformation"]


def test_lossless_relevant_fields_include_output_location(monkeypatch):
    action = lossless_jpeg.Action()
    monkeypatch.setattr(
        lossless_jpeg.UtilityMixin,
        "get_relevant_field_labels",
        lambda self, relevant=None: relevant,
    )

    assert action.get_relevant_field_labels() == ["File Name", "In"]


def test_lossless_call_reports_only_after_transaction(monkeypatch, tmp_path):
    action = lossless_jpeg.Action()
    utility = lossless_jpeg.Exiftran()
    monkeypatch.setattr(utility, "preserves_timestamp", lambda action, photo: False)
    reports = []
    photo = SimpleNamespace(append_to_report=reports.append)
    calls = []
    monkeypatch.setattr(
        action,
        "get_field",
        lambda label, info: "output" if label == "File Name" else str(tmp_path),
    )
    monkeypatch.setattr(
        lossless_jpeg, "run_lossless_jpeg", lambda *args: calls.append(args)
    )
    monkeypatch.setattr(
        action, "_external_tools", SimpleNamespace(runner=Mock()), raising=False
    )
    action._initialized_utility = utility.name
    action._initialized_executable = Path("/exiftran")

    action.call(
        photo,
        {"format": "JPEG", "path": str(tmp_path / "input.jpg"), "type": "jpg"},
        utility,
    )

    assert len(calls) == 1
    assert reports == [str(tmp_path / "output.jpg")]


@pytest.mark.parametrize("failure", LOSSLESS_FAILURES)
def test_lossless_call_does_not_report_failed_transaction(
    monkeypatch, tmp_path, failure
):
    action = lossless_jpeg.Action()
    utility = lossless_jpeg.Exiftran()
    monkeypatch.setattr(utility, "preserves_timestamp", lambda action, photo: False)
    monkeypatch.setattr(
        action,
        "get_field",
        lambda label, info: "output" if label == "File Name" else str(tmp_path),
    )

    def fail(*args):
        raise failure

    monkeypatch.setattr(lossless_jpeg, "run_lossless_jpeg", fail)
    monkeypatch.setattr(
        action, "_external_tools", SimpleNamespace(runner=Mock()), raising=False
    )
    action._initialized_utility = utility.name
    action._initialized_executable = Path("/exiftran")
    reports = []
    photo = SimpleNamespace(append_to_report=reports.append)

    with pytest.raises(type(failure)):
        action.call(
            photo,
            {"format": "JPEG", "path": str(tmp_path / "input.jpg"), "type": "jpg"},
            utility,
        )

    assert reports == []


def test_executable_for_resolves_when_utility_differs_from_initialized_one(monkeypatch):
    action = lossless_jpeg.Action()
    utility = lossless_jpeg.Jpegtran()
    executable = Mock(return_value=Path("/jpegtran"))
    action._initialized_utility = "selected"
    monkeypatch.setattr(
        action,
        "_external_tools",
        SimpleNamespace(executable=executable),
        raising=False,
    )

    assert action._executable_for(utility) == Path("/jpegtran")
    executable.assert_called_once_with(lossless_jpeg.JPEGTRAN)


def test_lossless_call_rejects_non_jpeg_input():
    action = lossless_jpeg.Action()
    utility = lossless_jpeg.Exiftran()
    with pytest.raises(Exception, match="PNG"):
        action.call(SimpleNamespace(), {"format": "PNG", "path": "input.png"}, utility)


def test_action_resolves_only_selected_utility():
    tools = Mock()
    tools.executable.return_value = Path("/exiftran")
    action = lossless_jpeg.Action()

    action.init(tools)

    tools.executable.assert_called_once_with(lossless_jpeg.EXIFTRAN)
