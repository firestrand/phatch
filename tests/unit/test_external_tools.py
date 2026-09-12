from __future__ import annotations

from pathlib import Path

import pytest

from phatch import external_tools
from phatch.external_tools import ExternalCapabilityError, ExternalTools
from phatch.lib import system
from phatch.lib.capabilities import (
    Capability,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.lib.external_capability_probes import EXIFTRAN, IMAGEMAGICK_6, JPEGTRAN
from phatch.lib.process import ProcessResult


class NeverRunner:
    def run(self, command, *, cancelled=None):
        raise AssertionError("runner must not execute while composing dependencies")


class ImageMagickVersionRunner:
    def run(self, command, *, cancelled=None):
        return ProcessResult(
            command,
            0,
            "Version: ImageMagick 6.9.12-93 Q16 x86_64\n",
            "",
        )


def available(identifier, executable: str) -> Capability:
    return Capability(
        identifier,
        CapabilityStatus.AVAILABLE,
        CapabilityReasonCode.AVAILABLE,
        "test capability",
        executable=Path(executable),
    )


def test_external_tools_composition_is_lazy_and_probes_only_requested_tool() -> None:
    calls: list[str] = []
    tools = ExternalTools(
        runner=NeverRunner(),
        probes=(
            (
                EXIFTRAN,
                lambda: calls.append("exiftran") or available(EXIFTRAN, "/exiftran"),
            ),
            (
                JPEGTRAN,
                lambda: calls.append("jpegtran") or available(JPEGTRAN, "/jpegtran"),
            ),
        ),
    )

    assert calls == []
    assert tools.require(EXIFTRAN).executable == Path("/exiftran")
    assert calls == ["exiftran"]


def test_external_tools_rejects_unavailable_and_unknown_capabilities() -> None:
    unavailable = Capability(
        EXIFTRAN,
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "missing",
    )
    tools = ExternalTools(NeverRunner(), ((EXIFTRAN, lambda: unavailable),))

    with pytest.raises(ExternalCapabilityError, match="missing"):
        tools.executable(EXIFTRAN)
    with pytest.raises(LookupError):
        tools.require(JPEGTRAN)


def test_default_external_tools_preserves_raw_spaced_executable_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tool_directory = tmp_path / "configured tools"
    tool_directory.mkdir()
    executable = tool_directory / ("convert.exe" if system.WINDOWS else "convert")
    executable.write_text("probe fixture", encoding="utf-8")
    executable.chmod(0o755)
    runner = ImageMagickVersionRunner()
    monkeypatch.setattr(external_tools, "StdlibProcessRunner", lambda: runner)

    tools = external_tools.default_external_tools()
    monkeypatch.setattr(system, "BIN", [tool_directory])
    monkeypatch.setenv("PATH", "")

    capability = tools.require(IMAGEMAGICK_6)
    executable_path = capability.executable

    assert executable_path is not None
    assert executable_path == executable.resolve()
    assert executable_path.exists()
    assert '"' not in str(executable_path)
    assert "'" not in str(executable_path)
