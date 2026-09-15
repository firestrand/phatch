#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run scripts/artifact_scan.py ARTIFACT [ARTIFACT ...]

from __future__ import annotations

import argparse
import io
import posixpath
import re
import stat
import sys
import tarfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from re import Pattern
from typing import Final

DEVELOPMENT_SEGMENTS: Final = frozenset(
    {".git", ".pytest_cache", "__pycache__", "tests"}
) | frozenset({".claude", ".omo", ".serena"})
DEVELOPMENT_PACKAGES: Final = frozenset(
    {"pytest", "pytest_cov", "ruff", "twine", "pyinstaller", "ty"}
)
CREDENTIAL_PATTERN: Final = re.compile(
    rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    rb"-----BEGIN [A-Z ]+PRIVATE KEY-----)"
)
KNOWN_BUILD_PATH_PATTERN: Final = re.compile(
    rb"(?:[A-Za-z]:\\(?:Users\\(?:runneradmin|containeradministrator|vsts)\\|a\\)|"
    rb"/Users/(?:runner|build|jenkins)/|/home/(?:runner|vsts|buildkite|jenkins)/)",
    re.IGNORECASE,
)
WINDOWS_ABSOLUTE_PATTERN: Final = re.compile(r"^[A-Za-z]:[\\/]")
PATH_BOUNDARY: Final = rb"(?<![A-Za-z0-9_.-])"
PATH_SEPARATOR: Final = rb"[\\/]"
PATH_END_BOUNDARY: Final = rb"(?=$|[\\/])"
MACHO_MAGICS: Final = (
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
)


@dataclass(frozen=True, slots=True)
class PayloadPrivacyPolicy:
    source_root_patterns: tuple[Pattern[bytes], ...]

    @classmethod
    def from_source_roots(cls, source_roots: Iterable[Path]) -> PayloadPrivacyPolicy:
        return cls(tuple(_source_root_pattern(root) for root in source_roots))

    def contains_build_path(self, payload: bytes, *, is_macho: bool) -> bool:
        if any(pattern.search(payload) for pattern in self.source_root_patterns):
            return True
        return not is_macho and KNOWN_BUILD_PATH_PATTERN.search(payload) is not None


@dataclass(frozen=True, slots=True)
class ScannedFile:
    source: str
    payload: bytes
    link_target: str | None = None
    link_kind: str | None = None


def _source_root_pattern(source_root: Path) -> Pattern[bytes]:
    raw_root = str(source_root)
    if not WINDOWS_ABSOLUTE_PATTERN.match(raw_root):
        raw_root = str(source_root.resolve())
    normalized = raw_root.replace("\\", "/").rstrip("/") or "/"
    escaped_segments = tuple(
        re.escape(segment).encode() for segment in normalized.split("/")
    )
    expression = PATH_SEPARATOR.join(escaped_segments)
    return re.compile(
        PATH_BOUNDARY + expression + PATH_END_BOUNDARY,
        re.IGNORECASE,
    )


def _filesystem_files(path: Path) -> Iterator[ScannedFile]:
    candidates = (path,) if path.is_file() else path.rglob("*")
    for candidate in candidates:
        if candidate.is_symlink():
            yield ScannedFile(
                candidate.relative_to(path).as_posix(),
                b"",
                candidate.readlink().as_posix(),
                "symbolic link",
            )
        elif candidate.is_file():
            name = (
                candidate.name
                if path.is_file()
                else candidate.relative_to(path).as_posix()
            )
            yield from _payload_files(name, candidate.read_bytes())


def _zip_files(path: Path) -> Iterator[ScannedFile]:
    with zipfile.ZipFile(path) as archive:
        for member in archive.infolist():
            if not member.is_dir():
                payload = archive.read(member)
                if stat.S_ISLNK(member.external_attr >> 16):
                    yield ScannedFile(
                        member.filename,
                        b"",
                        payload.decode("utf-8", errors="surrogateescape"),
                        "symbolic link",
                    )
                else:
                    yield from _payload_files(member.filename, payload)


def _tar_files(path: Path) -> Iterator[ScannedFile]:
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                yield ScannedFile(
                    member.name,
                    b"",
                    member.linkname,
                    "symbolic link" if member.issym() else "hard link",
                )
            elif member.isfile():
                stream = archive.extractfile(member)
                if stream is not None:
                    yield from _payload_files(member.name, stream.read())


