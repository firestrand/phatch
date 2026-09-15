from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts import artifact_scan


@pytest.mark.parametrize(
    "source",
    (
        ".omo/evidence/log.txt",
        "bundle/.claude/state.json",
        "bundle\\.serena\\cache.db",
        "outer.zip!.OMO/evidence/log.txt",
    ),
)
def test_agent_state_path_components_are_rejected(source: str) -> None:
    # Given: a release member whose path contains an agent-state directory
    scanned = artifact_scan.ScannedFile(source, b"harmless")

    # When: release policy inspects its archive identity
    result = artifact_scan.findings((scanned,))

    # Then: exact agent-state components fail the release scan
    assert result == (f"{source}: development-only path",)


def test_agent_state_component_match_does_not_reject_substrings() -> None:
    # Given: a legitimate runtime path containing only an agent-state substring
    scanned = artifact_scan.ScannedFile("bundle/.omoa/theme.txt", b"harmless")

    # When: release policy inspects the member
    result = artifact_scan.findings((scanned,))

    # Then: component matching does not create a substring false positive
    assert result == ()


def test_nested_zip_and_tar_cannot_hide_agent_state_members(tmp_path: Path) -> None:
    # Given: a ZIP containing a TAR whose member is under an agent-state directory
    inner_tar = io.BytesIO()
    with tarfile.open(fileobj=inner_tar, mode="w") as archive:
        member = tarfile.TarInfo("payload/.serena/index.json")
        member.size = len(b"harmless")
        archive.addfile(member, io.BytesIO(b"harmless"))
    outer = tmp_path / "release.zip"
    with zipfile.ZipFile(outer, "w") as archive:
        archive.writestr("nested/content.tar", inner_tar.getvalue())

    # When: the scanner recursively expands both archive formats
    result = artifact_scan.findings(artifact_scan.scan_files(outer))

    # Then: the nested member identity remains subject to component policy
    assert result == (
        "nested/content.tar!payload/.serena/index.json: development-only path",
    )


def test_nested_tar_and_zip_cannot_hide_agent_state_members(tmp_path: Path) -> None:
    # Given: a TAR containing a ZIP whose member is under an agent-state directory
    inner_zip = io.BytesIO()
    with zipfile.ZipFile(inner_zip, "w") as archive:
        archive.writestr("payload/.claude/session.json", b"harmless")
    outer = tmp_path / "release.tar"
    with tarfile.open(outer, "w") as archive:
        member = tarfile.TarInfo("nested/content.zip")
        member.size = len(inner_zip.getvalue())
        archive.addfile(member, io.BytesIO(inner_zip.getvalue()))

    # When: the scanner recursively expands both archive formats
    result = artifact_scan.findings(artifact_scan.scan_files(outer))

    # Then: reverse nesting cannot hide an agent-state member
    assert result == (
        "nested/content.zip!payload/.claude/session.json: development-only path",
    )


def test_nested_archive_payload_scans_configured_source_roots(tmp_path: Path) -> None:
    # Given: a TAR containing a ZIP text member with a private build root
    source_root = Path("/Volumes/Build Root Ω/phatch")
    inner_zip = io.BytesIO()
    with zipfile.ZipFile(inner_zip, "w") as archive:
        archive.writestr("package/build.log", f"source={source_root}/phatch.py")
    outer = tmp_path / "release.tar"
    with tarfile.open(outer, "w") as archive:
        member = tarfile.TarInfo("nested/content.zip")
        member.size = len(inner_zip.getvalue())
        archive.addfile(member, io.BytesIO(inner_zip.getvalue()))

    # When: recursive payload scanning uses an explicit source root
    result = artifact_scan.findings(
        artifact_scan.scan_files(outer), source_roots=(source_root,)
    )

    # Then: nesting cannot hide configured source-root text
    assert result == ("nested/content.zip!package/build.log: local build path",)


