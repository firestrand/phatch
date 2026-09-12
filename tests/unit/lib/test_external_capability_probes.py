from __future__ import annotations

from pathlib import Path

import pytest

from phatch.lib.capabilities import CapabilityReasonCode, CapabilityStatus
from phatch.lib.external_capability_probes import (
    BlenderCapabilityProbe,
    ExiftranCapabilityProbe,
    ImageMagick6CapabilityProbe,
    JpegtranCapabilityProbe,
)
from phatch.lib.process import (
    Command,
    ProcessExitError,
    ProcessLaunchError,
    ProcessResult,
    ProcessTimeoutError,
)


class StubLookup:
    def __init__(self, executable: Path | None) -> None:
        self.executable = executable
        self.names: list[str] = []

    def find(self, name: str) -> Path | None:
        self.names.append(name)
        return self.executable


class StubRunner:
    def __init__(
        self,
        response: tuple[int, str, str] | Exception,
    ) -> None:
        self.response = response
        self.commands: list[Command] = []

    def run(self, command: Command, *, cancelled=None) -> ProcessResult:
        self.commands.append(command)
        if isinstance(self.response, Exception):
            raise self.response
        returncode, stdout, stderr = self.response
        return ProcessResult(command, returncode, stdout, stderr)


def make_probe(probe_type, response, *, present: bool = True):
    executable = Path("/opt/phatch/tool") if present else None
    lookup = StubLookup(executable)
    runner = StubRunner(response)
    return probe_type(lookup, runner), lookup, runner


JPEGTRAN_HELP = """usage: jpegtran [switches] [inputfile]
 -copy none
 -crop WxH+X+Y
 -flip horizontal
 -grayscale
 -outfile name
 -rotate 90
 -transpose
 -transverse
"""

EXIFTRAN_HELP = """usage: exiftran [options] file1 file2
 -i inplace
 -o file output
 -a automatic
 -9 rotate 90
 -1 rotate 180
 -2 rotate 270
 -F flip horizontal
 -f flip vertical
 -g regenerate thumbnail
 -t transpose
 -T transverse
 -ni no image update
 -nt no thumbnail update
 -no no orientation update
 -p preserve timestamp
"""


def test_external_probes_are_lazy_and_use_bounded_exact_commands() -> None:
    cases = (
        (ImageMagick6CapabilityProbe, "convert", ("-version",), (0,)),
        (JpegtranCapabilityProbe, "jpegtran", ("-help",), (0,)),
        (ExiftranCapabilityProbe, "exiftran", ("-h",), (0, 1)),
        (BlenderCapabilityProbe, "blender", ("-v",), (0,)),
    )
    outputs = (
        "Version: ImageMagick 6.9.12-93 Q16 x86_64\n",
        JPEGTRAN_HELP,
        EXIFTRAN_HELP,
        "Blender 2.49b\n",
    )

    for (probe_type, name, arguments, returncodes), output in zip(
        cases, outputs, strict=True
    ):
        probe, lookup, runner = make_probe(probe_type, (0, output, ""))
        assert lookup.names == []
        assert runner.commands == []

        result = probe()

        assert result.status is CapabilityStatus.AVAILABLE
        assert lookup.names == [name]
        assert runner.commands[0].argv == ("/opt/phatch/tool", *arguments)
        assert runner.commands[0].timeout_seconds == 5.0
        assert runner.commands[0].accepted_returncodes == frozenset(returncodes)


@pytest.mark.parametrize(
    ("output", "status", "reason_code", "version"),
    [
        (
            "Version: ImageMagick 6.9.12-93 Q16 x86_64\n",
            CapabilityStatus.AVAILABLE,
            CapabilityReasonCode.AVAILABLE,
            "6.9.12-93",
        ),
        (
            "Version: ImageMagick 7.1.1-38 Q16 x86_64\n",
            CapabilityStatus.MISCONFIGURED,
            CapabilityReasonCode.UNSUPPORTED_VERSION,
            "7.1.1-38",
        ),
        (
            "Microsoft Windows [Version 10.0]\n",
            CapabilityStatus.MISCONFIGURED,
            CapabilityReasonCode.PROBE_FAILED,
            None,
        ),
    ],
)
def test_imagemagick_requires_version_6_identity(
    output: str,
    status: CapabilityStatus,
    reason_code: CapabilityReasonCode,
    version: str | None,
) -> None:
    probe, _lookup, _runner = make_probe(ImageMagick6CapabilityProbe, (0, output, ""))

    result = probe()

    assert result.status is status
    assert result.reason_code is reason_code
    assert result.version == version


