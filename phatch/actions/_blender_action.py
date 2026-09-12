from __future__ import annotations

import builtins
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from core import models
from core.config import PATHS

from phatch.actions._blender_argv import BlenderInvocation, build_blender_argv
from phatch.actions._blender_options import Background, BlenderObjects, Camera, Floor
from phatch.lib.external_capability_probes import BLENDER_LEGACY
from phatch.lib.image_process import ImageProcessPaths, run_image_process
from phatch.lib.process import Command

translate = cast(Callable[[str], str], builtins.__dict__["_"])


class BlenderActionMixin(models.Action):
    BlenderObjectField: Any
    ChoiceField: Any
    PixelField: Any

    def __init__(self, **options):
        self._objects = BlenderObjects()
        self._background = Background()
        self._floor = Floor()
        self._camera = Camera()
        super().__init__(**options)

    def init(self, tools=None):
        from lib import imtools

        self._imtools = imtools
        self._external_tools = tools or self.plugin_context.external_tools
        self._blender = self._external_tools.executable(BLENDER_LEGACY)

    def interface(self, fields):
        from phatch.actions._blender_options import SIZE_CHOICES

        fields["Render Width"] = self.PixelField("800px")
        fields["Render Height"] = self.PixelField("600px")
        fields["Object"] = self.BlenderObjectField("Box")
        fields["Image Size"] = self.ChoiceField(SIZE_CHOICES[0], choices=SIZE_CHOICES)
        self._objects.interface(self, fields)
        self._camera.interface(self, fields)
        self._background.interface(self, fields)
        self._floor.interface(self, fields)

    def get_relevant_field_labels(self):
        relevant = ["Render Width", "Render Height", "Object", "Image Size"]
        image_size = self._get_field("Image Size")
        image_size.dirty = True
        selected_object = self._objects.get_selected_object(self)
        relevant.extend(selected_object.get_relevant(self))
        image_size.set_choices(selected_object.image_size_choices)
        relevant.extend(self._camera.get_relevant(self))
        relevant.extend(self._background.get_relevant(self))
        relevant.extend(self._floor.get_relevant(self))
        camera = self._get_field("Camera")
        camera.selected_object = self.get_field_string("Object")
        camera.dialog = translate("Select Rotation for %s") % translate(
            camera.selected_object
        )
        camera.init_dictionary()
        return relevant

    def apply(self, photo, setting, cache):
        info = photo.info
        width, height = info["size"]
        values = self.values(
            info,
            pixel_fields={
                "Render Width": width,
                "Render Height": height,
                "Box Depth": height,
            },
        )
        mode = info["mode"]
        if mode in ("RGBA", "LA") or (mode == "P" and "transparency" in info):
            mode, suffix = "RGBA", ".png"
        else:
            mode, suffix = "RGB", ".bmp"
        layer = photo.get_layer()
        result = run_image_process(
            layer.image,
            self._external_tools.runner,
            lambda paths: Command(
                self.construct_command(values, paths), timeout_seconds=300.0
            ),
            input_suffix=suffix,
            output_relative=Path("render/0001.png"),
            input_mode=mode,
        )
        if self.get_field("Auto Crop", info):
            result = self._imtools.auto_crop(result)
        layer.image = result
        return photo

    def construct_command(self, values, paths=None):
        values["amount_of_input_images"] = 1
        values["input_image_2"] = ""
        selected_object = self._objects.get_selected_object(self)
        selected_object.set_args(self, values)
        self._background.set_args(self, values)
        self._camera.set_args(self, values)
        if paths is None:
            paths = ImageProcessPaths(
                Path("."), Path("file_in.bmp"), Path("file_out.png")
            )
        invocation = BlenderInvocation(
            self._blender,
            Path(PATHS["PHATCH_BLENDER_PATH"]),
            selected_object.name,
            selected_object.extra_options,
        )
        return build_blender_argv(invocation, paths, values)
