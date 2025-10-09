#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2007-2008  www.stani.be
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
Doctest runner for Phatch modules.

Runs pytest with doctest support on core Phatch modules to verify
code examples in docstrings work correctly.

Modernized from nosetests to pytest for Python 3 compatibility.
"""

import subprocess
import sys
from pathlib import Path


# Modules to test for doctests
MODULES = ['actions', 'console', 'core', 'data', 'lib', 'pyWx']


def main():
    """Run doctests using pytest."""
    # Build pytest command
    pytest_args = [
        sys.executable, '-m', 'pytest',
        '--doctest-modules',  # Enable doctest
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
    ]

    # Platform-specific module exclusions
    # These modules have platform-specific code that may not work on all platforms
    ignore_patterns = []
    if sys.platform.startswith('win'):
        # Windows: ignore Linux-specific modules
        ignore_patterns.extend(['*/linux/*', '*/linux.py'])
    elif sys.platform.startswith('darwin'):
        # macOS: ignore Linux and Windows specific modules
        ignore_patterns.extend(['*/linux/*', '*/linux.py', '*/windows/*', '*/windows.py'])
    else:
        # Linux: ignore Windows-specific modules
        ignore_patterns.extend(['*/windows/*', '*/windows.py'])

    # Add ignore patterns to pytest args
    for pattern in ignore_patterns:
        pytest_args.extend(['--ignore-glob', pattern])

    # Change to phatch directory to run tests
    # Script is now in tests/quality/, so parent.parent.parent = project root
    project_root = Path(__file__).parent.parent.parent
    phatch_dir = project_root / 'phatch'

    # Add module paths
    module_paths = [str(phatch_dir / module) for module in MODULES]
    pytest_args.extend(module_paths)

    # Run pytest
    print(f"Running doctests with command: {' '.join(pytest_args)}")
    print(f"Working directory: {phatch_dir}")

    try:
        result = subprocess.run(
            pytest_args,
            cwd=project_root,
            check=False
        )
        return result.returncode
    except FileNotFoundError:
        print("ERROR: pytest not found. Install it with: pip install pytest")
        print("Or install all dev dependencies: pip install -r requirements-dev.txt")
        return 1
    except Exception as e:
        print(f"ERROR running doctests: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
