from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from phatch.lib import system
from phatch.lib.capabilities import Capability, CapabilityId, CapabilityProbe
from phatch.lib.capability_probes import ExecutableFinder
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
from phatch.lib.process import ProcessRunner
from phatch.lib.subprocess_runner import StdlibProcessRunner


class ExternalCapabilityError(RuntimeError):
    def __init__(self, capability: Capability) -> None:
        super().__init__()
        self.capability = capability

    def __str__(self) -> str:
        return self.capability.reason


class _SystemExecutableLookup:
    @staticmethod
    def find(name: str) -> Path | None:
        executable = system.find_exe(name, quote=False)
        return None if executable is None else Path(executable)


@dataclass(frozen=True, slots=True)
class ExternalTools:
    runner: ProcessRunner
    probes: tuple[tuple[CapabilityId, CapabilityProbe], ...]

    def require(self, identifier: CapabilityId) -> Capability:
        for registered, probe in self.probes:
            if registered == identifier:
                capability = probe()
                if not capability.available or capability.executable is None:
                    raise ExternalCapabilityError(capability)
                return capability
        raise LookupError(identifier)

    def executable(self, identifier: CapabilityId) -> Path:
        executable = self.require(identifier).executable
        assert executable is not None
        return executable


def compose_external_tools(
    lookup: ExecutableFinder,
    runner: ProcessRunner,
) -> ExternalTools:
    return ExternalTools(
        runner=runner,
        probes=(
            (IMAGEMAGICK_6, ImageMagick6CapabilityProbe(lookup, runner)),
            (JPEGTRAN, JpegtranCapabilityProbe(lookup, runner)),
            (EXIFTRAN, ExiftranCapabilityProbe(lookup, runner)),
            (BLENDER_LEGACY, BlenderCapabilityProbe(lookup, runner)),
        ),
    )


def default_external_tools() -> ExternalTools:
    runner = StdlibProcessRunner()
    return compose_external_tools(_SystemExecutableLookup(), runner)
