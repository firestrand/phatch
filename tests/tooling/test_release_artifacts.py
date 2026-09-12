from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

from scripts import artifact_scan, release_manifest
from tests.tooling.release_fixtures import write_metadata_wheel

PROJECT_ROOT = Path(__file__).parents[2]
MANIFEST_TOOL = PROJECT_ROOT / "scripts" / "release_manifest.py"
SCAN_TOOL = PROJECT_ROOT / "scripts" / "artifact_scan.py"


def _run(script: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_manifest_contains_real_checksums_sbom_and_runtime_licenses(
    tmp_path: Path,
) -> None:
    # Given: two release artifacts in a Unicode and space-containing directory
    artifacts = tmp_path / "downloaded artifacts Ω"
    artifacts.mkdir()
    wheel = write_metadata_wheel(
        artifacts / "Phatch.whl", ("Pillow", "platformdirs", "rich")
    )
    (artifacts / "Phatch.zip").write_bytes(b"portable")
    output = tmp_path / "release metadata"

    # When: the release manifest boundary processes the files
    completed = _run(
        MANIFEST_TOOL,
        str(artifacts),
        "--metadata-wheel",
        str(wheel),
        "--output",
        str(output),
    )

    # Then: checksums cover bytes and SPDX/licenses describe runtime dependencies
    assert completed.returncode == 0, completed.stderr
    checksums = (output / "SHA256SUMS").read_text(encoding="utf-8")
    assert hashlib.sha256(wheel.read_bytes()).hexdigest() in checksums
    assert hashlib.sha256(b"portable").hexdigest() in checksums
    sbom = json.loads((output / "sbom.spdx.json").read_text(encoding="utf-8"))
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["documentNamespace"].endswith("/0.3.0")
    assert {package["name"].lower() for package in sbom["packages"]} >= {
        "phatch",
        "pillow",
        "platformdirs",
        "rich",
    }
    licenses = (output / "licenses.tsv").read_text(encoding="utf-8").lower()
    assert "phatch\t0.3.0\tgpl-3.0-or-later" in licenses
    assert "pytest" not in licenses


def test_checksum_verification_detects_download_tampering(tmp_path: Path) -> None:
    # Given: a generated checksum followed by a changed downloaded artifact
    artifact = tmp_path / "portable.zip"
    artifact.write_bytes(b"original")
    wheel = write_metadata_wheel(tmp_path / "metadata.whl")
    output = tmp_path / "release"
    created = _run(
        MANIFEST_TOOL,
        str(artifact),
        "--metadata-wheel",
        str(wheel),
        "--output",
        str(output),
    )
    artifact.write_bytes(b"tampered")

    # When: the downloaded copy is verified against the original manifest
    verified = _run(
        MANIFEST_TOOL,
        str(artifact),
        "--metadata-wheel",
        str(wheel),
        "--output",
        str(tmp_path / "verification"),
        "--verify",
        str(output / "SHA256SUMS"),
    )

    # Then: verification fails and names the mismatched artifact
    assert created.returncode == 0
    assert verified.returncode == 1
    assert "portable.zip" in verified.stderr


def test_scanner_checks_archive_members_and_payload_for_release_leaks(
    tmp_path: Path,
) -> None:
    # Given: an archive containing developer state, a home path, and a token shape
    archive = tmp_path / "Phatch.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("Phatch/tests/debug.txt", "home=/Users/runner/work/project")
        bundle.writestr(
            "Phatch/config.txt", "token=ghp_abcdefghijklmnopqrstuvwxyz123456"
        )

    # When: the scanner inspects archive names and text payloads
    completed = _run(SCAN_TOOL, str(archive))

    # Then: every release leak is reported as a failing result
    assert completed.returncode == 1
    assert "development-only path" in completed.stderr
    assert "local build path" in completed.stderr
    assert "credential pattern" in completed.stderr


def test_scanner_accepts_normal_binary_and_resource_artifacts(tmp_path: Path) -> None:
    # Given: a portable directory with expected binaries, resources, and licenses
    portable = tmp_path / "Phatch portable Ω"
    (portable / "phatch_assets" / "data").mkdir(parents=True)
    (portable / "Phatch.exe").write_bytes(b"MZ\x00safe")
    (portable / "phatch_assets" / "data" / "geek.txt").write_text(
        "portable resource", encoding="utf-8"
    )
    (portable / "COPYING").write_text("GPL-3.0-or-later", encoding="utf-8")

    # When: the artifact scanner walks the real filesystem tree
    completed = _run(SCAN_TOOL, str(portable))

    # Then: legitimate runtime content passes without suppression rules
    assert completed.returncode == 0, completed.stderr
    assert "scanned 3 files" in completed.stdout


def test_scanner_reads_complete_nested_archives_without_generic_home_false_positive(
    tmp_path: Path,
) -> None:
    # Given: a nested wheel-sized archive with a leak beyond the former read cap
    inner = tmp_path / "inner.whl"
    with zipfile.ZipFile(inner, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("docs/example.txt", b"example=/home/alice/photos")
        bundle.writestr(
            "package/module.pyc",
            b"\0" * (2 * 1024 * 1024 + 1)
            + b"build=/home/runner/work/phatch ghp_abcdefghijklmnopqrstuvwxyz123456",
        )
    outer = tmp_path / "release.zip"
    with zipfile.ZipFile(outer, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.write(inner, "wheels/inner.whl")

    # When: the outer artifact is scanned recursively
    completed = _run(SCAN_TOOL, str(tmp_path))

    # Then: build provenance and credentials fail, but generic examples do not
    assert completed.returncode == 1
    assert "local build path" in completed.stderr
    assert "credential pattern" in completed.stderr
    assert "docs/example.txt: local" not in completed.stderr


def test_manifest_append_preserves_existing_platform_checksums(tmp_path: Path) -> None:
    # Given: one platform artifact already represented in release metadata
    first = tmp_path / "linux.whl"
    second = tmp_path / "windows.zip"
    first.write_bytes(b"linux")
    second.write_bytes(b"windows")
    wheel = write_metadata_wheel(tmp_path / "metadata.whl")
    output = tmp_path / "release"
    initial = _run(
        MANIFEST_TOOL,
        str(first),
        "--metadata-wheel",
        str(wheel),
        "--output",
        str(output),
    )

    # When: another platform artifact is appended
    appended = _run(
        MANIFEST_TOOL,
        str(second),
        "--metadata-wheel",
        str(wheel),
        "--output",
        str(output),
        "--append",
    )

    # Then: both checksums remain represented exactly once
    assert initial.returncode == 0
    assert appended.returncode == 0
    lines = (output / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert any(line.endswith("  linux.whl") for line in lines)
    assert any(line.endswith("  windows.zip") for line in lines)


def test_manifest_library_covers_append_verify_and_missing_dependency(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    # Given: direct library inputs including nested files and an absent dependency
    artifacts = tmp_path / "artifacts"
    nested = artifacts / "nested"
    nested.mkdir(parents=True)
    first = nested / "first.whl"
    second = artifacts / "second.zip"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output = artifacts / "release"
    wheel = write_metadata_wheel(tmp_path / "metadata.whl")

    # When: manifests are created, appended, verified, and checked after tampering
    files = release_manifest.create_manifest((artifacts,), output, metadata_wheel=wheel)
    release_manifest.create_manifest(
        (second,), output, metadata_wheel=wheel, append=True
    )
    clean = release_manifest.verify_manifest((first, second), output / "SHA256SUMS")
    first.write_bytes(b"changed")
    changed = release_manifest.main(
        (
            str(first),
            "--metadata-wheel",
            str(wheel),
            "--output",
            str(tmp_path / "check"),
            "--verify",
            str(output / "SHA256SUMS"),
        )
    )

    # Then: output recursion is excluded and both verify outcomes are observable
    assert {path.name for path in files} == {"first.whl", "second.zip"}
    assert clean == ()
    assert changed == 1
    assert "first.whl" in capsys.readouterr().err
    assert "not-installed" not in (output / "licenses.tsv").read_text(encoding="utf-8")


def test_manifest_preserves_relative_paths_and_rejects_incomplete_sets(
    tmp_path: Path,
) -> None:
    # Given: two uploaded artifacts with the same basename in distinct directories
    artifacts = tmp_path / "artifacts"
    first = artifacts / "a" / "same.dll"
    second = artifacts / "b" / "same.dll"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    output = tmp_path / "release"
    wheel = write_metadata_wheel(tmp_path / "metadata.whl")

    # When: checksums are generated and an extra file is later presented
    release_manifest.create_manifest((artifacts,), output, metadata_wheel=wheel)
    extra = artifacts / "extra.dll"
    extra.write_bytes(b"extra")
    mismatches = release_manifest.verify_manifest((artifacts,), output / "SHA256SUMS")

    # Then: both relative names survive and the exact artifact set is enforced
    checksums = (output / "SHA256SUMS").read_text(encoding="utf-8")
    assert "a/same.dll" in checksums
    assert "b/same.dll" in checksums
    assert mismatches == ("extra.dll",)


def test_sbom_has_utc_creation_relationships_and_installed_runtime_dependencies(
    tmp_path: Path,
) -> None:
    # Given: one release artifact
    artifact = write_metadata_wheel(
        tmp_path / "Phatch.whl",
        (
            "Pillow",
            "platformdirs",
            "rich",
        ),
    )
    output = tmp_path / "release"

    # When: SPDX release metadata is generated
    release_manifest.create_manifest((artifact,), output, metadata_wheel=artifact)

    # Then: required SPDX metadata and portable runtime packages are represented
    sbom = json.loads((output / "sbom.spdx.json").read_text(encoding="utf-8"))
    assert sbom["creationInfo"]["created"].endswith("Z")
    assert sbom["relationships"]
    package_names = {package["name"].lower() for package in sbom["packages"]}
    assert {
        "phatch",
        "pillow",
        "platformdirs",
        "rich",
    } <= package_names


def test_scanner_library_covers_zip_tar_directory_and_failure_main(
    tmp_path: Path, capsys
) -> None:
    # Given: equivalent safe files in a directory, ZIP, and tar archive
    directory = tmp_path / "directory"
    directory.mkdir()
    safe = directory / "safe.bin"
    safe.write_bytes(b"runtime")
    archive = tmp_path / "safe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("safe.bin", b"runtime")
        bundle.writestr("empty/", b"")
    tar_path = tmp_path / "safe.tar.gz"
    with tarfile.open(tar_path, "w:gz") as bundle:
        bundle.add(safe, arcname="safe.bin")
        bundle.add(directory, arcname="empty-dir", recursive=False)

    # When: all adapters scan and an unsafe record crosses the CLI boundary
    scanned = (
        *artifact_scan.scan_files(directory),
        *artifact_scan.scan_files(archive),
        *artifact_scan.scan_files(tar_path),
    )
    failures = artifact_scan.findings(
        (
            artifact_scan.ScannedFile("../escape.pyc", b"safe"),
            artifact_scan.ScannedFile("ruff/tool.py", b"safe"),
            artifact_scan.ScannedFile("config", b"/home/runner/work"),
        )
    )
    result = artifact_scan.main((str(tmp_path / "missing tests"),))

    # Then: real adapters return bytes and every prohibited class fails closed
    assert len(scanned) == 3
    assert {finding.rpartition(": ")[2] for finding in failures} == {
        "unsafe archive path",
        "development-only path",
        "local build path",
    }
    assert result == 2
    assert "missing artifact" in capsys.readouterr().err
