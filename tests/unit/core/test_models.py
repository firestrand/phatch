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
Unit tests for phatch.core.models module.

Tests the base Action class and related utilities.
"""

import pytest
from phatch.core import models


class TestNegativeFunction:
    """Test the negative() utility function."""

    def test_positive_to_negative(self):
        """Convert positive string to negative."""
        assert models.negative('5') == '-5'

    def test_negative_to_positive(self):
        """Convert negative string to positive."""
        assert models.negative('-5') == '5'

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert models.negative('') == ''

    def test_whitespace_only(self):
        """Whitespace-only string should return same."""
        assert models.negative('   ') == '   '

    @pytest.mark.parametrize("input_val,expected", [
        ('10', '-10'),
        ('-10', '10'),
        ('0', '-0'),
        ('-0', '0'),
        ('3.14', '-3.14'),
        ('-3.14', '3.14'),
    ])
    def test_various_values(self, input_val, expected):
        """Test negative() with various numeric strings."""
        assert models.negative(input_val) == expected


class TestActionBase:
    """Test the base Action class."""

    def test_action_class_exists(self):
        """Action class should be importable."""
        assert models.Action is not None

    def test_action_has_required_attributes(self):
        """Action class should have required metadata attributes."""
        assert hasattr(models.Action, 'label')
        assert hasattr(models.Action, 'author')
        assert hasattr(models.Action, 'email')
        assert hasattr(models.Action, 'version')
        assert hasattr(models.Action, 'tags')
        assert hasattr(models.Action, '__doc__')

    def test_action_default_author(self):
        """Action should have default author."""
        assert models.Action.author == 'Stani'

    def test_action_default_email(self):
        """Action should have default email."""
        assert models.Action.email == 'spe.stani.be@gmail.com'

    def test_action_default_version(self):
        """Action should have default version."""
        assert models.Action.version == '0.1'

    def test_action_has_methods(self):
        """Action class should have required methods."""
        assert hasattr(models.Action, 'apply')
        assert callable(models.Action.apply)
        assert hasattr(models.Action, 'values')
        assert callable(models.Action.values)

    def test_action_has_init_staticmethod(self):
        """Action should have init staticmethod."""
        assert hasattr(models.Action, 'init')
        # Check it's callable (staticmethod)
        assert callable(models.Action.init)

    def test_action_default_all_layers(self):
        """Action should have all_layers attribute defaulting to False."""
        assert hasattr(models.Action, 'all_layers')
        assert models.Action.all_layers is False

    def test_action_default_cache(self):
        """Action should have cache attribute defaulting to False."""
        assert hasattr(models.Action, 'cache')
        assert models.Action.cache is False

    def test_action_default_valid_last(self):
        """Action should have valid_last attribute defaulting to False."""
        assert hasattr(models.Action, 'valid_last')
        assert models.Action.valid_last is False

    def test_action_default_tags(self):
        """Action should have tags attribute as list."""
        assert hasattr(models.Action, 'tags')
        assert isinstance(models.Action.tags, list)

    def test_action_default_tags_hidden(self):
        """Action should have tags_hidden attribute as list."""
        assert hasattr(models.Action, 'tags_hidden')
        assert isinstance(models.Action.tags_hidden, list)

    def test_action_default_metadata(self):
        """Action should have metadata attribute as list."""
        assert hasattr(models.Action, 'metadata')
        assert isinstance(models.Action.metadata, list)


class TestActionInheritance:
    """Test that Action class can be inherited properly."""

    def test_can_create_subclass(self):
        """Should be able to create Action subclass."""
        class CustomAction(models.Action):
            label = 'Test Action'
            author = 'Test Author'
            version = '1.0'

        assert CustomAction.label == 'Test Action'
        assert CustomAction.author == 'Test Author'
        assert CustomAction.version == '1.0'

    def test_subclass_inherits_defaults(self):
        """Subclass should inherit default attributes."""
        class MinimalAction(models.Action):
            label = 'Minimal'

        assert MinimalAction.all_layers is False
        assert MinimalAction.cache is False
        assert isinstance(MinimalAction.tags, list)

    def test_subclass_can_override_defaults(self):
        """Subclass should be able to override defaults."""
        class CustomAction(models.Action):
            label = 'Custom'
            all_layers = True
            cache = True

        assert CustomAction.all_layers is True
        assert CustomAction.cache is True
