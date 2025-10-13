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
Code quality test for Phatch using Ruff.

Ruff is a fast, modern Python linter that checks code quality including:
- PEP8 style compliance
- Unused imports (F401)
- Unused variables (F841)
- Code correctness issues
- And many more quality checks

Configuration is in pyproject.toml at the project root.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


def test(dirname='..'):
    """
    Run ruff linter on the Phatch codebase.

    Args:
        dirname: Directory to check (default: '..' for project root)

    Returns:
        bool: True if violations found, False if clean
    """
    # Calculate target directory relative to this script's location
    # Script is now in tests/quality/, so parent.parent = project root
    script_dir = Path(__file__).parent
    if dirname == '..':
        # Default: check project root (parent.parent of quality directory)
        target_dir = script_dir.parent.parent
    elif dirname:
        # Check specific subdirectory relative to script location
        target_dir = (script_dir / dirname).resolve()
    else:
        # Empty string: check project root
        target_dir = script_dir.parent.parent

    # Build ruff command
    # --output-format=concise shows file:line:col: message format
    ruff_cmd = [
        sys.executable, '-m', 'ruff', 'check',
        str(target_dir),
        '--output-format=concise',
    ]

    print(f"Running ruff code quality checks on: {target_dir}")
    print(f"Command: {' '.join(ruff_cmd)}\n")

    try:
        if importlib.util.find_spec('ruff') is None:
            pytest.skip("ruff not installed in current environment")
        result = subprocess.run(
            ruff_cmd,
            cwd=target_dir,
            capture_output=True,
            text=True,
            check=False
        )

        # Ruff exits with 0 if no violations, 1 if violations found
        if result.returncode == 0:
            print("✓ All files pass code quality checks!")
            return False
        else:
            # Show the violations
            print("✗ Code quality violations found:\n")
            print(result.stdout)
            if result.stderr:
                print("Errors:")
                print(result.stderr)
            return True

    except FileNotFoundError:
        pytest.skip("ruff executable not found")
    except Exception as e:
        print(f"ERROR running ruff: {e}")
        sys.exit(1)


def test_code_quality():
    """
    Pytest test for code quality using ruff.

    This test will fail if any code quality violations are found.
    """
    has_violations = test('..')
    if has_violations:
        pytest.fail("Code quality violations found. Run 'ruff check --fix .' to auto-fix many issues.")


def main_with_exit(dirname='..'):
    """
    Run code quality checks and exit with appropriate code (for command-line use).

    Args:
        dirname: Directory to check (default: parent directory)

    Exit codes:
        0: All checks passed
        1: Violations found or error occurred
    """
    has_violations = test(dirname)
    if has_violations:
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main_with_exit('..')
