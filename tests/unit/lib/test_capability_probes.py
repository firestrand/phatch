from __future__ import annotations

from pathlib import Path

import pytest

from phatch.lib import capability_probes
from phatch.lib.capabilities import CapabilityId, CapabilityReasonCode, CapabilityStatus
from phatch.lib.capability_probes import (
    ExecutableCapabilityProbe,
    ModuleCapabilityProbe,
)


class StubLookup:
    def __init__(self, path: Path | None) -> None:
        self.path = path
        self.calls = 0

    def find(self, name: str) -> Path | None:
        self.calls += 1
        return self.path


def test_executable_probe_is_lazy_and_reports_available_path(tmp_path: Path) -> None:
    executable = tmp_path / "tool"
    lookup = StubLookup(executable)
    probe = ExecutableCapabilityProbe(CapabilityId("tool"), "tool", lookup)

    assert lookup.calls == 0
    result = probe()
    assert result.status is CapabilityStatus.AVAILABLE
    assert result.reason_code is CapabilityReasonCode.AVAILABLE
    assert result.executable == executable
    assert lookup.calls == 1


def test_executable_probe_reports_missing_tool() -> None:
    result = ExecutableCapabilityProbe(CapabilityId("tool"), "tool", StubLookup(None))()

    assert result.status is CapabilityStatus.UNAVAILABLE
    assert result.reason_code is CapabilityReasonCode.MISSING_EXECUTABLE


def test_module_probe_imports_only_when_called(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        capability_probes.importlib.util,
        "find_spec",
        lambda name: calls.append(f"find:{name}") or object(),
    )
    monkeypatch.setattr(
        capability_probes.importlib,
        "import_module",
        lambda name: calls.append(f"import:{name}"),
    )
    monkeypatch.setattr(
        capability_probes.importlib.metadata,
        "version",
        lambda name: "1.2.3",
    )
    probe = ModuleCapabilityProbe(CapabilityId("codec"), "optional_codec")

    assert calls == []
    result = probe()
    assert calls == ["find:optional_codec", "import:optional_codec"]
    assert result.status is CapabilityStatus.AVAILABLE
    assert result.version == "1.2.3"


def test_module_probe_distinguishes_missing_and_broken_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capability_probes.importlib.util, "find_spec", lambda name: None
    )
    missing = ModuleCapabilityProbe(CapabilityId("codec"), "optional_codec")()
    assert missing.status is CapabilityStatus.UNAVAILABLE
    assert missing.reason_code is CapabilityReasonCode.MISSING_PACKAGE

    monkeypatch.setattr(
        capability_probes.importlib.util, "find_spec", lambda name: object()
    )

    def broken_import(name: str) -> None:
        raise ImportError("native library is unavailable")

    monkeypatch.setattr(capability_probes.importlib, "import_module", broken_import)
    broken = ModuleCapabilityProbe(CapabilityId("codec"), "optional_codec")()
    assert broken.status is CapabilityStatus.MISCONFIGURED
    assert broken.reason_code is CapabilityReasonCode.BROKEN_IMPORT


def test_module_probe_reports_broken_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_discovery(name: str) -> None:
        raise ValueError(name)

    monkeypatch.setattr(capability_probes.importlib.util, "find_spec", broken_discovery)
    result = ModuleCapabilityProbe(CapabilityId("codec"), "optional_codec")()

    assert result.status is CapabilityStatus.MISCONFIGURED
    assert result.reason_code is CapabilityReasonCode.BROKEN_IMPORT


def test_module_probe_allows_missing_distribution_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        capability_probes.importlib.util, "find_spec", lambda name: object()
    )
    monkeypatch.setattr(capability_probes.importlib, "import_module", lambda name: None)

    def missing_version(name: str) -> str:
        raise __import__("importlib.metadata").metadata.PackageNotFoundError(name)

    monkeypatch.setattr(
        capability_probes.importlib.metadata, "version", missing_version
    )
    result = ModuleCapabilityProbe(CapabilityId("codec"), "optional_codec")()

    assert result.status is CapabilityStatus.AVAILABLE
    assert result.version is None
