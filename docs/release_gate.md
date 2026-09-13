# Release Verification and Artifacts

GitHub Actions is disabled for this repository. Workflow definitions are kept
for future use, but they are not release evidence and must not be enabled as
part of the 0.4.0 release. The stable release is gated by complete local runs of
`uv run --extra gui python scripts/verify.py` on macOS and Ubuntu, followed by
native GUI processing on both desktops and fresh-artifact validation on macOS.

The canonical gate checks the lock file, formatting, linting, typing, the full
test suite, 90% line and branch coverage, changed-module coverage, wheel and
source-distribution builds, and package metadata. Headless or focused test runs
are partial checks and do not satisfy the release gate.

## Stable 0.4.0 Scope

The published binary is `Phatch-0.4.0-macos-arm64.zip` for Apple silicon on
macOS 14 or newer. It is ad-hoc signed and is not Developer ID signed or
notarized. The release also provides the matching SHA-256 sidecar. Ubuntu 24.04
is validated as a source installation from the exact tag; no Linux binary is
published. Windows source support remains in the repository, but native Windows
verification and the unsigned portable Windows archive are deferred.

## Deferred Portable Windows Build

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

The portable build design is Windows x64 only. It is not an artifact of the
0.4.0 stable release and is not covered by the macOS and Ubuntu evidence above.
