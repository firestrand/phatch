from __future__ import annotations

from pathlib import Path, PureWindowsPath

import pytest

from phatch.core.file_references import FileReferenceError, parse_file_reference
from phatch.core.user_paths import HostPlatform


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("photos/image.jpg", Path("photos/image.jpg")),
        ("file:///tmp/a%20b-%E2%98%83.jpg", Path("/tmp/a b-☃.jpg")),
        ("file://localhost/tmp/image.jpg", Path("/tmp/image.jpg")),
    ],
)
def test_posix_file_references(reference: str, expected: Path) -> None:
    assert parse_file_reference(reference, HostPlatform.LINUX) == expected


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("C:\\Photos\\image.jpg", PureWindowsPath("C:/Photos/image.jpg")),
        ("file:///C:/Photos/a%20b.jpg", PureWindowsPath("C:/Photos/a b.jpg")),
        (
            "file://server/share/%E9%9B%AA.jpg",
            PureWindowsPath("//server/share/雪.jpg"),
        ),
        (
            "file:////server/share/history.jpg",
            PureWindowsPath("//server/share/history.jpg"),
        ),
    ],
)
def test_windows_drive_and_unc_file_references(
    reference: str, expected: PureWindowsPath
) -> None:
    assert parse_file_reference(reference, HostPlatform.WINDOWS) == expected


def test_file_uri_converts_only_the_validated_path_component() -> None:
    # Given
    converted_components: list[str] = []

    def convert(component: str) -> str:
        converted_components.append(component)
        return component.replace("%20", " ")

    # When
    result = parse_file_reference(
        "file:///tmp/holiday%20photo.jpg", HostPlatform.LINUX, convert
    )

    # Then
    assert result == Path("/tmp/holiday photo.jpg")
    assert converted_components == ["/tmp/holiday%20photo.jpg"]


@pytest.mark.parametrize(
    "reference",
    [
        "https://example.test/a.jpg",
        "file:",
        "file://server",
        "file:///tmp/a?query",
        "file:///tmp/a#fragment",
        "file://user@localhost/tmp/a",
        "file://localhost:80/tmp/a",
        "file:///tmp/%ZZ",
        "file:///tmp/%FF",
        "file:///tmp/a%00b",
        "file:///tmp/a%0Ab",
        "file://./share/a",
        "file://%6Cocalhost/tmp/a",
        "file://server%00/share/a",
    ],
)
def test_malformed_or_unsupported_file_references_are_rejected(reference: str) -> None:
    with pytest.raises(FileReferenceError):
        parse_file_reference(reference, HostPlatform.LINUX)


@pytest.mark.parametrize(
    "reference",
    ["", "bad\npath", "file://server/", "file:////server", "file:///relative"],
)
def test_windows_malformed_file_references_are_rejected(reference: str) -> None:
    with pytest.raises(FileReferenceError):
        parse_file_reference(reference, HostPlatform.WINDOWS)


def test_malformed_uri_is_wrapped_as_typed_error() -> None:
    with pytest.raises(FileReferenceError, match="malformed URI") as caught:
        parse_file_reference("file://[invalid", HostPlatform.LINUX)

    assert str(caught.value).startswith("invalid file reference")


def test_windows_relative_path_remains_a_windows_path() -> None:
    assert parse_file_reference(
        "photos/image.jpg", HostPlatform.WINDOWS
    ) == PureWindowsPath("photos/image.jpg")


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows integration")
def test_windows_native_file_uri_returns_concrete_path() -> None:
    result = parse_file_reference("file:///C:/Temp/image.jpg", HostPlatform.WINDOWS)
    assert isinstance(result, Path)


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows integration")
def test_windows_native_unc_file_uri_returns_concrete_path() -> None:
    result = parse_file_reference("file://server/share/image.jpg", HostPlatform.WINDOWS)
    assert isinstance(result, Path)
