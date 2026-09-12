from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityRegistry,
    CapabilityStatus,
)
from phatch.lib.process import ProcessRunner


class ExecutableFinder(Protocol):
    def find(self, name: str) -> Path | None: ...


@dataclass(frozen=True, slots=True)
class ExecutableCapabilityProbe:
    identifier: CapabilityId
    executable_name: str
    lookup: ExecutableFinder

    def __call__(self) -> Capability:
        executable = self.lookup.find(self.executable_name)
        if executable is None:
            return Capability(
                identifier=self.identifier,
                status=CapabilityStatus.UNAVAILABLE,
                reason_code=CapabilityReasonCode.MISSING_EXECUTABLE,
                reason=f"install {self.executable_name} or configure its directory",
            )
        return Capability(
            identifier=self.identifier,
            status=CapabilityStatus.AVAILABLE,
            reason_code=CapabilityReasonCode.AVAILABLE,
            reason=f"found {self.executable_name}",
            executable=executable,
        )


@dataclass(frozen=True, slots=True)
class ModuleCapabilityProbe:
    identifier: CapabilityId
    module_name: str
    distribution_name: str | None = None

    def __call__(self) -> Capability:
        try:
            specification = importlib.util.find_spec(self.module_name)
        except (ImportError, ValueError) as error:
            return self._broken(error)
        if specification is None:
            return Capability(
                identifier=self.identifier,
                status=CapabilityStatus.UNAVAILABLE,
                reason_code=CapabilityReasonCode.MISSING_PACKAGE,
                reason=f"install the optional package providing {self.module_name}",
            )
        try:
            importlib.import_module(self.module_name)
        except (ImportError, OSError) as error:
            return self._broken(error)

        distribution = self.distribution_name or self.module_name
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            version = None
        return Capability(
            identifier=self.identifier,
            status=CapabilityStatus.AVAILABLE,
            reason_code=CapabilityReasonCode.AVAILABLE,
            reason=f"imported {self.module_name}",
            version=version,
        )

    def _broken(self, error: ImportError | OSError | ValueError) -> Capability:
        return Capability(
            identifier=self.identifier,
            status=CapabilityStatus.MISCONFIGURED,
            reason_code=CapabilityReasonCode.BROKEN_IMPORT,
            reason=f"{self.module_name} could not be imported: {error}",
        )


ModuleImporter = Callable[[str], object]

PYWIN32 = CapabilityId("pywin32")
LEGACY_METADATA = CapabilityId("legacy-metadata")
HEIF_NATIVE = CapabilityId("heif-native")


def _import_optional(
    identifier: CapabilityId,
    module_name: str,
    importer: ModuleImporter,
) -> tuple[object | None, Capability | None]:
    try:
        return importer(module_name), None
    except ModuleNotFoundError as error:
        missing_name = error.name
        if missing_name is None or not (
            module_name == missing_name or module_name.startswith(f"{missing_name}.")
        ):
            return None, Capability(
                identifier,
                CapabilityStatus.MISCONFIGURED,
                CapabilityReasonCode.BROKEN_IMPORT,
                f"{module_name} could not be imported: {error}",
            )
        return None, Capability(
            identifier,
            CapabilityStatus.UNAVAILABLE,
            CapabilityReasonCode.MISSING_PACKAGE,
            f"install the optional package providing {module_name}",
        )
    except (ImportError, OSError) as error:
        return None, Capability(
            identifier,
            CapabilityStatus.MISCONFIGURED,
            CapabilityReasonCode.BROKEN_IMPORT,
            f"{module_name} could not be imported: {error}",
        )


