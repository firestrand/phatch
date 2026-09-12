# Phatch - PHoto bATCH Processor

**Batch process your photos with just one click!**

Phatch is a powerful, cross-platform photo batch processing application that enables you to resize, rotate, apply watermarks, shadows, rounded corners, perspective effects, and much more to entire photo collections.

## ✨ Features

- **50+ Image Actions**: Resize, rotate, crop, watermark, shadow, reflection, borders, effects, and more
- **GUI & Console Modes**: Interactive desktop application or command-line batch processing
- **Cross-Platform**: Runs on Linux, macOS, and Windows
- **Action Lists**: Save and reuse your favorite batch processing workflows
- **Image Inspector**: View detailed EXIF/IPTC metadata
- **Droplet Mode**: Drag and drop images onto saved action lists
- **Plugin Architecture**: Easily extend with custom actions using Python and Pillow

## 🚀 Quick Start

### Requirements

- **CPython 3.11-3.13**
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

See [CI and Portable Artifacts](docs/release_gate.md) for supported CI targets,
unsigned Windows portable behavior, optional capabilities, manifests, and
artifact scanning.

### Installation

```bash
# Standard wheel install (uv is not required)
python -m pip install "Phatch[gui]"
```

## 🧪 Testing

```bash
# Create the reproducible GUI-enabled development environment
uv sync --locked --dev --extra gui

# Run the canonical local gate, including automated native GUI tests and 90% coverage
uv run --extra gui python scripts/verify.py

# CI must identify the comparison base explicitly
uv run --extra gui python scripts/verify.py --base-ref origin/master

# Run the headless suite only; this is partial testing, not a coverage pass
uv run pytest --no-cov --ignore=tests/unit/pywx \
  --ignore=tests/integration/test_gui_smoke.py \
  --ignore=tests/integration/test_windows_gui_runtime.py
```

The GUI tests are scripted and guarded against human input. CI combines raw
branch coverage from the required nine-job non-GUI matrix with the native
Windows GUI contributor before enforcing the same 90% global and changed-module
thresholds. Actual native Windows completion remains a downstream release gate;
local runs on other platforms do not constitute a native Windows claim.
Local coverage checks derive changed production modules directly from Git, so
new or unlisted files cannot bypass the changed-module threshold.

## 📚 Documentation

- **Action Lists**: Pre-configured batch processing recipes shipped as package data
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

- ✅ CPython 3.11-3.13 compatible
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
