from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from phatch.lib.image_process import ImageProcessPaths

Value = str | int | float | bool


@dataclass(frozen=True, slots=True)
class BlenderInvocation:
    executable: Path
    asset_root: Path
    object_name: str
    extra_options: tuple[str, ...]


def _argument(name: str, value: Value) -> str:
    return f"{name}:{value}"


def build_blender_argv(
    invocation: BlenderInvocation,
    paths: ImageProcessPaths,
    values: Mapping[str, Value],
) -> tuple[str, ...]:
    root = invocation.asset_root
    render_target = paths.output.parent / "file_out.png"
    arguments = [
        _argument("input_image_1", str(paths.input)),
        _argument("render_path", str(render_target)),
        "script:box",
        _argument("script_path", str(root / "object.py")),
        _argument("render_width", values["render_width"]),
        _argument("render_height", values["render_height"]),
        _argument("image_size", values["image_size"]),
        _argument("object", invocation.object_name),
        _argument("amount_of_input_images", values["amount_of_input_images"]),
        _argument("input_image_2", values["input_image_2"]),
    ]
    for label in invocation.extra_options:
        name = label.lower().replace(" ", "_")
        if name in values:
            arguments.append(_argument(name, values[name]))
    arguments.extend(
        _argument(name, values[name])
        for name in (
            "gradient_top",
            "gradient_bottom",
            "alpha",
            "stars",
            "stars_color",
            "mist",
            "use_floor",
            "floor_color",
            "floor_reflection",
            "floor_opacity",
            "camera_lens_angle",
            "camera_distance",
        )
    )
    arguments.extend(
        (
            _argument("rotation_x", values["camera_roll"]),
            _argument("rotation_y", values["camera_vertical_rotation"]),
            _argument("rotation_z", values["camera_horizontal_rotation"]),
        )
    )
    return (
        str(invocation.executable),
        "-b",
        str(root / f"{invocation.object_name.lower()}.blend"),
        "-P",
        str(root / "runner.py"),
        "--",
        *arguments,
    )
