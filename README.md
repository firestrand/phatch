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

- **Python 3.x** (3.8+ recommended)
- **Pillow** (Python Imaging Library fork)
- **wxPython 4.x** (Phoenix) - for GUI mode

### Running Phatch

```bash
# GUI mode (default)
python bin/phatch

# Console mode (no GUI required)
python bin/phatch --console <actionlist.phatch> <image_files>

# Image inspector
python bin/phatch --inspect <image_file>

# Droplet mode
python bin/phatch --droplet <actionlist.phatch> <image_files>
```

**Note**: On first run, Phatch scans for system fonts and creates a cache at `~/phatch/fonts.cache` for faster subsequent launches.

### Installation

```bash
# Install dependencies
pip install Pillow wxPython

# Install Phatch (Linux/macOS)
python setup.py install
```

## 🧪 Testing

```bash
# Run all tests
cd tests
python -m pytest

# Run PEP8 style checks
cd tests
python pep8_test.py
```

## 📚 Documentation

- **Action Lists**: Pre-configured batch processing recipes in `data/actionlists/`
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

- ✅ Python 3.8+ compatible
- ✅ wxPython 4.x Phoenix support
- ✅ Pillow (modern PIL fork) integration
- ✅ 2173 passing tests
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
