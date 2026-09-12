from __future__ import annotations

from types import SimpleNamespace

import pytest

from phatch.lib.capabilities import CapabilityReasonCode, CapabilityStatus
from phatch.lib.capability_probes import (
    HEIF_NATIVE,
    LEGACY_METADATA,
    PYWIN32,
    HeifNativeCapabilityProbe,
    LegacyMetadataCapabilityProbe,
    Pywin32CapabilityProbe,
    foundation_capability_registry,
)
from phatch.lib.external_capability_probes import (
    BLENDER_LEGACY,
    EXIFTRAN,
    IMAGEMAGICK_6,
    JPEGTRAN,
)


class StubImporter:
    def __init__(self, result: object | Exception) -> None:
        self.result = result
        self.names: list[str] = []

    def __call__(self, name: str) -> object:
        self.names.append(name)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_foundation_registry_wires_every_concrete_probe_lazily() -> None:
    class UnusedLookup:
        def find(self, name: str):
            raise AssertionError(f"construction must not find {name}")

    class UnusedRunner:
        def run(self, command, *, cancelled=None):
            raise AssertionError(f"construction must not run {command}")

    importer = StubImporter(AssertionError("construction must not import"))
    registry = foundation_capability_registry(
        UnusedLookup(), UnusedRunner(), platform="win32", importer=importer
    )

    assert tuple(identifier for identifier, _probe in registry.probes) == (
        IMAGEMAGICK_6,
        JPEGTRAN,
        EXIFTRAN,
        BLENDER_LEGACY,
        PYWIN32,
        LEGACY_METADATA,
        HEIF_NATIVE,
    )
    assert importer.names == []


def test_pywin32_probe_is_lazy_platform_specific_and_never_dispatches() -> None:
    dispatch_calls: list[str] = []
    module = SimpleNamespace(
        Dispatch=lambda name: dispatch_calls.append(name) or object()
    )
    importer = StubImporter(module)
    probe = Pywin32CapabilityProbe(platform="win32", importer=importer)
    assert importer.names == []

    result = probe()

    assert result.status is CapabilityStatus.AVAILABLE
    assert importer.names == ["win32com.client"]
    assert dispatch_calls == []

    non_windows_importer = StubImporter(module)
    unsupported = Pywin32CapabilityProbe(
        platform="darwin", importer=non_windows_importer
    )()
    assert unsupported.status is CapabilityStatus.UNAVAILABLE
    assert unsupported.reason_code is CapabilityReasonCode.UNSUPPORTED_PLATFORM
    assert non_windows_importer.names == []


class LegacyImage:
    def __init__(self, filename: str) -> None:
        raise AssertionError(f"probe must not open {filename}")

    def readMetadata(self) -> None: ...

    def writeMetadata(self) -> None: ...

    def exifKeys(self) -> list[str]: ...

    def iptcKeys(self) -> list[str]: ...

    def getThumbnailData(self) -> bytes: ...

    def setThumbnailData(self, data: bytes) -> None: ...

    def getComment(self) -> str: ...

    def setComment(self, comment: str) -> None: ...

    def _Image__getExifTag(self, key: str) -> tuple[str, object]: ...

    def _Image__setExifTag(self, key: str, value: object) -> None: ...

    def __getitem__(self, key: str) -> object: ...

    def __setitem__(self, key: str, value: object) -> None: ...

    def __delitem__(self, key: str) -> None: ...


def test_metadata_probe_requires_phatch_legacy_api_without_opening_files() -> None:
    importer = StubImporter(SimpleNamespace(Image=LegacyImage, __version__="0.3.2"))
    probe = LegacyMetadataCapabilityProbe(importer=importer)
    assert importer.names == []

    result = probe()

    assert result.status is CapabilityStatus.AVAILABLE
    assert result.version == "0.3.2"
    assert importer.names == ["pyexiv2"]

    class ModernImage:
        def read_exif(self) -> dict[str, str]:
            return {}

        def modify_exif(self, values: dict[str, str]) -> None: ...

    incompatible = LegacyMetadataCapabilityProbe(
        importer=StubImporter(SimpleNamespace(Image=ModernImage))
    )()
    assert incompatible.status is CapabilityStatus.MISCONFIGURED
    assert incompatible.reason_code is CapabilityReasonCode.INCOMPATIBLE_API
    assert "readMetadata" in incompatible.reason

    incomplete_image = type(
        "IncompleteImage",
        (LegacyImage,),
        {"getThumbnailData": None},
    )
    incomplete = LegacyMetadataCapabilityProbe(
        importer=StubImporter(SimpleNamespace(Image=incomplete_image))
    )()
    assert incomplete.status is CapabilityStatus.MISCONFIGURED
    assert "getThumbnailData" in incomplete.reason


