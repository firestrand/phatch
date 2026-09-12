from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from phatch import release_inventory
from scripts import artifact_scan, release_manifest
from tests.tooling.release_fixtures import write_metadata_wheel


def test_manifest_main_reports_missing_and_successful_inputs(
    tmp_path: Path, capsys
) -> None:
    # Given: one missing artifact and one real file
    missing = tmp_path / "missing.whl"
    artifact = tmp_path / "real.whl"
    write_metadata_wheel(artifact)

    # When: both inputs cross the command boundary independently
    rejected = release_manifest.main(
        (
            str(missing),
            "--metadata-wheel",
            str(artifact),
            "--output",
            str(tmp_path / "missing-output"),
        )
    )
    created = release_manifest.main(
        (
            str(artifact),
            "--metadata-wheel",
            str(artifact),
            "--output",
            str(tmp_path / "release"),
        )
    )
    verified = release_manifest.main(
        (
            str(artifact),
            "--metadata-wheel",
            str(artifact),
            "--output",
            str(tmp_path / "verified"),
            "--verify",
            str(tmp_path / "release" / "SHA256SUMS"),
        )
    )

    # Then: absence fails while a real artifact produces all manifests
    captured = capsys.readouterr()
    assert rejected == 2
    assert created == 0
    assert verified == 0
    assert "missing artifact" in captured.err
    assert "manifested 1 files" in captured.out


def test_manifest_parsers_reject_malformed_checksum_lines(
    tmp_path: Path, monkeypatch
) -> None:
    # Given: installed metadata with legacy license fields and a mixed manifest
    distribution = SimpleNamespace(
        metadata={"Name": "Example", "License-Expression": None, "License": "MIT"},
        version="1.2.3",
        requires=(),
    )
    monkeypatch.setattr(
        release_inventory.metadata, "distribution", lambda name: distribution
    )
    checksum_file = tmp_path / "SHA256SUMS"
    checksum_file.write_text("malformed\nabc  artifact.whl\n", encoding="utf-8")

    # When: package metadata and checksum records are parsed
    package, requirements = release_inventory._installed_record("Example")

    # Then: legacy license metadata works and malformed manifests fail closed
    assert package == release_manifest.PackageRecord("Example", "1.2.3", "MIT")
    assert requirements == ()
    with pytest.raises(release_manifest.ManifestFormatError):
        release_manifest._read_checksums(checksum_file)
    with pytest.raises(release_manifest.ManifestFormatError):
        release_manifest._read_checksums(tmp_path / "absent")
    empty = tmp_path / "empty"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(release_manifest.ManifestFormatError, match="empty"):
        release_manifest._read_checksums(empty)


def test_manifest_rejects_changed_duplicate_artifact(
    tmp_path: Path,
) -> None:
    # Given: an artifact already represented by an existing checksum manifest
    artifact = write_metadata_wheel(tmp_path / "Phatch.whl")
    output = tmp_path / "release"
    release_manifest.create_manifest((artifact,), output, metadata_wheel=artifact)
    artifact.write_bytes(artifact.read_bytes() + b"changed")

    # When/Then: appending different bytes at the same path fails closed
    with pytest.raises(release_manifest.ManifestFormatError, match="duplicate"):
        release_manifest.create_manifest(
            (artifact,), output, metadata_wheel=artifact, append=True
        )


def test_manifest_main_reports_invalid_verification_and_runtime_inventory(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # Given: a real artifact, malformed verification input, and failed inventory
    artifact = write_metadata_wheel(tmp_path / "Phatch.whl")
    malformed = tmp_path / "SHA256SUMS"
    malformed.write_text("invalid", encoding="utf-8")
    arguments = (
        str(artifact),
        "--metadata-wheel",
        str(artifact),
        "--output",
        str(tmp_path / "release"),
    )

    # When: each failure crosses the command boundary
    invalid_verification = release_manifest.main(
        (*arguments, "--verify", str(malformed))
    )
    monkeypatch.setattr(
        release_manifest,
        "package_records",
        lambda *args: (_ for _ in ()).throw(
            release_inventory.MissingRuntimeDistributionError("missing")
        ),
    )
    missing_runtime = release_manifest.main(arguments)

    # Then: both boundary failures return usage errors with actionable messages
    captured = capsys.readouterr()
    assert invalid_verification == 2
    assert missing_runtime == 2
    assert "invalid checksum record" in captured.err
    assert "selected runtime dependency is not installed" in captured.err


def test_scanner_main_reports_clean_and_credential_artifacts(
    tmp_path: Path, capsys
) -> None:
    # Given: one clean standalone file and one credential-shaped payload
    clean = tmp_path / "clean.bin"
    leaked = tmp_path / "leaked.txt"
    clean.write_bytes(b"runtime")
    leaked.write_bytes(b"ghp_abcdefghijklmnopqrstuvwxyz123456")

    # When: both files cross the scanner command boundary independently
    accepted = artifact_scan.main((str(clean),))
    rejected = artifact_scan.main((str(leaked),))

    # Then: clean content succeeds and the credential shape fails visibly
    captured = capsys.readouterr()
    assert accepted == 0
    assert rejected == 1
    assert "scanned 1 files" in captured.out
    assert "credential pattern" in captured.err


def test_scanner_rejects_missing_unsafe_and_symbolic_link_artifacts(
    tmp_path: Path, capsys
) -> None:
    target = tmp_path / "target.txt"
    target.write_bytes(b"runtime")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    missing = artifact_scan.main((str(tmp_path / "missing.zip"),))
    scanned = artifact_scan.scan_files(tmp_path)
    unsafe = artifact_scan.findings(
        (artifact_scan.ScannedFile("../debug.pdb", b"runtime"),)
    )

    assert missing == 2
    assert "missing artifact" in capsys.readouterr().err
    assert any(
        "symbolic link" in finding for finding in artifact_scan.findings(scanned)
    )
    assert unsafe == (
        "../debug.pdb: unsafe archive path",
        "../debug.pdb: development-only file",
    )


def test_scanner_expands_tar_payloads_and_preserves_empty_archives(
    tmp_path: Path,
) -> None:
    archive = tmp_path / "release.tar"
    payload = b"build=/home/runner/work/phatch"
    with tarfile.open(archive, "w") as bundle:
        member = tarfile.TarInfo("package/runtime.txt")
        member.size = len(payload)
        bundle.addfile(member, io.BytesIO(payload))

    empty_buffer = io.BytesIO()
    with tarfile.open(fileobj=empty_buffer, mode="w"):
        pass

    scanned = artifact_scan.scan_files(archive)
    nested = tuple(artifact_scan._payload_files("nested.tar", archive.read_bytes()))
    empty = tuple(artifact_scan._payload_files("empty.tar", empty_buffer.getvalue()))

    assert scanned == (artifact_scan.ScannedFile("package/runtime.txt", payload),)
    assert nested == (
        artifact_scan.ScannedFile("nested.tar!package/runtime.txt", payload),
    )
    assert empty == (artifact_scan.ScannedFile("empty.tar", empty_buffer.getvalue()),)


def test_scanner_expands_nested_zip_payload_directly() -> None:
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w") as archive:
        archive.writestr("package/", b"")
        archive.writestr("package/runtime.txt", b"runtime")

    scanned = tuple(
        artifact_scan._payload_files("nested.whl", archive_buffer.getvalue())
    )

    assert scanned == (
        artifact_scan.ScannedFile("nested.whl!package/runtime.txt", b"runtime"),
    )
