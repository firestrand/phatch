"""Unit tests for phatch.actions.maximum module.

Tests the Maximum action (apply maximum filter).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch, MagicMock
import pytest

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import maximum
from PIL import Image


class TestMaximumAction:
    """Test the Maximum action class metadata."""

    def test_action_exists(self):
        """Maximum action class should exist."""
        assert hasattr(maximum, 'Action')
        assert maximum.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = maximum.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = maximum.Action()
        assert 'maximum' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(maximum.Action, 'init')
        assert callable(maximum.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(maximum.Action, 'pil')
        assert callable(maximum.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = maximum.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = maximum.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestMaximumInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_two_fields(self):
        """Maximum should have two parameters."""
        action = maximum.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_defines_radius_field(self):
        """interface should define Radius parameter."""
        action = maximum.Action()
        fields = {}
        action.interface(fields)

        assert any('radius' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = maximum.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestMaximumInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(maximum, 'init')
        assert callable(maximum.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        maximum.init()

        # Should have loaded Image, ImageFilter, imtools
        assert hasattr(maximum, 'Image')
        assert hasattr(maximum, 'ImageFilter')
        assert hasattr(maximum, 'imtools')


class TestMaximumFunction:
    """Test the maximum() function."""

    def test_maximum_function_exists(self):
        """maximum function should exist."""
        assert hasattr(maximum, 'maximum')
        assert callable(maximum.maximum)

    def test_maximum_returns_image(self):
        """maximum should return Image object."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_radius_1(self):
        """maximum should apply filter with radius 1."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 1, 100)

        # Result should be same size
        assert result.size == (100, 100)

    def test_maximum_with_radius_3(self):
        """maximum should apply filter with radius 3."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 3, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_radius_5(self):
        """maximum should apply filter with radius 5."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_amount_less_than_100(self):
        """maximum should blend when amount < 100."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% blend with filtered image
        result = maximum.maximum(image, 1, 50)

        assert isinstance(result, Image.Image)

    def test_maximum_with_full_amount(self):
        """maximum should use filtered image directly when amount=100."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_minimum_amount(self):
        """maximum should handle minimum amount (1%)."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 1, 1)

        assert isinstance(result, Image.Image)

    def test_maximum_with_rgba_image(self):
        """maximum should handle RGBA images."""
        maximum.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_preserves_size(self):
        """maximum should preserve image size."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = maximum.maximum(image, 3, 100)

        assert result.size == (100, 100)


class TestMaximumEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_maximum_with_small_image(self):
        """maximum should handle small images."""
        maximum.init()

        image = Image.new('RGB', (10, 10), 'red')
        result = maximum.maximum(image, 1, 100)

        # Should maintain size
        assert result.size == (10, 10)

    def test_maximum_with_large_image(self):
        """maximum should handle large images."""
        maximum.init()

        image = Image.new('RGB', (500, 500), 'red')
        result = maximum.maximum(image, 1, 100)

        assert result.size == (500, 500)

    def test_maximum_with_small_radius(self):
        """maximum should work with minimum radius."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # Note: MaxFilter requires radius > 0
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_large_radius(self):
        """maximum should handle large radius."""
        maximum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # MaxFilter has size limitations - use radius 5 as a safe large value
        result = maximum.maximum(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_grayscale_image(self):
        """maximum should handle grayscale images."""
        maximum.init()

        image = Image.new('L', (100, 100), 128)
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_maximum_with_p_mode_image(self):
        """maximum should handle palette mode images."""
        maximum.init()

        image = Image.new('P', (100, 100))
        result = maximum.maximum(image, 1, 100)

        assert isinstance(result, Image.Image)


class TestMaximumIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = maximum.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = maximum.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = maximum.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_maximum(self):
        """Action documentation mentions maximum or pixel."""
        action = maximum.Action()
        doc_lower = action.__doc__.lower()
        assert 'maximum' in doc_lower or 'pixel' in doc_lower

    def test_action_pil_is_maximum(self):
        """Action.pil should be maximum function."""
        assert maximum.Action.pil == maximum.maximum
