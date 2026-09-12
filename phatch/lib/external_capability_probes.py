from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.lib.capability_probes import ExecutableFinder
from phatch.lib.process import Command, ProcessError, ProcessResult, ProcessRunner

IMAGEMAGICK_6 = CapabilityId("imagemagick-6")
JPEGTRAN = CapabilityId("jpegtran")
EXIFTRAN = CapabilityId("exiftran")
BLENDER_LEGACY = CapabilityId("blender-2.45-2.49")

_IMAGEMAGICK_VERSION = re.compile(
    r"^Version: ImageMagick (?P<version>(?P<major>\d+)\.\d+\.\d+(?:-\d+)?)\b"
)
_BLENDER_VERSION = re.compile(
    r"^Blender (?P<version>(?P<major>\d+)\.(?P<minor>\d+)"
    r"(?:\.\d+|[a-z])?)(?:\s|$)"
)


def _combined_output(result: ProcessResult) -> str:
    return "\n".join(part for part in (result.stdout, result.stderr) if part)


def _missing_options(output: str, options: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        option
        for option in options
        if re.search(rf"(?m)^\s*{re.escape(option)}(?:\s|,|$)", output) is None
    )


@dataclass(frozen=True, slots=True)
class _ExternalCapabilityProbe:
    lookup: ExecutableFinder
    runner: ProcessRunner

    identifier: ClassVar[CapabilityId]
    executable_name: ClassVar[str]
    arguments: ClassVar[tuple[str, ...]]
    accepted_returncodes: ClassVar[frozenset[int]] = frozenset({0})

    def __call__(self) -> Capability:
        executable = self.lookup.find(self.executable_name)
        if executable is None:
            return Capability(
                self.identifier,
                CapabilityStatus.UNAVAILABLE,
                CapabilityReasonCode.MISSING_EXECUTABLE,
                f"install {self.executable_name} or configure its directory",
            )
        command = Command(
            (str(executable), *self.arguments),
            timeout_seconds=5.0,
            accepted_returncodes=self.accepted_returncodes,
        )
        try:
            result = self.runner.run(command)
        except ProcessError as error:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                f"{self.executable_name} probe failed: {error}; verify the executable",
            )
        return self._classify(executable, result)

    def _classify(self, executable: Path, result: ProcessResult) -> Capability:
        raise NotImplementedError

    def _available(
        self,
        executable: Path,
        reason: str,
        version: str | None = None,
    ) -> Capability:
        return Capability(
            self.identifier,
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            reason,
            executable=executable,
            version=version,
        )

    def _misconfigured(
        self,
        executable: Path,
        reason_code: CapabilityReasonCode,
        reason: str,
        version: str | None = None,
    ) -> Capability:
        return Capability(
            self.identifier,
            CapabilityStatus.MISCONFIGURED,
            reason_code,
            reason,
            executable=executable,
            version=version,
        )


class ImageMagick6CapabilityProbe(_ExternalCapabilityProbe):
    identifier = IMAGEMAGICK_6
    executable_name = "convert"
    arguments = ("-version",)

    def _classify(self, executable: Path, result: ProcessResult) -> Capability:
        match = _IMAGEMAGICK_VERSION.match(_combined_output(result))
        if match is None:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                "convert did not identify itself as ImageMagick; install ImageMagick 6",
            )
        version = match.group("version")
        if match.group("major") != "6":
            return self._misconfigured(
                executable,
                CapabilityReasonCode.UNSUPPORTED_VERSION,
                f"ImageMagick {version} is unsupported; Phatch requires ImageMagick 6",
                version,
            )
        return self._available(
            executable,
            "ImageMagick 6 legacy convert dialect is available",
            version,
        )


class JpegtranCapabilityProbe(_ExternalCapabilityProbe):
    identifier = JPEGTRAN
    executable_name = "jpegtran"
    arguments = ("-help",)
    required_options = (
        "-copy",
        "-crop",
        "-flip",
        "-grayscale",
        "-outfile",
        "-rotate",
        "-transpose",
        "-transverse",
    )

    def _classify(self, executable: Path, result: ProcessResult) -> Capability:
        output = _combined_output(result)
        if re.search(r"(?im)^usage:\s+jpegtran\b", output) is None:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                "jpegtran help identity is missing; verify the executable",
            )
        missing = _missing_options(output, self.required_options)
        if missing:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                f"jpegtran lacks required options: {', '.join(missing)}",
            )
        return self._available(
            executable,
            "jpegtran supports required transforms and file output",
        )


class ExiftranCapabilityProbe(_ExternalCapabilityProbe):
    identifier = EXIFTRAN
    executable_name = "exiftran"
    arguments = ("-h",)
    accepted_returncodes = frozenset({0, 1})
    required_options = (
        "-i",
        "-o",
        "-a",
        "-9",
        "-1",
        "-2",
        "-F",
        "-f",
        "-g",
        "-t",
        "-T",
        "-ni",
        "-nt",
        "-no",
        "-p",
    )

    def _classify(self, executable: Path, result: ProcessResult) -> Capability:
        output = _combined_output(result)
        if re.search(r"(?im)^usage:\s+exiftran\b", output) is None:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                "exiftran did not return documented help; verify the executable",
            )
        missing = _missing_options(output, self.required_options)
        if missing:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                f"exiftran lacks required options: {', '.join(missing)}",
            )
        return self._available(
            executable,
            "exiftran supports Phatch's metadata-preserving transforms",
        )


class BlenderCapabilityProbe(_ExternalCapabilityProbe):
    identifier = BLENDER_LEGACY
    executable_name = "blender"
    arguments = ("-v",)

    def _classify(self, executable: Path, result: ProcessResult) -> Capability:
        match = _BLENDER_VERSION.match(_combined_output(result))
        if match is None:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.PROBE_FAILED,
                "blender version output is malformed; "
                "expected an anchored Blender version",
            )
        version = match.group("version")
        major = int(match.group("major"))
        minor = int(match.group("minor"))
        if major != 2 or not 45 <= minor <= 49:
            return self._misconfigured(
                executable,
                CapabilityReasonCode.UNSUPPORTED_VERSION,
                f"Blender {version} is unsupported; Phatch requires 2.45 through 2.49",
                version,
            )
        return self._available(
            executable,
            "supported legacy Blender renderer is available",
            version,
        )
