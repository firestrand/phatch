from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Final
from urllib.parse import unquote_to_bytes, urlsplit
from urllib.request import url2pathname

from .user_paths import HostPlatform

MALFORMED_ESCAPE: Final = re.compile(r"%(?![0-9A-Fa-f]{2})")
WINDOWS_DRIVE: Final = re.compile(r"^[A-Za-z]:[\\/]")
URI_AUTHORITY: Final = re.compile(r"^[A-Za-z0-9._-]+$")
PathConverter = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class FileReferenceError(ValueError):
    reference: str
    reason: str

    def __str__(self) -> str:
        return f"invalid file reference ({self.reason}): {self.reference!r}"


def _decoded_component(reference: str, component: str) -> str:
    if MALFORMED_ESCAPE.search(component):
        raise FileReferenceError(reference, "malformed percent escape")
    try:
        decoded = unquote_to_bytes(component).decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise FileReferenceError(reference, "invalid UTF-8") from error
    if any(ord(character) < 32 for character in decoded):
        raise FileReferenceError(reference, "control character")
    return decoded


def _windows_path(value: str) -> Path | PureWindowsPath:
    normalized = value.replace("/", "\\")
    if os.name == "nt":
        return Path(normalized)
    return PureWindowsPath(normalized)


def _windows_uri(
    reference: str,
    authority: str,
    component: str,
    converter: PathConverter,
) -> Path | PureWindowsPath:
    _decoded_component(reference, component)
    decoded = converter(component)
    if authority:
        if not decoded.startswith("/") or decoded == "/":
            raise FileReferenceError(reference, "UNC share is missing")
        return _windows_path(f"//{authority}{decoded}")
    if decoded.startswith("//"):
        parts = decoded[2:].split("/", 2)
        if len(parts) < 2 or not all(parts[:2]):
            raise FileReferenceError(reference, "UNC share is missing")
        return _windows_path(decoded)
    drive_path = decoded[1:] if re.match(r"^/[A-Za-z]:/", decoded) else decoded
    if not WINDOWS_DRIVE.match(drive_path):
        raise FileReferenceError(reference, "Windows drive path is missing")
    return _windows_path(drive_path)


def parse_file_reference(
    reference: os.PathLike[str] | str,
    platform: HostPlatform,
    converter: PathConverter = url2pathname,
) -> Path | PureWindowsPath:
    raw = os.fspath(reference)
    if not raw or any(ord(character) < 32 for character in raw):
        raise FileReferenceError(raw, "empty path or control character")
    if platform is HostPlatform.WINDOWS and WINDOWS_DRIVE.match(raw):
        return _windows_path(raw)

    try:
        parsed = urlsplit(raw)
    except ValueError as error:
        raise FileReferenceError(raw, "malformed URI") from error
    if not parsed.scheme:
        return _windows_path(raw) if platform is HostPlatform.WINDOWS else Path(raw)
    if parsed.scheme.lower() != "file":
        raise FileReferenceError(raw, "unsupported scheme")
    if parsed.query or parsed.fragment:
        raise FileReferenceError(raw, "query or fragment is unsupported")
    authority = parsed.netloc
    if "@" in authority or ":" in authority:
        raise FileReferenceError(raw, "userinfo or port is unsupported")
    if authority and ("%" in authority or not URI_AUTHORITY.fullmatch(authority)):
        raise FileReferenceError(raw, "invalid authority")
    if authority.lower() == "localhost":
        authority = ""
    if authority in {".", ".."}:
        raise FileReferenceError(raw, "ambiguous authority")
    if not parsed.path:
        raise FileReferenceError(raw, "path is missing")
    if platform is HostPlatform.WINDOWS:
        return _windows_uri(raw, authority, parsed.path, converter)
    if authority:
        raise FileReferenceError(raw, "remote authority is unsupported")
    _decoded_component(raw, parsed.path)
    return Path(converter(parsed.path))