@pytest.mark.parametrize(
    ("root", "payload"),
    (
        ("/Users/owner/Project [private] Ω", "/Users/owner/Project [private] Ω"),
        ("/Users/owner/Project Ω ", "/Users/owner/Project Ω "),
        ("/Users/owner/Project [private] Ω", "at=/Users/owner/Project [private] Ω/src"),
        (
            "/Users/owner/Project [private] Ω",
            "at=\\Users\\owner\\Project [private] Ω\\src",
        ),
        ("C:\\Users\\Owner Name\\phatch Ω", "c:/users/owner name/phatch Ω/build"),
    ),
)
def test_configured_source_roots_are_rejected_with_separator_aliases(
    root: str, payload: str
) -> None:
    # Given: a harmless payload containing a configured private source root
    scanned = artifact_scan.ScannedFile("payload.txt", payload.encode())

    # When: policy scans with the source/build root supplied by its caller
    result = artifact_scan.findings((scanned,), source_roots=(Path(root),))

    # Then: escaped root text is reported without relying on known CI homes
    assert result == ("payload.txt: local build path",)


@pytest.mark.parametrize(
    "payload",
    (
        b"/Users/owner/Projectile/build",
        b"prefix/Users/owner/Project/build",
        b"C:/Users/Owner Name/phatcher/build",
    ),
)
def test_configured_source_roots_require_path_boundaries(payload: bytes) -> None:
    # Given: text containing only a prefix or embedded fragment of a private root
    roots = (Path("/Users/owner/Project"), Path("C:\\Users\\Owner Name\\phatch"))

    # When: policy scans the text
    result = artifact_scan.findings(
        (artifact_scan.ScannedFile("payload.txt", payload),), source_roots=roots
    )

    # Then: partial usernames and root prefixes are not path matches
    assert result == ()


@pytest.mark.parametrize(
    ("root", "source"),
    (
        ("/Users/owner/Project Ω", "outer.zip!/Users/owner/Project Ω/log.txt"),
        (
            "C:\\Users\\Owner Name\\phatch",
            "outer.tar!C:/Users/Owner Name/phatch/build.log",
        ),
    ),
)
def test_configured_source_roots_are_rejected_in_archive_member_names(
    root: str, source: str
) -> None:
    # Given: a nested archive identity containing a configured source root
    scanned = artifact_scan.ScannedFile(source, b"harmless")

    # When: release policy inspects member names and payloads
    result = artifact_scan.findings((scanned,), source_roots=(Path(root),))

    # Then: the member is both unsafe and private even without a payload leak
    assert result == (
        f"{source}: unsafe archive path",
        f"{source}: local build path",
    )


def test_explicit_source_roots_and_credentials_are_scanned_inside_macho() -> None:
    # Given: Mach-O bytes with upstream provenance, an owner root, and a credential
    payload = (
        b"\xcf\xfa\xed\xfe/Users/runner/work/upstream "
        b"/Users/current-owner/phatch/src "
        b"ghp_abcdefghijklmnopqrstuvwxyz123456"
    )
    scanned = artifact_scan.ScannedFile("native.dylib", payload)

    # When: release policy applies the explicit owner root
    result = artifact_scan.findings(
        (scanned,), source_roots=(Path("/Users/current-owner/phatch"),)
    )

    # Then: only the upstream provenance exception remains; privacy checks still run
    assert result == (
        "native.dylib: credential pattern",
        "native.dylib: local build path",
    )


def test_cli_defaults_source_root_to_selected_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Given: an artifact containing the selected source working directory
    source_root = tmp_path / "source Ω"
    source_root.mkdir()
    artifact = source_root / "artifact.txt"
    artifact.write_text(f"built from {source_root}/phatch", encoding="utf-8")
    monkeypatch.chdir(source_root)

    # When: the CLI scans without an explicit source-root option
    result = artifact_scan.main((str(artifact),))

    # Then: the default protects the selected source checkout
    assert result == 1


def test_cli_accepts_repeated_explicit_source_roots(tmp_path: Path) -> None:
    # Given: an artifact containing the second configured build root
    artifact = tmp_path / "artifact.txt"
    artifact.write_text(
        "built=C:\\work\\private build\\project\\module", encoding="utf-8"
    )

    # When: the CLI receives multiple explicit source/build roots
    result = artifact_scan.main(
        (
            "--source-root",
            "/different/source",
            "--source-root",
            "C:\\work\\private build\\project",
            str(artifact),
        )
    )

    # Then: every configured root participates in payload scanning
    assert result == 1
