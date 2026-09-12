#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = []
# ///

# How to run: uv run scripts/release_manifest.py ARTIFACT
#   --metadata-wheel WHEEL --output DIR

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from os.path import commonpath
from pathlib import Path

from phatch.release_inventory import (
    MissingRuntimeDistributionError,
    PackageRecord,
    WheelMetadataError,
    package_records,
)


class ManifestFormatError(ValueError):
    pass


def _artifact_files(paths: tuple[Path, ...], output: Path) -> tuple[Path, ...]:
    files: set[Path] = set()
    resolved_output = output.resolve()
    for path in paths:
        if path.is_file():
            files.add(path)
            continue
        files.update(
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file()
            and resolved_output not in candidate.resolve().parents
        )
    return tuple(sorted(files, key=lambda item: item.as_posix()))


def _artifact_names(
    files: tuple[Path, ...], paths: tuple[Path, ...]
) -> dict[Path, str]:
    roots = tuple(path if path.is_dir() else path.parent for path in paths)
    root = Path(commonpath(tuple(str(path.resolve()) for path in roots)))
    return {path: path.resolve().relative_to(root).as_posix() for path in files}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    if not path.is_file():
        raise ManifestFormatError(f"missing checksum manifest: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if (
            not separator
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            or not name
            or name in checksums
        ):
            raise ManifestFormatError(f"invalid checksum record: {line}")
        checksums[name] = digest
    if not checksums:
        raise ManifestFormatError("checksum manifest is empty")
    return checksums


def _write_sbom(output: Path, packages: tuple[PackageRecord, ...]) -> None:
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "Phatch release dependencies",
        "documentNamespace": (
            f"https://github.com/firestrand/phatch/sbom/{packages[0].version}"
        ),
        "creationInfo": {
            "creators": ["Tool: scripts/release_manifest.py"],
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "packages": [
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": package.name,
                "versionInfo": package.version,
                "licenseConcluded": package.license_expression,
                "licenseDeclared": package.license_expression,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
            }
            for index, package in enumerate(packages, start=1)
        ],
        "relationships": [
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": "SPDXRef-Package-1",
            },
            *[
                {
                    "spdxElementId": "SPDXRef-Package-1",
                    "relationshipType": "DEPENDS_ON",
                    "relatedSpdxElement": f"SPDXRef-Package-{index}",
                }
                for index in range(2, len(packages) + 1)
            ],
        ],
    }
    (output / "sbom.spdx.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def create_manifest(
    paths: tuple[Path, ...],
    output: Path,
    *,
    metadata_wheel: Path,
    selected_extras: tuple[str, ...] = (),
    append: bool = False,
) -> tuple[Path, ...]:
    output.mkdir(parents=True, exist_ok=True)
    files = _artifact_files(paths, output)
    checksum_path = output / "SHA256SUMS"
    checksums = _read_checksums(checksum_path) if append else {}
    names = _artifact_names(files, paths)
    for artifact in files:
        name = names[artifact]
        if name in checksums and checksums[name] != _sha256(artifact):
            raise ManifestFormatError(f"duplicate artifact path: {name}")
        checksums[name] = _sha256(artifact)
    checksum_path.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    packages = package_records(metadata_wheel, selected_extras)
    _write_sbom(output, packages)
    (output / "licenses.tsv").write_text(
        "name\tversion\tlicense\n"
        + "".join(
            f"{package.name}\t{package.version}\t{package.license_expression}\n"
            for package in packages
        ),
        encoding="utf-8",
    )
    return files


def verify_manifest(paths: tuple[Path, ...], manifest: Path) -> tuple[str, ...]:
    expected = _read_checksums(manifest)
    files = _artifact_files(paths, manifest.parent)
    names = _artifact_names(files, paths)
    actual = {names[path]: _sha256(path) for path in files}
    return tuple(
        sorted(
            set(expected) ^ set(actual)
            | {
                name
                for name in set(expected) & set(actual)
                if expected[name] != actual[name]
            }
        )
    )


def main(arguments: tuple[str, ...] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--metadata-wheel", required=True, type=Path)
    parser.add_argument("--extra", action="append", default=[])
    options = parser.parse_args(arguments)
    paths = tuple(options.artifacts)
    missing = tuple(
        path for path in (*paths, options.metadata_wheel) if not path.exists()
    )
    if missing:
        print(f"missing artifact: {missing[0]}", file=sys.stderr)
        return 2
    if options.verify is not None:
        try:
            mismatches = verify_manifest(paths, options.verify)
        except ManifestFormatError as error:
            print(error, file=sys.stderr)
            return 2
        if mismatches:
            print(f"checksum mismatch: {', '.join(mismatches)}", file=sys.stderr)
            return 1
    try:
        files = create_manifest(
            paths,
            options.output,
            metadata_wheel=options.metadata_wheel,
            selected_extras=tuple(options.extra),
            append=options.append,
        )
    except (MissingRuntimeDistributionError, WheelMetadataError) as error:
        print(error, file=sys.stderr)
        return 2
    print(f"manifested {len(files)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
