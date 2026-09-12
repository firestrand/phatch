from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType

from PIL import Image
from PIL import __version__ as pillow_version

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)


@dataclass(frozen=True, slots=True)
class ImageCodecCapability:
    format_name: str
    extensions: tuple[str, ...]
    can_read: bool
    can_write: bool


def register_optional_heif() -> ModuleType | None:
    try:
        module = importlib.import_module("pillow_heif")
    except ImportError:
        return None
    register = getattr(module, "register_heif_opener", None)
    if not callable(register):
        return module
    register()
    return module


def codec_capabilities() -> tuple[ImageCodecCapability, ...]:
    register_optional_heif()
    Image.init()
    extensions_by_format: dict[str, list[str]] = {}
    for extension, format_name in Image.registered_extensions().items():
        extensions_by_format.setdefault(format_name, []).append(extension.casefold())
    formats = sorted(set(Image.OPEN) | set(Image.SAVE) | set(extensions_by_format))
    return tuple(
        ImageCodecCapability(
            format_name,
            tuple(sorted(extensions_by_format.get(format_name, ()))),
            format_name in Image.OPEN,
            format_name in Image.SAVE,
        )
        for format_name in formats
    )


def codec_for_extension(
    extension: str,
    capabilities: tuple[ImageCodecCapability, ...],
) -> ImageCodecCapability | None:
    normalized = f".{extension.lstrip('.').casefold()}"
    return next(
        (
            capability
            for capability in capabilities
            if normalized in capability.extensions
        ),
        None,
    )


def codec_capability(extension: str) -> Capability:
    normalized = extension.lstrip(".").casefold()
    codec = codec_for_extension(normalized, codec_capabilities())
    identifier = CapabilityId(f"image-codec-write:{normalized}")
    if codec is not None and codec.can_write:
        return Capability(
            identifier,
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            f"Pillow registered the {codec.format_name} encoder",
            version=pillow_version,
        )
    return Capability(
        identifier,
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_PACKAGE,
        f"no Pillow encoder is registered for .{normalized}",
        version=pillow_version,
    )


def codec_registry_capabilities() -> tuple[Capability, ...]:
    return tuple(
        Capability(
            CapabilityId(f"image-codec-write:{extension.lstrip('.')}"),
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            f"Pillow registered the {codec.format_name} encoder",
            version=pillow_version,
        )
        for codec in codec_capabilities()
        if codec.can_write
        for extension in codec.extensions
    )
