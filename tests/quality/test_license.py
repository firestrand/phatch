#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2010  www.stani.be
# Copyright (C) 2015-2025  Travis Silvers
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
# Follows PEP8

"""
License header test for Phatch.

Checks that all Python files have proper GPL v3+ license headers.

This test requires the 'licensecheck' command from the devscripts package:
  - Linux: sudo apt-get install devscripts
  - macOS: brew install devscripts (or skip this test)
  - Windows: Not commonly available (test will be skipped)

The test is marked as optional and will be skipped if licensecheck
is not available on the system.
"""

import re
import shutil
import sys
import time
from pathlib import Path

import pytest

# Add project root to path so we can import phatch
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phatch.lib import system

# Regex to parse licensecheck output
RE_FILE = re.compile(
    r'(?P<filename>.+?):\s(?P<license>.+?)\s*'
    r'\n(\s+\[(?P<copyright>.+?)\])?'
)

# Check if licensecheck is available
HAS_LICENSECHECK = shutil.which('licensecheck') is not None


def get_error(d):
    """
    Validate license and copyright information.

    Args:
        d: Dictionary with 'license' and 'copyright' keys from licensecheck output

    Returns:
        Error message string if validation fails, None if valid
    """
    # Skip auto-generated files
    if 'GENERATED' in d['license']:
        return None

    # Check license
    if d['license'] != 'GPL (v3 or later)':
        return 'License should be "GPL (v3 or later)".'

    # Check copyright exists
    if d['copyright'] is None:
        return 'Copyright is missing.'

    # Copyright should include original author or current maintainer
    # Accept either www.stani.be (original) or Travis Silvers (current maintainer)
    if not ('www.stani.be' in d['copyright'] or 'Travis Silvers' in d['copyright']):
        return "Copyright should include 'www.stani.be' or 'Travis Silvers'"

    return None


@pytest.mark.requires_external
@pytest.mark.skipif(
    not HAS_LICENSECHECK,
    reason="licensecheck command not available (install devscripts package)"
)
def test_license_headers():
    """Test that all Python files have proper GPL v3+ license headers."""
    time_start = time.time()
    errors = []
    total = 0

    # Get project root
    # Script is now in tests/quality/, so parent.parent.parent = project root
    project_root = Path(__file__).parent.parent.parent

    # Run licensecheck
    stdout, stderr = system.shell([
        'licensecheck',
        '--recursive',
        '--copyright',
        '--ignore', 'phatch/other|wxGlade|license|.venv|build|dist',
        str(project_root),
    ])

    # Parse output
    for match in RE_FILE.finditer(stdout):
        d = match.groupdict()
        d['error'] = get_error(d)

        # Skip api.py (known to have different format)
        if d['error'] and 'api.py' not in d['filename']:
            error_msg = (
                f"{d['filename']}:\n"
                f"- {d['error']}\n"
                f"- license: {d['license']}\n"
                f"- copyright: {d['copyright']}\n"
            )
            print(error_msg)
            errors.append(d['filename'])

        total += 1

    elapsed = time.time() - time_start
    print(f"Ran {total} license tests in {elapsed:.3f}s")

    # Assert no errors
    if errors:
        pytest.fail(
            f"Found {len(errors)} file(s) with license/copyright issues:\n" +
            "\n".join(f"  - {e}" for e in errors)
        )


def main():
    """
    Run license check from command line.

    Exit codes:
        0: All files have proper licenses
        1: Some files have license issues or licensecheck not available
    """
    if not HAS_LICENSECHECK:
        print("ERROR: licensecheck command not found.")
        print("Install it with:")
        print("  Linux: sudo apt-get install devscripts")
        print("  macOS: brew install devscripts")
        print("\nAlternatively, run with pytest which will skip this test:")
        print("  pytest tests/license_test.py")
        sys.exit(1)

    try:
        test_license_headers()
        print("\n✓ All files pass license checks!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ License check failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
