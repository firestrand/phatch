from __future__ import annotations

from typing import Any, ClassVar

from core import models
from lib.reverse_translation import _t

from phatch.actions._imagemagick_argv import build_argv
from phatch.lib.external_capability_probes import IMAGEMAGICK_6
from phatch.lib.image_process import run_image_process
from phatch.lib.process import Command


class ImageMagickActionMixin(models.Action):
    SMALL_PIXELS: ClassVar[list[str]]
    STAMPS: ClassVar[list[str]]
    CharField: Any
    ChoiceField: Any
    ColorField: Any
    PixelField: Any
    SliderField: Any

    def init(self, tools=None):
        self._external_tools = tools or self.plugin_context.external_tools
        self._convert = self._external_tools.executable(IMAGEMAGICK_6)

    def interface(self, fields):
        from phatch.actions._imagemagick_argv import BUILDERS

        actions = sorted(BUILDERS)
        fields[_t("Action")] = self.ChoiceField("Polaroid", choices=actions)
        fields[_t("Horizontal Offset")] = self.PixelField(
            "2%", choices=self.SMALL_PIXELS
        )
        fields[_t("Vertical Offset")] = self.PixelField("2%", choices=self.SMALL_PIXELS)
        fields[_t("Color")] = self.ColorField("#FF0000")
        fields[_t("Border Color")] = self.ColorField("#FFFFFF")
        fields[_t("Shadow Color")] = self.ColorField("#000000")
        fields[_t("Caption")] = self.CharField(choices=self.STAMPS)
        fields[_t("Charcoal Radius")] = self.PixelField("0.5%")
        fields[_t("Contrast Factor")] = self.SliderField(100, 0, 100)
        fields[_t("Contrast Treshold")] = self.SliderField(50, 0, 100)
        fields[_t("Blur Radius")] = self.PixelField("80px")
        fields[_t("Blur Sigma")] = self.PixelField("3px")
        fields[_t("Blur Angle")] = self.SliderField(120, 0, 359)
        fields[_t("Paint Radius")] = self.PixelField("0.5%")
        fields[_t("Sharpen Radius")] = self.PixelField("0px")
        fields[_t("Sharpen Sigma")] = self.PixelField("3px")
        fields[_t("Sketch Radius")] = self.PixelField("0px")
        fields[_t("Sketch Sigma")] = self.PixelField("20px")
        fields[_t("Sketch Angle")] = self.SliderField(120, 0, 359)
        fields[_t("Unsharp Radius")] = self.PixelField("0px")
        fields[_t("Unsharp Sigma")] = self.PixelField("3px")
        fields[_t("Wave Height")] = self.PixelField("0px")
        fields[_t("Wave Length")] = self.PixelField("3px")

    def get_relevant_field_labels(self):
        action = self.get_field_string("Action")
        relevant = ["Action"]
        fields = {
            "Blur": ["Blur Radius", "Blur Sigma"],
            "Bullet": ["Color"],
            "Charcoal": ["Charcoal Radius"],
            "Motion Blur": ["Blur Radius", "Blur Sigma", "Blur Angle"],
            "Paint": ["Paint Radius"],
            "Polaroid": ["Border Color", "Shadow Color", "Caption"],
            "Shadow": [
                "Horizontal Offset",
                "Vertical Offset",
                "Shadow Color",
                "Blur Radius",
                "Blur Sigma",
            ],
            "Sharpen": ["Sharpen Radius", "Sharpen Sigma"],
            "Pencil Sketch": ["Sketch Radius", "Sketch Sigma", "Sketch Angle"],
            "Sigmoidal Contrast": ["Contrast Factor", "Contrast Treshold"],
            "Unsharp": ["Unsharp Radius", "Unsharp Sigma"],
            "Wave": ["Wave Height", "Wave Length"],
        }
        relevant.extend(fields.get(action, []))
        return relevant

    def apply(self, photo, setting, cache):
        info = photo.info
        action = self.get_field("Action", info)
        width, height = info["size"]
        diameter = (width + height) / 2
        values = self.values(
            info,
            pixel_fields={
                "Horizontal Offset": width,
                "Vertical Offset": height,
                "Blur Radius": diameter,
                "Blur Sigma": diameter,
                "Charcoal Radius": diameter,
                "Paint Radius": diameter,
                "Sharpen Radius": diameter,
                "Sharpen Sigma": diameter,
                "Sketch Radius": diameter,
                "Sketch Sigma": diameter,
                "Unsharp Radius": diameter,
                "Unsharp Sigma": diameter,
                "Wave Height": diameter,
                "Wave Length": diameter,
            },
        )
        if action == "Bullet":
            values["border"] = diameter / 3
            values["blur1"] = diameter / 7
            values["shade"] = f"{int(diameter + 105)}x{int(diameter + 15)}"
            values["blur2"] = diameter / 12
        elif action == "Sigmoidal Contrast":
            values["contrast_factor"] /= 10.0
        layer = photo.get_layer()
        result = run_image_process(
            layer.image,
            self._external_tools.runner,
            lambda paths: Command(
                build_argv(action, self._convert, paths, values),
                timeout_seconds=60.0,
            ),
        )
        layer.image = result
        return photo
