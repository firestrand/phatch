#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
Unit tests for phatch.core.ct module.

Tests constants and re-exported configuration values.
This module re-exports path constants from config for convenience.
"""

import builtins

# Initialize translation system for tests
# The ct module uses _t() which expects _ to be defined globally
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x  # No-op translation for tests

from phatch.core import ct


class TestCoreConstants:
    """Test basic ct module constants."""

    def test_module_exists(self):
        """ct module should be importable."""
        assert ct is not None

    def test_has_platform_constants(self):
        """ct should have platform detection constants."""
        assert hasattr(ct, 'PLATFORM')
        assert hasattr(ct, 'LINUX')
        assert hasattr(ct, 'WINDOWS')
        assert hasattr(ct, 'MAC')

    def test_has_application_metadata(self):
        """ct should have application metadata constants."""
        assert hasattr(ct, 'TITLE')
        assert hasattr(ct, 'COPYRIGHT')
        assert hasattr(ct, 'DESCRIPTION')
        assert hasattr(ct, 'CONTACT')
        assert hasattr(ct, 'LICENSE')

    def test_has_file_extension(self):
        """ct should have file extension constant."""
        assert hasattr(ct, 'EXTENSION')
        assert isinstance(ct.EXTENSION, str)


class TestUserPathReExports:
    """
    Test that ct re-exports USER_* path constants from config.

    These are re-exported for convenience so other modules can access
    them via ct.USER_PATH instead of importing from config directly.
    """

    def test_has_user_path(self):
        """ct should re-export USER_PATH from config."""
        assert hasattr(ct, 'USER_PATH')
        assert ct.USER_PATH is not None

    def test_has_user_data_path(self):
        """ct should re-export USER_DATA_PATH from config."""
        assert hasattr(ct, 'USER_DATA_PATH')

    def test_has_user_config_path(self):
        """ct should re-export USER_CONFIG_PATH from config."""
        assert hasattr(ct, 'USER_CONFIG_PATH')

    def test_has_user_cache_path(self):
        """ct should re-export USER_CACHE_PATH from config."""
        assert hasattr(ct, 'USER_CACHE_PATH')

    def test_has_user_actionlists_path(self):
        """ct should re-export USER_ACTIONLISTS_PATH from config."""
        assert hasattr(ct, 'USER_ACTIONLISTS_PATH')

    def test_has_user_actions_path(self):
        """ct should re-export USER_ACTIONS_PATH from config."""
        assert hasattr(ct, 'USER_ACTIONS_PATH')

    def test_has_user_bin_path(self):
        """ct should re-export USER_BIN_PATH from config."""
        assert hasattr(ct, 'USER_BIN_PATH')

    def test_has_user_fonts_path(self):
        """ct should re-export USER_FONTS_PATH from config."""
        assert hasattr(ct, 'USER_FONTS_PATH')

    def test_has_user_highlights_path(self):
        """ct should re-export USER_HIGHLIGHTS_PATH from config."""
        assert hasattr(ct, 'USER_HIGHLIGHTS_PATH')

    def test_has_user_log_path(self):
        """ct should re-export USER_LOG_PATH from config."""
        assert hasattr(ct, 'USER_LOG_PATH')

    def test_has_user_masks_path(self):
        """ct should re-export USER_MASKS_PATH from config."""
        assert hasattr(ct, 'USER_MASKS_PATH')

    def test_has_user_settings_path(self):
        """ct should re-export USER_SETTINGS_PATH from config."""
        assert hasattr(ct, 'USER_SETTINGS_PATH')

    def test_has_user_watermarks_path(self):
        """ct should re-export USER_WATERMARKS_PATH from config."""
        assert hasattr(ct, 'USER_WATERMARKS_PATH')


class TestPathsAreStrings:
    """Test that all USER_* paths are strings or paths."""

    def test_user_path_is_string(self):
        """USER_PATH should be a string."""
        assert isinstance(ct.USER_PATH, str)

    def test_user_paths_are_strings(self):
        """All USER_*_PATH constants should be strings."""
        path_attrs = [
            'USER_PATH', 'USER_DATA_PATH', 'USER_CONFIG_PATH',
            'USER_CACHE_PATH', 'USER_ACTIONLISTS_PATH', 'USER_ACTIONS_PATH',
            'USER_BIN_PATH', 'USER_FONTS_PATH', 'USER_HIGHLIGHTS_PATH',
            'USER_LOG_PATH', 'USER_MASKS_PATH', 'USER_SETTINGS_PATH',
            'USER_WATERMARKS_PATH'
        ]
        for attr in path_attrs:
            assert hasattr(ct, attr), f"Missing attribute: {attr}"
            value = getattr(ct, attr)
            assert isinstance(value, str), f"{attr} should be a string, got {type(value)}"