@pytest.mark.parametrize(
    ("probe_type", "output", "missing_option"),
    [
        (JpegtranCapabilityProbe, JPEGTRAN_HELP, "-outfile"),
        (ExiftranCapabilityProbe, EXIFTRAN_HELP, "-no"),
    ],
)
def test_lossless_jpeg_probes_require_identity_and_every_consumed_option(
    probe_type,
    output: str,
    missing_option: str,
) -> None:
    available, _lookup, _runner = make_probe(probe_type, (0, output, ""))
    assert available().status is CapabilityStatus.AVAILABLE

    malformed, _lookup, _runner = make_probe(
        probe_type, (0, output.replace(missing_option, "-missing"), "")
    )
    result = malformed()
    assert result.status is CapabilityStatus.MISCONFIGURED
    assert result.reason_code is CapabilityReasonCode.PROBE_FAILED
    assert missing_option in result.reason


def test_exiftran_accepts_exit_one_only_for_documented_help() -> None:
    documented, _lookup, _runner = make_probe(
        ExiftranCapabilityProbe, (1, "", EXIFTRAN_HELP)
    )
    assert documented().status is CapabilityStatus.AVAILABLE

    malformed, _lookup, _runner = make_probe(
        ExiftranCapabilityProbe, (1, "", "exiftran failed")
    )
    assert malformed().status is CapabilityStatus.MISCONFIGURED


@pytest.mark.parametrize("version", ["2.45", "2.45a", "2.47.3", "2.49b"])
def test_blender_accepts_only_supported_anchored_versions(version: str) -> None:
    probe, _lookup, _runner = make_probe(
        BlenderCapabilityProbe, (0, f"Blender {version}\n", "")
    )
    result = probe()
    assert result.status is CapabilityStatus.AVAILABLE
    assert result.version == version


@pytest.mark.parametrize(
    ("output", "reason_code"),
    [
        ("Blender 2.44\n", CapabilityReasonCode.UNSUPPORTED_VERSION),
        ("Blender 2.490\n", CapabilityReasonCode.UNSUPPORTED_VERSION),
        ("Blender 3.6.1\n", CapabilityReasonCode.UNSUPPORTED_VERSION),
        ("wrapper reports Blender 2.49\n", CapabilityReasonCode.PROBE_FAILED),
        ("not blender\n", CapabilityReasonCode.PROBE_FAILED),
    ],
)
def test_blender_rejects_unsupported_or_unanchored_identity(
    output: str, reason_code: CapabilityReasonCode
) -> None:
    probe, _lookup, _runner = make_probe(BlenderCapabilityProbe, (0, output, ""))
    result = probe()
    assert result.status is CapabilityStatus.MISCONFIGURED
    assert result.reason_code is reason_code


@pytest.mark.parametrize(
    "probe_type",
    [
        ImageMagick6CapabilityProbe,
        JpegtranCapabilityProbe,
        ExiftranCapabilityProbe,
        BlenderCapabilityProbe,
    ],
)
def test_external_probes_distinguish_missing_from_present_but_unusable(
    probe_type,
) -> None:
    missing, _lookup, runner = make_probe(probe_type, (0, "", ""), present=False)
    missing_result = missing()
    assert missing_result.status is CapabilityStatus.UNAVAILABLE
    assert missing_result.reason_code is CapabilityReasonCode.MISSING_EXECUTABLE
    assert runner.commands == []

    placeholder = Command(("tool",), timeout_seconds=5.0)
    failures = (
        ProcessExitError(placeholder, 2, "", "bad status"),
        ProcessTimeoutError(placeholder, 5.0),
        ProcessLaunchError(placeholder, "access denied", 13),
    )
    for failure in failures:
        unusable, _lookup, _runner = make_probe(probe_type, failure)
        result = unusable()
        assert result.status is CapabilityStatus.MISCONFIGURED
        assert result.reason_code is CapabilityReasonCode.PROBE_FAILED
