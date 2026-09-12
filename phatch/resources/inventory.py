from __future__ import annotations

from enum import StrEnum, unique
from typing import Final

from .provider import LogicalResource


@unique
class ResourceClass(StrEnum):
    ACTION_LISTS = "action-lists"
    BLENDER = "blender"
    DOCUMENTATION = "documentation"
    FONTS = "fonts"
    HIGHLIGHTS = "highlights"
    IMAGES = "images"
    LOCALES = "locales"
    MASKS = "masks"
    PERSPECTIVE = "perspective"


RESOURCE_CLASSES: Final = {
    ResourceClass.ACTION_LISTS: LogicalResource("data/actionlists"),
    ResourceClass.BLENDER: LogicalResource("data/blender"),
    ResourceClass.DOCUMENTATION: LogicalResource("docs"),
    ResourceClass.FONTS: LogicalResource("data/fonts"),
    ResourceClass.HIGHLIGHTS: LogicalResource("data/highlights"),
    ResourceClass.IMAGES: LogicalResource("images"),
    ResourceClass.LOCALES: LogicalResource("locale"),
    ResourceClass.MASKS: LogicalResource("data/masks"),
    ResourceClass.PERSPECTIVE: LogicalResource("data/perspective"),
}
