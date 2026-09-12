from pathlib import Path

from phatch.lib.capabilities import (
    Capability,
    CapabilityId,
    CapabilityReasonCode,
    CapabilityStatus,
)
from phatch.services.action_schema import ActionDocument
from phatch.services.preflight import PreflightRequest, PreflightService


def test_preflight_reports_outputs_conflicts_capabilities_and_work(
    tmp_path: Path,
) -> None:
    # Given
    source = tmp_path / "source image.png"
    source.write_bytes(b"input")
    destination = tmp_path / "dest"
    output = destination / source.name
    destination.mkdir()
    output.write_bytes(b"old")
    document = ActionDocument.from_values(
        "plan",
        (
            ("imagemagick", (("enabled", "yes"),)),
            (
                "save",
                (
                    ("in", str(destination)),
                    ("file_name", "<filename>"),
                    ("as", "<type>"),
                    ("enabled", "yes"),
                ),
            ),
        ),
    )
    unavailable = Capability(
        CapabilityId("imagemagick-6"),
        CapabilityStatus.UNAVAILABLE,
        CapabilityReasonCode.MISSING_EXECUTABLE,
        "not installed",
    )

    # When
    result = PreflightService().build(
        PreflightRequest(document, (source,), (unavailable,))
    )

    # Then
    assert result.inputs == (source.resolve(),)
    assert result.outputs == (output.resolve(),)
    assert result.conflicts == (output.resolve(),)
    assert result.unavailable_capabilities == (unavailable,)
    assert result.estimated_work == 2


def test_preflight_never_creates_destination_or_changes_inputs(tmp_path: Path) -> None:
    # Given
    source = tmp_path / "input.png"
    source.write_bytes(b"unchanged")
    destination = tmp_path / "missing" / "nested"
    document = ActionDocument.from_values(
        "readonly",
        (
            (
                "save",
                (
                    ("in", str(destination)),
                    ("file_name", "copy"),
                    ("as", "png"),
                ),
            ),
        ),
    )

    # When
    result = PreflightService().build(PreflightRequest(document, (source,), ()))

    # Then
    assert result.outputs == ((destination / "copy.png").resolve(),)
    assert source.read_bytes() == b"unchanged"
    assert not destination.exists()


def test_preflight_discovers_direct_and_recursive_files(tmp_path: Path) -> None:
    direct = tmp_path / "direct.png"
    nested = tmp_path / "nested" / "nested.png"
    direct.write_bytes(b"direct")
    nested.parent.mkdir()
    nested.write_bytes(b"nested")
    document = ActionDocument.from_values("discover", ())

    shallow = PreflightService().build(PreflightRequest(document, (tmp_path,), ()))
    recursive = PreflightService().build(
        PreflightRequest(
            document,
            (tmp_path, direct),
            (),
            recursive=True,
        )
    )

    assert shallow.inputs == (direct.resolve(),)
    assert recursive.inputs == (direct.resolve(), direct.resolve(), nested.resolve())
    assert recursive.outputs == ()


def test_preflight_reports_unsafe_action_forms(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    document = ActionDocument.from_values(
        "unsafe",
        (
            ("geek", ()),
            ("save", (("file_name", "../escape"),)),
            ("scale", (("width", "=danger"),)),
        ),
    )

    result = PreflightService().build(PreflightRequest(document, (source,), ()))

    assert result.unsafe_operations == (
        "geek",
        "save_path_escape",
        "unsafe_expression:scale",
    )


def test_preflight_appends_output_extension_without_replacing_filename_suffix(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    destination = tmp_path / "output"
    document = ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("in", str(destination)),
                    ("file_name", "<filename>.thumb"),
                    ("as", "<type>"),
                ),
            ),
        ),
    )

    result = PreflightService().build(PreflightRequest(document, (source,), ()))

    assert result.outputs == ((destination / "source.thumb.png").resolve(),)


def test_preflight_preserves_explicit_suffix_and_empty_output_type(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    destination = tmp_path / "output"
    explicit = ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("in", str(destination)),
                    ("file_name", "<filename>.png"),
                    ("as", ".png"),
                ),
            ),
        ),
    )
    empty = ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("in", str(destination)),
                    ("file_name", "<filename>"),
                    ("as", ""),
                ),
            ),
        ),
    )

    explicit_result = PreflightService().build(
        PreflightRequest(explicit, (source,), ())
    )
    empty_result = PreflightService().build(PreflightRequest(empty, (source,), ()))

    assert explicit_result.outputs == ((destination / "source.png").resolve(),)
    assert empty_result.outputs == ((destination / "source").resolve(),)


def test_preflight_preserves_recursive_subfolder_and_detects_duplicate_outputs(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "inputs"
    nested = source_root / "nested" / "source.png"
    nested.parent.mkdir(parents=True)
    nested.write_bytes(b"input")
    destination = tmp_path / "output"
    document = ActionDocument.from_values(
        "",
        (
            (
                "save",
                (
                    ("in", f"{destination}/<subfolder>"),
                    ("file_name", "<filename>"),
                    ("as", "<type>"),
                ),
            ),
        ),
    )

    result = PreflightService().build(
        PreflightRequest(document, (source_root, source_root), (), recursive=True)
    )
    expected = (destination / "nested" / "source.png").resolve()

    assert result.outputs == (expected, expected)
    assert result.conflicts == (expected, expected)


def test_preflight_rejects_unregistered_output_codec(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    source.write_bytes(b"input")
    destination = tmp_path / "output"
    document = ActionDocument.from_values(
        "",
        (("save", (("in", str(destination)), ("as", "unregistered"))),),
    )

    result = PreflightService().build(PreflightRequest(document, (source,), ()))

    assert tuple(
        str(capability.identifier) for capability in result.unavailable_capabilities
    ) == ("image-codec-write:unregistered",)
