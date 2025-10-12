"""Shared helpers for action modules."""

from __future__ import annotations

from typing import Any


def resolve_orientation(orientation: Any, image_module: Any) -> Any:
    """Convert orientation string names to Pillow constants when possible."""

    if isinstance(orientation, str) and image_module is not None:
        value = getattr(image_module, orientation, None)
        if value is not None:
            return value
    return orientation
