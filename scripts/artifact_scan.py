#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run scripts/artifact_scan.py ARTIFACT [ARTIFACT ...]

from __future__ import annotations

import argparse
import io
import re
import stat
import sys
import tarfile
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final

DEVELOPMENT_SEGMENTS: Final = frozenset(
    {".git", ".pytest_cache", "__pycache__", "tests"}
)
DEVELOPMENT_PACKAGES: Final = frozenset(
    {"pytest", "pytest_cov", "ruff", "twine", "pyinstaller", "ty"}
)
CREDENTIAL_PATTERN: Final = re.compile(
    rb"(?:gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
    rb"-----BEGIN [A-Z ]+PRIVATE KEY-----)"
)
BUILD_PATH_PATTERN: Final = re.compile(
    rb"(?:[A-Za-z]:\\(?:Users\\(?:runneradmin|containeradministrator|vsts)\\|a\\)|"
    rb"/Users/(?:runner|build|jenkins)/|/home/(?:runner|vsts|buildkite|jenkins)/)",
    re.IGNORECASE,
)
SYMLINK_PAYLOAD: Final = b"PHATCH_UNSAFE_SYMLINK"


@dataclass(frozen=True, slots=True)
class ScannedFile:
    source: str
    payload: bytes


def _filesystem_files(path: Path) -> Iterator[ScannedFile]:
    candidates = (path,) if path.is_file() else path.rglob("*")
    for candidate in candidates:
        if candidate.is_symlink():
            yield ScannedFile(candidate.relative_to(path).as_posix(), SYMLINK_PAYLOAD)
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
                payload = (
                    SYMLINK_PAYLOAD
                    if stat.S_ISLNK(member.external_attr >> 16)
                    else archive.read(member)
                )
                yield from _payload_files(member.filename, payload)


def _tar_files(path: Path) -> Iterator[ScannedFile]:
    with tarfile.open(path, "r:*") as archive:
        for member in archive.getmembers():
            if member.issym() or member.islnk():
                yield ScannedFile(member.name, SYMLINK_PAYLOAD)
            elif member.isfile():
                stream = archive.extractfile(member)
                if stream is not None:
                    yield from _payload_files(member.name, stream.read())


def _payload_files(source: str, payload: bytes) -> Iterator[ScannedFile]:
    if zipfile.is_zipfile(io.BytesIO(payload)):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for member in archive.infolist():
                if not member.is_dir():
                    member_payload = (
                        SYMLINK_PAYLOAD
                        if stat.S_ISLNK(member.external_attr >> 16)
                        else archive.read(member)
                    )
                    yield from _payload_files(
                        f"{source}!{member.filename}", member_payload
                    )
        return
    try:
        with tarfile.open(fileobj=io.BytesIO(payload), mode="r:*") as archive:
            members = archive.getmembers()
            if not members:
                yield ScannedFile(source, payload)
                return
            for member in members:
                if member.issym() or member.islnk():
                    yield ScannedFile(f"{source}!{member.name}", SYMLINK_PAYLOAD)
                elif member.isfile():
                    extracted = archive.extractfile(member)
                    if extracted is not None:
                        yield from _payload_files(
                            f"{source}!{member.name}", extracted.read()
                        )
        return
    except tarfile.ReadError:
        pass
    yield ScannedFile(source, payload)


def scan_files(path: Path) -> tuple[ScannedFile, ...]:
    if path.is_file() and zipfile.is_zipfile(path):
        return tuple(_zip_files(path))
    if path.is_file() and tarfile.is_tarfile(path):
        return tuple(_tar_files(path))
    return tuple(_filesystem_files(path))


def _name_findings(name: str) -> tuple[str, ...]:
    findings: list[str] = []
    for raw_name in name.split("!"):
        path = PurePosixPath(raw_name.replace("\\", "/"))
        if (
            path.is_absolute() or ".." in path.parts
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


def findings(files: Iterable[ScannedFile]) -> tuple[str, ...]:
    results: list[str] = []
    for scanned in files:
        results.extend(
            f"{scanned.source}: {finding}" for finding in _name_findings(scanned.source)
        )
        if CREDENTIAL_PATTERN.search(scanned.payload):
            results.append(f"{scanned.source}: credential pattern")
        if BUILD_PATH_PATTERN.search(scanned.payload):
            results.append(f"{scanned.source}: local build path")
        if scanned.payload == SYMLINK_PAYLOAD:
            results.append(f"{scanned.source}: symbolic link")
    return tuple(results)


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    options = parser.parse_args(arguments)
    missing = tuple(path for path in options.artifacts if not path.exists())
    if missing:
        print(f"missing artifact: {missing[0]}", file=sys.stderr)
        return 2
    scanned = tuple(file for path in options.artifacts for file in scan_files(path))
    failures = findings(scanned)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"scanned {len(scanned)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