def _payload_files(source: str, payload: bytes) -> Iterator[ScannedFile]:
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
            members = archive.getmembers()
            if not members:
                yield ScannedFile(source, payload)
                return
            for member in members:
                if member.issym() or member.islnk():
                    yield ScannedFile(
                        f"{source}!{member.name}",
                        b"",
                        member.linkname,
                        "symbolic link" if member.issym() else "hard link",
                    )
                elif member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        yield from _payload_files(
                            f"{source}!{member.name}", extracted.read()
                        )
        return
    except tarfile.ReadError:
        pass
    if zipfile.is_zipfile(io.BytesIO(payload)):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    member_payload = archive.read(member)
                    member_source = f"{source}!{member.filename}"
                    if stat.S_ISLNK(member.external_attr >> 16):
                        yield ScannedFile(
                            member_source,
                            b"",
                            member_payload.decode("utf-8", errors="surrogateescape"),
                            "symbolic link",
                        )
                    else:
                        yield from _payload_files(member_source, member_payload)
        return
    yield ScannedFile(source, payload)


def scan_files(path: Path) -> tuple[ScannedFile, ...]:
    if path.is_file() and tarfile.is_tarfile(path):
        return tuple(_tar_files(path))
    if path.is_file() and zipfile.is_zipfile(path):
        return tuple(_zip_files(path))
    return tuple(_filesystem_files(path))


def _name_findings(name: str) -> tuple[str, ...]:
    findings: list[str] = []
    for raw_name in name.split("!"):
        normalized_name = raw_name.replace("\\", "/")
        path = PurePosixPath(normalized_name)
        if (
            path.is_absolute()
            or WINDOWS_ABSOLUTE_PATTERN.match(normalized_name)
            or ".." in path.parts
        ) and "unsafe archive path" not in findings:
            findings.append("unsafe archive path")
        lowered = {part.lower() for part in path.parts}
        if (
            lowered & DEVELOPMENT_SEGMENTS or lowered & DEVELOPMENT_PACKAGES
        ) and "development-only path" not in findings:
            findings.append("development-only path")
        if path.suffix.lower() == ".pdb" and "development-only file" not in findings:
            findings.append("development-only file")
    return tuple(findings)


def _safe_symlink(source: str, target: str) -> bool:
    member = source.rsplit("!", maxsplit=1)[-1].replace("\\", "/")
    normalized_target = target.replace("\\", "/")
    if not normalized_target or PurePosixPath(normalized_target).is_absolute():
        return False
    resolved = posixpath.normpath(
        posixpath.join(posixpath.dirname(member), normalized_target)
    )
    return resolved != ".." and not resolved.startswith("../")


def findings(
    files: Iterable[ScannedFile], *, source_roots: Iterable[Path] = ()
) -> tuple[str, ...]:
    results: list[str] = []
    privacy_policy = PayloadPrivacyPolicy.from_source_roots(source_roots)
    for scanned in files:
        results.extend(
            f"{scanned.source}: {finding}" for finding in _name_findings(scanned.source)
        )
        if CREDENTIAL_PATTERN.search(scanned.payload):
            results.append(f"{scanned.source}: credential pattern")
        payload_has_build_path = privacy_policy.contains_build_path(
            scanned.payload, is_macho=scanned.payload.startswith(MACHO_MAGICS)
        )
        name_has_build_path = privacy_policy.contains_build_path(
            scanned.source.encode("utf-8", errors="surrogateescape"), is_macho=False
        )
        if payload_has_build_path or name_has_build_path:
            results.append(f"{scanned.source}: local build path")
        if scanned.link_kind == "hard link":
            results.append(f"{scanned.source}: hard link")
        elif scanned.link_kind == "symbolic link" and (
            scanned.link_target is None
            or not _safe_symlink(scanned.source, scanned.link_target)
        ):
            results.append(f"{scanned.source}: symbolic link")
    return tuple(results)


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", action="append", type=Path)
    parser.add_argument("artifacts", nargs="+", type=Path)
    options = parser.parse_args(arguments)
    missing = tuple(path for path in options.artifacts if not path.exists())
    if missing:
        print(f"missing artifact: {missing[0]}", file=sys.stderr)
        return 2
    scanned = tuple(file for path in options.artifacts for file in scan_files(path))
    source_roots = tuple(options.source_root) if options.source_root else (Path.cwd(),)
    failures = findings(scanned, source_roots=source_roots)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"scanned {len(scanned)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
