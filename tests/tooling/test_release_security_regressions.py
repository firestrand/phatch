from __future__ import annotations

import io
import json
import stat
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from phatch import release_inventory
from scripts import artifact_scan, release_manifest


def _metadata_wheel(path: Path, extra_requirements: tuple[str, ...] = ()) -> Path:
    requirements = "".join(
        f"Requires-Dist: {requirement}\n" for requirement in extra_requirements
    )
    metadata_text = f"""Metadata-Version: 2.4
Name: Phatch
Version: 0.3.0
License-Expression: GPL-3.0-or-later
Requires-Dist: rich>=14.1.0
Requires-Dist: wxPython>=4.2.3; extra == "gui"
Requires-Dist: pywin32>=311; sys_platform == "win32" and extra == "windows"
{requirements}

"""
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("phatch-0.3.0.dist-info/METADATA", metadata_text)
    return path


def _distribution(name: str, requirements: tuple[str, ...] = ()) -> SimpleNamespace:
    return SimpleNamespace(
        metadata={
            "Name": name,
            "License-Expression": "MIT",
            "License": None,
        },
        version="1.0.0",
        requires=requirements,
    )


def test_sbom_uses_wheel_metadata_and_installed_transitive_closure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a supplied Phatch wheel and installed metadata with a transitive chain
    wheel = _metadata_wheel(tmp_path / "phatch.whl")
    distributions = {
        "rich": _distribution("rich", ("markdown-it-py>=2.2.0", "Pygments>=2.13.0")),
        "markdown-it-py": _distribution("markdown-it-py", ("mdurl~=0.1",)),
        "mdurl": _distribution("mdurl"),
        "pygments": _distribution("Pygments"),
        "wxpython": _distribution("wxPython"),
    }
    monkeypatch.setattr(
        release_inventory.metadata,
        "distribution",
        lambda name: distributions[name.lower()],
    )

    # When: release metadata is generated from that wheel
    output = tmp_path / "release"
    release_manifest.create_manifest(
        (wheel,), output, metadata_wheel=wheel, selected_extras=("gui", "windows")
    )

    # Then: the root and every selected installed transitive dependency are present
    sbom = json.loads((output / "sbom.spdx.json").read_text(encoding="utf-8"))
    assert {package["name"].lower() for package in sbom["packages"]} == {
        "phatch",
        "rich",
        "markdown-it-py",
        "pygments",
        "mdurl",
        "wxpython",
    }


def test_sbom_fails_when_selected_runtime_dependency_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: a wheel whose selected Rich dependency is not installed
    wheel = _metadata_wheel(tmp_path / "phatch.whl")
    monkeypatch.setattr(
        release_inventory.metadata,
        "distribution",
        lambda name: (_ for _ in ()).throw(
            release_inventory.metadata.PackageNotFoundError(name)
        ),
    )

    # When/Then: SBOM generation fails rather than recording a placeholder
    with pytest.raises(release_manifest.MissingRuntimeDistributionError, match="rich"):
        release_manifest.create_manifest(
            (wheel,), tmp_path / "release", metadata_wheel=wheel
        )


@pytest.mark.parametrize("shape", ["invalid", "empty", "duplicate", "missing-version"])
def test_sbom_rejects_invalid_wheel_metadata(tmp_path: Path, shape: str) -> None:
    # Given: a wheel boundary with malformed or ambiguous metadata
    wheel = tmp_path / "phatch.whl"
    if shape == "invalid":
        wheel.write_bytes(b"not a wheel")
    else:
        metadata_text = "Metadata-Version: 2.4\nName: Phatch\n\n"
        with zipfile.ZipFile(wheel, "w") as archive:
            if shape in {"duplicate", "missing-version"}:
                archive.writestr("phatch-0.3.0.dist-info/METADATA", metadata_text)
            if shape == "duplicate":
                archive.writestr("other-1.0.dist-info/METADATA", metadata_text)

    # When/Then: release inventory rejects the untrustworthy wheel boundary
    with pytest.raises(release_inventory.WheelMetadataError):
        release_inventory.package_records(wheel)


def test_sbom_deduplicates_requirement_for_root_distribution(tmp_path: Path) -> None:
    # Given: wheel metadata that redundantly requires its own root distribution
    wheel = _metadata_wheel(tmp_path / "phatch.whl", ("Phatch>=0.3",))

    # When: package records are resolved
    packages = release_inventory.package_records(wheel)

    # Then: the wheel root appears exactly once without an installed lookup
    assert sum(package.name == "Phatch" for package in packages) == 1


