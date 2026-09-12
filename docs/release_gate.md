# CI and Portable Artifacts

The GitHub Actions workflow is configured to validate CPython 3.11-3.13 on
Windows, Linux, and macOS. It separates fast Python 3.12 quality checks, the
non-GUI OS/Python matrix, the same 3-by-3 OS/Python distribution matrix, native
Windows GUI behavior, Windows path failures, optional-capability contracts, the
Windows portable build, and a second job that downloads and re-tests the
uploaded portable archive.

All external actions are pinned to full immutable commits listed with their
official tag API sources in `.github/action-pins.txt`. The workflow grants only
`contents: read`. It uploads workflow artifacts for review but does not create a
release, publish a package, sign binaries, or upload to a public registry.

## Portable Windows Build

`packaging/phatch.spec` produces unsigned x64 one-folder `Phatch.exe` and
`Phatch-GUI.exe` applications on native Windows with Python 3.12. The reviewed
spec collects the `phatch_assets` resource package, dynamic action and service
modules, Pillow and wxPython hooks/native libraries, license files, and the
spawn-worker bootstrap.

The sibling `portable-data` directory opts into portable storage through the
existing `PHATCH_USER_CONFIG_DIR`, `PHATCH_USER_DATA_DIR`, and
`PHATCH_USER_CACHE_DIR` path injection points. Removing that directory restores
normal platform-specific user directories. No machine-wide registry writes are
part of startup.

`scripts/portable_smoke.py` must run on native Windows. It opens and closes the
real GUI window, executes public console entry points, loads a generated action
list, runs capability and preflight checks, processes generated images through
spawned workers, exercises recovery twice, checks packaged resources indirectly
through registry/preflight execution, and rejects writes outside portable data.

## Release Metadata and Scanning

`scripts/release_manifest.py` generates `SHA256SUMS`, an SPDX 2.3 JSON SBOM, and
a tab-separated runtime dependency/license report. It reads direct requirements
from the supplied wheel metadata, applies explicitly selected extras and current
environment markers, and resolves the installed transitive runtime closure. A
missing selected dependency fails generation instead of producing a placeholder.
Checksum verification is
repeated after workflow download before extraction. `scripts/artifact_scan.py`
walks directories and reads ZIP and tar members to reject unsafe archive paths,
development-only files, local home paths, and common credential/private-key
shapes. Scanner or manifest errors fail the job; there are no ignore lists for
reported findings.

Supported runtime dependencies are Pillow, platformdirs, and Rich. wxPython,
pywin32, pyexiv2, pillow-heif, and external ImageMagick, Blender, jpegtran, or
exiftran adapters remain optional capability boundaries. The portable artifact
includes wxPython and pywin32 but does not bundle those external executables or
promise HEIF/AVIF support when their providers/codecs are unavailable.

The portable build is Windows x64 only. The workflow is configured to validate
macOS and Linux source, sdist, and wheel installations; no native portable
application is claimed for those targets.