def _missing_callables(owner: object, names: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(name for name in names if not callable(getattr(owner, name, None)))


def _incompatible(
    identifier: CapabilityId,
    package: str,
    missing: tuple[str, ...],
) -> Capability:
    return Capability(
        identifier,
        CapabilityStatus.MISCONFIGURED,
        CapabilityReasonCode.INCOMPATIBLE_API,
        f"{package} lacks the API required by Phatch: {', '.join(missing)}",
    )


@dataclass(frozen=True, slots=True)
class Pywin32CapabilityProbe:
    platform: str = sys.platform
    importer: ModuleImporter = importlib.import_module

    def __call__(self) -> Capability:
        if self.platform != "win32":
            return Capability(
                PYWIN32,
                CapabilityStatus.UNAVAILABLE,
                CapabilityReasonCode.UNSUPPORTED_PLATFORM,
                "pywin32 COM shortcuts are available only on Windows",
            )
        module, failure = _import_optional(PYWIN32, "win32com.client", self.importer)
        if failure is not None:
            return failure
        assert module is not None
        missing = _missing_callables(module, ("Dispatch",))
        if missing:
            return _incompatible(PYWIN32, "win32com.client", missing)
        return Capability(
            PYWIN32,
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            "win32com.client exposes Dispatch; COM was not instantiated",
        )


@dataclass(frozen=True, slots=True)
class LegacyMetadataCapabilityProbe:
    importer: ModuleImporter = importlib.import_module

    def __call__(self) -> Capability:
        module, failure = _import_optional(LEGACY_METADATA, "pyexiv2", self.importer)
        if failure is not None:
            return failure
        assert module is not None
        image_type = getattr(module, "Image", None)
        required = (
            "readMetadata",
            "writeMetadata",
            "exifKeys",
            "iptcKeys",
            "getThumbnailData",
            "setThumbnailData",
            "getComment",
            "setComment",
            "_Image__getExifTag",
            "_Image__setExifTag",
            "__getitem__",
            "__setitem__",
            "__delitem__",
        )
        missing = (
            ("Image",)
            if not callable(image_type)
            else _missing_callables(image_type, required)
        )
        if missing:
            return _incompatible(LEGACY_METADATA, "pyexiv2", missing)
        version = getattr(module, "__version__", None)
        return Capability(
            LEGACY_METADATA,
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            "pyexiv2 exposes Phatch's legacy read, tag, and write API",
            version=version if isinstance(version, str) else None,
        )


@dataclass(frozen=True, slots=True)
class HeifNativeCapabilityProbe:
    importer: ModuleImporter = importlib.import_module

    def __call__(self) -> Capability:
        module, failure = _import_optional(HEIF_NATIVE, "pillow_heif", self.importer)
        if failure is not None:
            return failure
        assert module is not None
        required = ("HeifFile", "open_heif", "from_bytes", "libheif_info")
        missing = _missing_callables(module, required)
        if missing:
            return _incompatible(HEIF_NATIVE, "pillow_heif", missing)
        version = getattr(module, "__version__", None)
        return Capability(
            HEIF_NATIVE,
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            "pillow_heif exposes its native file API; "
            "Pillow codecs remain unregistered",
            version=version if isinstance(version, str) else None,
        )


def foundation_capability_registry(
    lookup: ExecutableFinder,
    runner: ProcessRunner,
    *,
    platform: str = sys.platform,
    importer: ModuleImporter = importlib.import_module,
) -> CapabilityRegistry:
    from phatch.lib.external_capability_probes import (
        BLENDER_LEGACY,
        EXIFTRAN,
        IMAGEMAGICK_6,
        JPEGTRAN,
        BlenderCapabilityProbe,
        ExiftranCapabilityProbe,
        ImageMagick6CapabilityProbe,
        JpegtranCapabilityProbe,
    )

    return CapabilityRegistry(
        (
            (IMAGEMAGICK_6, ImageMagick6CapabilityProbe(lookup, runner)),
            (JPEGTRAN, JpegtranCapabilityProbe(lookup, runner)),
            (EXIFTRAN, ExiftranCapabilityProbe(lookup, runner)),
            (BLENDER_LEGACY, BlenderCapabilityProbe(lookup, runner)),
            (PYWIN32, Pywin32CapabilityProbe(platform, importer)),
            (LEGACY_METADATA, LegacyMetadataCapabilityProbe(importer)),
            (HEIF_NATIVE, HeifNativeCapabilityProbe(importer)),
        )
    )