def test_scanner_rejects_nested_raw_parent_traversal_from_directory(
    tmp_path: Path,
) -> None:
    # Given: a permanent directory containing a wheel with a raw traversal member
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    wheel = artifact_dir / "outer.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("../escape.py", b"runtime")

    # When: the directory boundary recursively scans the wheel
    result = artifact_scan.main((str(artifact_dir),))

    # Then: prefix composition cannot hide the unsafe raw member
    assert result == 1


def test_scanner_accepts_confined_symlinks_and_rejects_escaping_links(
    tmp_path: Path,
) -> None:
    # Given: confined bundle symlinks plus escaping symbolic and hard links
    zip_path = tmp_path / "links.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        for name, target in (
            ("App/Resources/library", "../Frameworks/library"),
            ("App/escape", "../../outside"),
        ):
            link = zipfile.ZipInfo(name)
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, target)
    tar_path = tmp_path / "links.tar"
    with tarfile.open(tar_path, "w") as archive:
        for name, link_type, target in (
            ("App/confined", tarfile.SYMTYPE, "target"),
            ("App/symbolic", tarfile.SYMTYPE, "/absolute"),
            ("App/hard", tarfile.LNKTYPE, "target"),
        ):
            member = tarfile.TarInfo(name)
            member.type = link_type
            member.linkname = target
            archive.addfile(member, io.BytesIO())

    # When: both archive adapters inspect raw entry types
    findings = artifact_scan.findings(
        (*artifact_scan.scan_files(zip_path), *artifact_scan.scan_files(tar_path))
    )

    # Then: confined symbolic links pass while escapes and hard links fail
    assert sum("symbolic link" in finding for finding in findings) == 2
    assert sum("hard link" in finding for finding in findings) == 1


def test_scanner_preserves_links_inside_nested_archives() -> None:
    # Given: link entries embedded in ZIP and TAR payloads
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as archive:
        link = zipfile.ZipInfo("App/escape")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(link, "../../outside")

    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        member = tarfile.TarInfo("App/hard")
        member.type = tarfile.LNKTYPE
        member.linkname = "target"
        archive.addfile(member, io.BytesIO())

    # When: nested payload expansion and release rules inspect both entries
    findings = artifact_scan.findings(
        (
            *artifact_scan._payload_files("nested.zip", zip_buffer.getvalue()),
            *artifact_scan._payload_files("nested.tar", tar_buffer.getvalue()),
        )
    )

    # Then: archive nesting cannot hide unsafe symbolic or hard links
    assert findings == (
        "nested.zip!App/escape: symbolic link",
        "nested.tar!App/hard: hard link",
    )


def test_scanner_ignores_macho_build_provenance_but_scans_other_payloads() -> None:
    # Given: the same CI path in a Mach-O binary, bytecode, and text payload
    build_path = b"/Users/runner/work/phatch"
    files = (
        artifact_scan.ScannedFile("native.dylib", b"\xcf\xfa\xed\xfe" + build_path),
        artifact_scan.ScannedFile("module.pyc", b"\xa7\r\r\n" + build_path),
        artifact_scan.ScannedFile("config.txt", build_path),
    )

    # When: release payload rules inspect each file
    findings = artifact_scan.findings(files)

    # Then: native dependency provenance is ignored but releasable data is not
    assert findings == (
        "module.pyc: local build path",
        "config.txt: local build path",
    )


def test_sbom_normalizes_non_spdx_legacy_license_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: an installed dependency exposing a legacy descriptive license URL
    wheel = _metadata_wheel(tmp_path / "phatch.whl")
    distribution = _distribution("rich")
    legacy_license = (
        "wxWindows Library License (https://opensource.org/licenses/wxwindows.php)"
    )
    distribution.metadata["License-Expression"] = None
    distribution.metadata["License"] = legacy_license
    monkeypatch.setattr(
        release_inventory.metadata, "distribution", lambda name: distribution
    )

    # When: package records and an SPDX document normalize the legacy metadata
    packages = release_inventory.package_records(wheel)
    output = tmp_path / "release"
    output.mkdir()
    release_manifest._write_sbom(output, packages)
    sbom = json.loads((output / "sbom.spdx.json").read_text(encoding="utf-8"))

    # Then: the custom reference retains matching extracted licensing information
    assert packages[1].license_expression == "LicenseRef-wxWindows-Library-License"
    assert packages[1].license_text == legacy_license
    assert sbom["hasExtractedLicensingInfos"] == [
        {
            "extractedText": legacy_license,
            "licenseId": "LicenseRef-wxWindows-Library-License",
        }
    ]