def test_heif_probe_requires_native_file_api_without_registering_codecs() -> None:
    registration_calls: list[bool] = []
    module = SimpleNamespace(
        HeifFile=type("HeifFile", (), {}),
        open_heif=lambda source: source,
        from_bytes=lambda mode, size, data: (mode, size, data),
        libheif_info=lambda: {"version": "1.19.8"},
        register_heif_opener=lambda: registration_calls.append(True),
        __version__="1.1.1",
    )
    importer = StubImporter(module)
    probe = HeifNativeCapabilityProbe(importer=importer)
    assert importer.names == []

    result = probe()

    assert result.status is CapabilityStatus.AVAILABLE
    assert result.version == "1.1.1"
    assert importer.names == ["pillow_heif"]
    assert registration_calls == []

    incompatible = HeifNativeCapabilityProbe(
        importer=StubImporter(SimpleNamespace(open_heif=lambda source: source))
    )()
    assert incompatible.status is CapabilityStatus.MISCONFIGURED
    assert incompatible.reason_code is CapabilityReasonCode.INCOMPATIBLE_API
    assert "HeifFile" in incompatible.reason


@pytest.mark.parametrize(
    ("probe_type", "module_name"),
    [
        (Pywin32CapabilityProbe, "win32com.client"),
        (LegacyMetadataCapabilityProbe, "pyexiv2"),
        (HeifNativeCapabilityProbe, "pillow_heif"),
    ],
)
def test_python_api_probes_distinguish_missing_broken_and_incompatible(
    probe_type,
    module_name: str,
) -> None:
    options = {"platform": "win32"} if probe_type is Pywin32CapabilityProbe else {}
    missing = probe_type(
        importer=StubImporter(
            ModuleNotFoundError("optional package missing", name=module_name)
        ),
        **options,
    )()
    assert missing.status is CapabilityStatus.UNAVAILABLE
    assert missing.reason_code is CapabilityReasonCode.MISSING_PACKAGE

    broken = probe_type(
        importer=StubImporter(ImportError("native load failed")), **options
    )()
    assert broken.status is CapabilityStatus.MISCONFIGURED
    assert broken.reason_code is CapabilityReasonCode.BROKEN_IMPORT

    incompatible = probe_type(importer=StubImporter(SimpleNamespace()), **options)()
    assert incompatible.status is CapabilityStatus.MISCONFIGURED
    assert incompatible.reason_code is CapabilityReasonCode.INCOMPATIBLE_API


def test_python_api_probe_treats_missing_parent_package_as_missing() -> None:
    result = Pywin32CapabilityProbe(
        platform="win32",
        importer=StubImporter(
            ModuleNotFoundError("parent package missing", name="win32com")
        ),
    )()

    assert result.status is CapabilityStatus.UNAVAILABLE
    assert result.reason_code is CapabilityReasonCode.MISSING_PACKAGE


@pytest.mark.parametrize(
    "probe_type",
    [Pywin32CapabilityProbe, LegacyMetadataCapabilityProbe, HeifNativeCapabilityProbe],
)
def test_python_api_probes_treat_missing_transitive_import_as_broken(
    probe_type,
) -> None:
    options = {"platform": "win32"} if probe_type is Pywin32CapabilityProbe else {}
    result = probe_type(
        importer=StubImporter(
            ModuleNotFoundError("native dependency missing", name="native_dependency")
        ),
        **options,
    )()

    assert result.status is CapabilityStatus.MISCONFIGURED
    assert result.reason_code is CapabilityReasonCode.BROKEN_IMPORT
