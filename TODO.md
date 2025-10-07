# Phatch Python 3.x Migration TODO List

This document outlines the steps needed to upgrade Phatch from Python 2.x to Python 3.x.

## Migration Strategy

We can use automated tools to help with the Python 2 to 3 migration:

1. **2to3 Tool**: Python's built-in conversion tool that can automatically fix most Python 2 syntax to be compatible with Python 3.
   - Usage: `2to3 -w <file_or_directory>` to write changes directly to files
   - Can be run with specific fixers: `2to3 -f print -f except <file>` 
   - Available in Python 3.x installations

2. **python-modernize**: A wrapper around 2to3 that produces code compatible with both Python 2 and 3 using the six library.
   - Better for gradual migration if we need to maintain Python 2 compatibility during transition
   - Install with: `pip install modernize`
   - Usage: `python-modernize -w <file_or_directory>`

For this project, we'll primarily use the 2to3 tool since we're doing a direct migration to Python 3 without needing to maintain Python 2 compatibility.

## Initial Assessment

- [x] Identify Python 2.x specific code that needs to be updated
- [x] Identify dependencies that need to be updated or replaced
- [ ] Determine compatibility issues with external libraries

## Core Python 3 Migration Tasks

1. [x] Remove Python 2.x version check in `phatch/phatch.py` and `bin/phatch`
2. [x] Update print statements to use parentheses (Python 3 syntax)
3. [x] Replace `xrange()` with `range()`
4. [x] Update dictionary methods:
   - [x] Replace `.iteritems()` with `.items()`
   - [x] Replace `.iterkeys()` with `.keys()`
   - [x] Replace `.itervalues()` with `.values()`
5. [ ] Update string handling:
   - [x] Review and update `unicode()` usage
   - [ ] Update string encoding/decoding methods
   - [ ] Review `lib/unicoding.py` module
6. [x] Update imports:
   - [x] Replace `cStringIO` with `io.StringIO` or `io.BytesIO`
   - [x] Replace `urllib` and `urllib2` with `urllib.parse`, `urllib.request`, etc.
   - [x] Update other standard library imports that have changed

## PIL/Pillow Migration

1. [x] Replace PIL with Pillow (PIL fork for Python 3)
2. [x] Update PIL import statements:
   - [x] Check for custom PIL modules in `phatch/other/pil_1_1_6/`
   - [x] Update PIL imports in action modules
   - [x] Update PIL imports in core modules

## wxPython Migration

1. [x] Update wxPython imports and usage:
   - [x] Identify current wxPython version
   - [x] Update to wxPython 4.x (Phoenix) which supports Python 3
   - [x] Fix any API changes between wxPython Classic and Phoenix

## Testing and Validation

1. [x] Set up a test environment with Python 3.x
2. [ ] Run unit tests and fix failures
3. [ ] Test basic functionality:
   - [ ] GUI operation
   - [ ] Image processing actions
   - [ ] Batch processing
4. [ ] Test on different platforms (Linux, macOS, Windows)

## Documentation and Packaging

1. [ ] Update setup.py for Python 3 compatibility
2. [ ] Update installation instructions
3. [ ] Update README and other documentation
4. [ ] Update version information

## Additional Tasks

1. [ ] Consider using modern Python tools:
   - [ ] Add type hints
   - [ ] Use pathlib instead of os.path
   - [ ] Consider using virtual environments for development
2. [ ] Review and update any custom modules in `phatch/other/`
3. [ ] Check for any platform-specific code that might need updates

## Remaining Issues

1. [ ] Fix string exceptions in `phatch/lib/pyWx/treeDragDrop.py` (Line 81: `raise 'no order'`)
2. [ ] Review and fix any other warnings from 2to3 