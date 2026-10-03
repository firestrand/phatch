# Phatch - PHoto bATCH Processor

**Batch process your photos with just one click!**

Phatch is a powerful, cross-platform photo batch processing application that enables you to resize, rotate, apply watermarks, shadows, rounded corners, perspective effects, and much more to entire photo collections.

## ✨ Features

- **50+ Image Actions**: Resize, rotate, crop, watermark, shadow, reflection, borders, effects, and more
- **GUI & Console Modes**: Interactive desktop application or command-line batch processing
- **Cross-Platform Source**: Linux, macOS, and Windows code, with release
  support limited to the platforms explicitly verified for each release
- **Action Lists**: Save and reuse your favorite batch processing workflows
- **Image Inspector**: View detailed EXIF/IPTC metadata
- **Droplet Mode**: Drag and drop images onto saved action lists
- **Plugin Architecture**: Easily extend with custom actions using Python and Pillow

## 🚀 Quick Start

### Requirements

- **CPython 3.12-3.14**
- **Pillow** (Python Imaging Library fork)
- **wxPython 4.x** (Phoenix) - for GUI mode

### Running Phatch

```bash
# Installed console and GUI entry points
phatch --help
phatch-gui

# Console mode (no GUI required)
phatch <actionlist.phatch> <image_files>

# Image inspector
phatch-gui --inspect <image_file>

# Droplet mode
phatch-gui --droplet <actionlist.phatch> <image_files>
```

`bin/phatch` remains a source-checkout compatibility wrapper for `phatch`.
Runtime action lists, images, fonts, masks, highlights, perspective data,
compiled locales, HTML documentation, and Blender support files are package
resources and do not depend on the current working directory.

**Note**: On first run, Phatch scans for system fonts and creates a cache at `~/phatch/fonts.cache` for faster subsequent launches.

See [Action Lists and Automation](docs/action_list_schema.md) for the versioned
schema, read-only preflight, JSON report, resume, capability, and exit-code
contracts.

See [Release Verification and Artifacts](docs/release_gate.md) for the current
release evidence, platform scope, optional capabilities, and artifact scanning.

The [0.5 usability candidate guide](docs/usability_050.md) documents the new
preview, action-list history, keyboard shortcuts, report v2 migration, six
starter workflows, and verified user-local Ubuntu launcher procedure. The 0.5
candidate is not published; this link describes a development candidate, not a
downloadable release.

### Installation

macOS 14 or newer on Apple silicon can use the ad-hoc-signed application from
the [v0.4.0 release](https://github.com/firestrand/phatch/releases/tag/v0.4.0).
Download both files, verify the checksum, extract the archive, and move the app:

```bash
shasum -a 256 -c Phatch-0.4.0-macos-arm64.zip.sha256
ditto -x -k Phatch-0.4.0-macos-arm64.zip Phatch-0.4.0
mv Phatch-0.4.0/Phatch.app /Applications/
open /Applications/Phatch.app
```

The application is ad-hoc signed, not Developer ID signed or notarized. On the
first launch, macOS may require Control-clicking `Phatch.app`, choosing Open,
and confirming Open. Do not disable Gatekeeper globally.

Ubuntu 24.04 source installations require Python development headers and
wxPython build dependencies supplied by the operating system. For the published
0.4.0 release, install from a clean checkout of the exact stable tag:

```bash
git clone --branch v0.4.0 --depth 1 https://github.com/firestrand/phatch.git
cd phatch
uv venv --python 3.12
uv sync --locked --extra gui
uv run phatch --help
uv run phatch-gui
```

The project is not published to PyPI as part of this release. The tag-bound
source checkout above and the macOS archive are the supported 0.4.0 inputs.
For an authorized local 0.5 candidate checkout or wheel, follow the
[Ubuntu user-local installation](docs/usability_050.md#ubuntu-2404-user-local-installation)
instructions; do not substitute a nonexistent 0.5 tag or remote download.

## 🧪 Testing

```bash
# Create the reproducible GUI-enabled development environment
uv sync --locked --dev --extra gui

# Run the canonical local gate, including automated native GUI tests and 90% coverage
uv run --extra gui python scripts/verify.py

# An automated runner must identify the comparison base explicitly
CI=1 uv run --extra gui python scripts/verify.py --base-ref origin/master

# Run the headless suite only; this is partial testing, not a coverage pass
uv run pytest --no-cov --ignore=tests/unit/pywx \
  --ignore=tests/integration/test_gui_smoke.py \
  --ignore=tests/integration/test_windows_gui_runtime.py
```

The GUI tests are scripted and guarded against human input. GitHub Actions is
disabled for this repository, so the 0.4.0 release is gated by complete local
macOS and Ubuntu runs of `scripts/verify.py`, including the same 90% line,
branch, and changed-module thresholds. Windows remains supported source code
but was not natively verified for 0.4.0, and no Windows binary is published.
Local coverage checks derive changed production modules directly from Git, so
new or unlisted files cannot bypass the changed-module threshold.

## 📚 Documentation

- **Action Lists**: Pre-configured batch processing recipes shipped as package data
- **Reliable Batch Workflows**: Planning, journals, workers and export policies in [`docs/BATCH_PROCESSING.md`](docs/BATCH_PROCESSING.md)
- **0.5 Usability Candidate**: Preview, history, workflows, reports, and Ubuntu setup in [`docs/usability_050.md`](docs/usability_050.md)
- **Developer Guide**: See `CLAUDE.md` for architecture and plugin development
- **License**: See `COPYING` for GPL v3 license details
- **Credits**: See `AUTHORS` file

## 🏗️ Architecture

Phatch uses a modular plugin architecture:

- **phatch/core/**: Batch processing engine and API
- **phatch/actions/**: 50+ image processing action plugins
- **phatch/pyWx/**: wxPython GUI application
- **phatch/console/**: Command-line interface
- **phatch/lib/**: Shared utilities and libraries

Each action is a self-contained plugin that declares its parameters and implements image processing using Pillow.

## 🔧 Development Status

**✅ Python 3 Migration Complete!**

Phatch has been successfully migrated from Python 2 to Python 3 with full functionality:

- ✅ CPython 3.12-3.14 compatible
- ✅ wxPython 4.x Phoenix support
- ✅ Pillow (modern PIL fork) integration
- ✅ Automated unit, integration, GUI, and release-gate tests
- ✅ PEP8 compliant codebase

## 🤝 Contributing

Phatch is open source and welcomes contributions!

- **Write Actions**: Create custom image processing plugins using Pillow
- **Report Issues**: Use the issue tracker for bugs and feature requests
- **Submit Pull Requests**: Follow PEP8 style guidelines and include tests

## 📝 License

Phatch is licensed under the **GNU General Public License v3** (GPL v3).

- ✅ 100% free and open source
- ✅ No limitations, no time-outs, no nags
- ✅ No adware, no banner ads, no spyware

See the `COPYING` file for full license details.

## 🌟 Credits

All credits are in the `AUTHORS` file or in the Help > About dialog box.

Original development: (c) 2007-2008 www.stani.be

---

**Phatch** - Making batch photo processing simple and powerful! 📸
