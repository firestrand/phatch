from __future__ import annotations

from pathlib import Path

from phatch.actions._blender_argv import BlenderInvocation, build_blender_argv
from phatch.lib.image_process import ImageProcessPaths


def test_blender_argv_keeps_each_legacy_key_value_literal() -> None:
    paths = ImageProcessPaths(
        Path("/private dir"),
        Path("/private dir/input image.png"),
        Path("/private dir/render/0001.png"),
    )
    values = {
        "render_width": 800,
        "render_height": 600,
        "image_size": "Fit Image",
        "amount_of_input_images": 1,
        "input_image_2": "C:/literal $;&()%'quote.png",
        "gradient_top": "#11133A",
        "gradient_bottom": "#5B86B5",
        "alpha": False,
        "stars": False,
        "stars_color": "#FFFFFF",
        "mist": False,
        "use_floor": True,
        "floor_color": "#11133A",
        "floor_reflection": 70,
        "floor_opacity": 100,
        "camera_lens_angle": 51,
        "camera_distance": 2,
        "camera_roll": 0,
        "camera_vertical_rotation": 0,
        "camera_horizontal_rotation": -30,
        "box_color": "#FFFFFF",
        "box_depth": 30,
    }
    invocation = BlenderInvocation(
        executable=Path("/tool path/blender"),
        asset_root=Path("/asset path/blender"),
        object_name="Box",
        extra_options=("Box Color", "Box Depth"),
    )

    argv = build_blender_argv(invocation, paths, values)

    assert argv[:7] == (
        "/tool path/blender",
        "-b",
        "/asset path/blender/box.blend",
        "-P",
        "/asset path/blender/runner.py",
        "--",
        "input_image_1:/private dir/input image.png",
    )
    assert "input_image_2:C:/literal $;&()%'quote.png" in argv
    assert "render_path:/private dir/render/file_out.png" in argv
    assert "script:box" in argv


def test_blender_argv_omits_optional_extra_option_when_not_relevant() -> None:
    paths = ImageProcessPaths(Path("."), Path("input.png"), Path("render/0001.png"))
    values = {
        "render_width": 1,
        "render_height": 1,
        "image_size": "Scale Image",
        "amount_of_input_images": 1,
        "input_image_2": "",
        "gradient_top": "black",
        "gradient_bottom": "white",
        "alpha": False,
        "stars": False,
        "stars_color": "white",
        "mist": False,
        "use_floor": True,
        "floor_color": "black",
        "floor_reflection": 0,
        "floor_opacity": 100,
        "camera_lens_angle": 51,
        "camera_distance": 2,
        "camera_roll": 0,
        "camera_vertical_rotation": 0,
        "camera_horizontal_rotation": 0,
        "cover_color": "white",
        "page_mapping": "Wrap Both",
    }
    invocation = BlenderInvocation(
        Path("blender"),
        Path("assets"),
        "Book",
        ("Cover Color", "Page Mapping", "Left Page"),
    )

    argv = build_blender_argv(invocation, paths, values)

    assert not any(argument.startswith("left_page:") for argument in argv)
