from __future__ import annotations

import os

from lib.reverse_translation import _t

FIT_IMAGE = _t("Fit Image")
LETTERBOX = _t("Letterbox")
SCALE_IMAGE = _t("Scale Image")
SCALE_MODEL = _t("Scale Model")
SIZE_CHOICES = (FIT_IMAGE, LETTERBOX, SCALE_IMAGE, SCALE_MODEL)


class BlenderObject:
    image_size_choices: tuple[str, ...] = ()
    extra_options: tuple[str, ...] = ()

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def interface(self, action, fields) -> None:
        return None

    def get_relevant(self, action) -> list[str]:
        return []

    def set_args(self, action, values) -> None:
        if len(self.image_size_choices) == 1:
            values["image_size"] = self.image_size_choices[0]


class Book(BlenderObject):
    image_size_choices = (SCALE_IMAGE,)
    extra_options = ("Cover Color", "Page Mapping", "Left Page")

    def interface(self, action, fields) -> None:
        mapping_choices = (_t("Wrap Both"), _t("Separate"))
        fields[_t("Cover Color")] = action.ColorField("#FFFFFF")
        fields[_t("Page Mapping")] = action.ChoiceField(
            mapping_choices[0], choices=mapping_choices
        )
        fields[_t("Left Page")] = action.EmptyFileField(" ")

    def get_relevant(self, action) -> list[str]:
        relevant = ["Cover Color", "Page Mapping"]
        if action.get_field_string("Page Mapping") == "Separate":
            relevant.append("Left Page")
        return relevant

    def set_args(self, action, values) -> None:
        super().set_args(action, values)
        values["amount_of_input_images"] += 1
        if action.get_field_string("Page Mapping") == "Separate":
            values["input_image_2"] = action.get_field_string("Left Page")


class Box(BlenderObject):
    image_size_choices = SIZE_CHOICES
    extra_options = ("Box Color", "Box Depth")

    def interface(self, action, fields) -> None:
        fields[_t("Box Color")] = action.ColorField("#FFFFFF")
        fields[_t("Box Depth")] = action.PixelField("30%")

    def get_relevant(self, action) -> list[str]:
        return ["Box Color", "Box Depth"]


class Can(BlenderObject):
    image_size_choices = (SCALE_IMAGE,)


class Cd(BlenderObject):
    image_size_choices = (FIT_IMAGE, LETTERBOX, SCALE_IMAGE)
    extra_options = ("Lid Rotation",)

    def interface(self, action, fields) -> None:
        fields[_t("Lid Rotation")] = action.SliderField(0, 0, 300)

    def get_relevant(self, action) -> list[str]:
        return ["Lid Rotation"]


class Lcd(BlenderObject):
    image_size_choices = SIZE_CHOICES


class Sphere(BlenderObject):
    image_size_choices = (SCALE_IMAGE,)


class BlenderObjects(list[BlenderObject]):
    def __init__(self) -> None:
        super().__init__([Book(), Box(), Can(), Cd(), Lcd(), Sphere()])

    def interface(self, action, fields) -> None:
        for blender_object in self:
            blender_object.interface(action, fields)

    def get_selected_object(self, action) -> BlenderObject:
        name = action.get_field_string("Object")
        for blender_object in self:
            if name == blender_object.name:
                return blender_object
        raise LookupError(name)


class Camera:
    def interface(self, action, fields) -> None:
        fields[_t("Camera")] = action.BlenderRotationField("Hori -30 Vert 0")
        fields[_t("Camera Horizontal Rotation")] = action.SliderField(30, -180, 180)
        fields[_t("Camera Vertical Rotation")] = action.SliderField(0, 0, 90)
        fields[_t("Camera Roll")] = action.SliderField(0, -90, 90)
        fields[_t("Camera Lens Angle")] = action.SliderField(51, 8, 172)
        fields[_t("Camera Distance")] = action.SliderField(2, 0, 10)

    def get_relevant(self, action) -> list[str]:
        relevant = ["Camera"]
        camera = action.get_field_string("Camera")
        if camera == "User":
            relevant.extend(
                [
                    "Camera Horizontal Rotation",
                    "Camera Vertical Rotation",
                    "Camera Roll",
                    "Camera Lens Angle",
                    "Camera Distance",
                ]
            )
        else:
            rotation = camera.split()
            action.set_field_as_string_dirty("Camera Horizontal Rotation", rotation[1])
            action.set_field_as_string_dirty("Camera Vertical Rotation", rotation[3])
            action.set_field_as_string_dirty("Camera Roll", "0")
            action.set_field_as_string_dirty("Camera Lens Angle", "51")
            action.set_field_as_string_dirty("Camera Distance", "2")
        return relevant

    def set_args(self, action, values) -> None:
        filename = os.path.split(values["camera"])[1]
        stem = filename.rsplit(".")[0]
        if stem.lower() != "user":
            rotation = stem.split("_")
            values["camera_horizontal_rotation"] = rotation[1]
            values["camera_vertical_rotation"] = rotation[3]


class Floor:
    def interface(self, action, fields) -> None:
        fields[_t("Show Floor Options")] = action.BooleanField(False)
        fields[_t("Use Floor")] = action.BooleanField(True)
        fields[_t("Floor Color")] = action.ColorField("#11133A")
        fields[_t("Floor Reflection")] = action.SliderField(70, 0, 100)
        fields[_t("Floor Opacity")] = action.SliderField(100, 0, 100)

    def get_relevant(self, action) -> list[str]:
        relevant = ["Show Floor Options"]
        if action.is_field_true("Show Floor Options"):
            relevant.append("Use Floor")
            if action.is_field_true("Use Floor"):
                relevant.extend(["Floor Color", "Floor Reflection", "Floor Opacity"])
        return relevant


class Background:
    def interface(self, action, fields) -> None:
        fields[_t("Transparent Background")] = action.BooleanField(False)
        fields[_t("Show Background Options")] = action.BooleanField(False)
        fields[_t("Background")] = action.ChoiceField(
            "Gradient", choices=(_t("Color"), _t("Gradient"), _t("Transparent"))
        )
        fields[_t("Background Color")] = action.ColorField("#11133A")
        fields[_t("Gradient Top")] = action.ColorField("#11133A")
        fields[_t("Gradient Bottom")] = action.ColorField("#5B86B5")
        fields[_t("Auto Crop")] = action.BooleanField(True)
        fields[_t("Stars")] = action.BooleanField(False)
        fields[_t("Stars Color")] = action.ColorField("#FFFFFF")
        fields[_t("Mist")] = action.BooleanField(False)

    def get_relevant(self, action) -> list[str]:
        relevant = ["Transparent Background"]
        if action.is_field_true("Transparent Background"):
            relevant.append("Auto Crop")
            return relevant
        relevant.append("Show Background Options")
        if not action.is_field_true("Show Background Options"):
            return relevant
        background = action.get_field_string("Background")
        relevant.append("Background")
        if background == "Color":
            relevant.append("Background Color")
        elif background == "Transparent":
            relevant.append("Auto Crop")
        else:
            relevant.extend(["Gradient Top", "Gradient Bottom"])
        if background != "Transparent":
            relevant.extend(["Stars", "Mist"])
            if action.is_field_true("Stars"):
                relevant.append("Stars Color")
        return relevant

    def set_args(self, action, values) -> None:
        if values["background"] == "Color":
            values["gradient_top"] = values["background_color"]
            values["gradient_bottom"] = values["background_color"]
        values["alpha"] = values["background"] == "Transparent"
        if values["transparent_background"]:
            values["alpha"] = True
            values["use_floor"] = False
