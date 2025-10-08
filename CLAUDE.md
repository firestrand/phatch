# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phatch (PHoto bATCH Processor) is a cross-platform photo batch processing application that enables users to resize, rotate, apply watermarks, shadows, rounded corners, perspective effects, and more to photo collections with GUI or console interfaces. The project is GPL v3 licensed.

**Current State**: ✅ Successfully migrated to Python 3.x! Application is functional and tested.

## Key Technologies

- **Python 3.x**: Project is currently being migrated from Python 2.x
- **Pillow (PIL)**: Image processing library (migrated from original PIL)
- **wxPython 4.x (Phoenix)**: GUI framework for cross-platform desktop interface
- **Platform Support**: Linux, macOS, Windows

## Running and Testing

### Running the Application

```bash
# GUI mode (default)
python bin/phatch

# Console mode (no GUI)
python bin/phatch --console <actionlist.phatch> <image_files>

# Image inspector
python bin/phatch --inspect <image_file>

# Droplet mode
python bin/phatch --droplet <actionlist> <image_files>
```

**Note**: On first run, Phatch scans for system fonts (in ~/Library/Fonts, /Library/Fonts, /System/Library/Fonts on macOS). This takes ~0.2 seconds and creates a cache at `~/phatch/fonts.cache` for faster subsequent launches.

### Testing

```bash
# Run PEP8 checks (project follows PEP8)
cd tests
python pep8_test.py

# Run tests from tests/ directory
cd tests
python -m pytest  # or your preferred test runner
```

### Installation

```bash
# Install using setup.py (Linux/macOS only)
python setup.py install

# Note: Windows installation uses a different process
```

## Project Architecture

### Core Components

- **phatch/core/**: Core batch processing engine
  - `api.py`: Main API for action list execution, imports/exports, error logging
  - `pil.py`: PIL/Pillow integration and image manipulation utilities
  - `models.py`: Base Action model class that all actions inherit from
  - `config.py`: Configuration and path initialization
  - `ct.py`: Core types and constants
  - `message.py`: Pub/sub messaging system for progress/status updates

- **phatch/actions/**: Image processing actions (50+ plugins)
  - Each file defines an `Action` class inheriting from `models.Action`
  - `common.py`: Shared utilities for actions
  - Actions use a declarative `interface()` method to define parameters
  - Actions implement a `pil()` staticmethod for the actual image processing

- **phatch/pyWx/**: wxPython GUI application
  - `gui.py`: Main GUI frame and application logic
  - Uses custom pubsub compatibility layer for wx.lib.pubsub
  - `wxGlade/`: UI layouts generated with wxGlade

- **phatch/console/**: Command-line interface
  - `console.py`: CLI implementation with progress display

- **phatch/lib/**: Shared libraries and utilities
  - `metadata.py`: EXIF/IPTC metadata handling (uses PyExiv2)
  - `imtools.py`: Image manipulation utilities
  - `formField.py`: Form field definitions for action parameters
  - `pyWx/`: wxPython-specific utilities
  - Platform-specific modules in `linux/`, `windows/` subdirectories

- **phatch/data/**: Application data and configuration
  - `info.py`: Project metadata (version, credits, setup.py info)
  - `version.py`: Version and date constants

- **data/**: Static resources
  - `actionlists/`: Pre-configured batch processing recipes (.phatch files)
  - `blender/`: Blender integration for 3D effects
  - `fonts/`, `masks/`, `highlights/`, `perspective/`: Image assets

### Action Plugin System

Actions are the heart of Phatch. Each action:
1. Inherits from `core.models.Action`
2. Defines metadata: `label`, `author`, `email`, `version`, `tags`, `__doc__`
3. Implements `interface(self, fields)` to declare user-configurable parameters
4. Implements static `pil(image, **params)` method for image processing
5. Optionally implements `init()` for lazy imports

Example action structure:
```python
class Action(models.Action):
    label = _t('Action Name')
    author = 'Name'
    email = 'email@example.com'
    version = '0.1'
    tags = [_t('category')]
    __doc__ = _t("Description")

    def interface(self, fields):
        fields[_t('Parameter')] = self.SomeField(default_value)

    @staticmethod
    def init():
        # Lazy imports here
        pass

    @staticmethod
    def pil(image, parameter_value):
        # Image processing logic
        return modified_image
```

### Messaging System

Phatch uses a pub/sub messaging pattern (`core.message`) for decoupling the processing engine from UI/console:
- `send()`: Publish messages
- `FrameReceiver`: Subscribe to and handle messages in GUI
- `ProgressReceiver`: Track batch processing progress

### Entry Points

- `bin/phatch`: Main executable script
- `phatch/app.py`: Command-line argument parsing and mode selection
- `phatch/phatch.py`: Legacy entry point
- Calls `config.init_config_paths()` to set up user directories

## Python 3 Migration Notes

✅ **Migration Complete!** The project has been successfully migrated from Python 2 to Python 3 using the 2to3 tool.

**Key changes completed:**
- Print statements → `print()` function
- `xrange()` → `range()`
- Dictionary iteration methods (`.iteritems()` → `.items()`, `.iterkeys()` → `.keys()`)
- Exception syntax: `except Exception, e` → `except Exception as e`
- `unicode()` handling updated
- PIL → Pillow (with proper `from PIL import` statements)
- wxPython Classic → wxPython 4.x Phoenix
- String imports: `cStringIO` → `io.StringIO/BytesIO`, `urllib`/`urllib2` → `urllib.parse`/`urllib.request`
- Relative imports: Added `.` prefix for intra-package imports
- String exceptions: `raise 'message'` → `raise Exception('message')`
- Regex patterns: Added raw string literals (`r''`) to avoid escape sequence warnings
- PIL.Image.VERSION compatibility: Added fallback to PIL.__version__ for Pillow 10+
- Hybrid imports: phatch.py supports both package and direct imports for test compatibility

**Migration branch:** `python3-migration-2to3`

**Remaining work:** See TODO.md for optional enhancements (tests, documentation updates, type hints).

## Code Style

- **Follows PEP8**: Run `tests/pep8_test.py` to verify compliance
- **Comment headers**: All files include GPL license header and "Follows PEP8" comment
- **Internationalization**: Use `_t()` for user-facing strings in code, `_()` for runtime translations
- **Imports**: Group into standard library, GUI-independent, GUI-dependent sections

## Development Guidelines

- New actions should be placed in `phatch/actions/` and follow the Action plugin pattern
- Action parameter fields are defined using methods like `SliderField()`, `FileField()`, `ChoiceField()`
- Image processing should use Pillow (imported as PIL for compatibility)
- Platform-specific code goes in `phatch/lib/{linux,windows}/` or `phatch/{linux,windows}/`
- GUI code is isolated to `phatch/pyWx/`, console to `phatch/console/`
