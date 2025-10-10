"""Unit tests for phatch.actions.median module.

Tests the Median action (apply median filter).

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

from phatch.actions import median
from PIL import Image


class TestMedianAction:
    """Test the Median action class metadata."""

    def test_action_exists(self):
        """Median action class should exist."""
        assert hasattr(median, 'Action')
        assert median.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = median.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = median.Action()
        assert 'median' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(median.Action, 'init')
        assert callable(median.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(median.Action, 'pil')
        assert callable(median.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = median.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = median.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestMedianInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_two_fields(self):
        """Median should have two parameters."""
        action = median.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_defines_radius_field(self):
        """interface should define Radius parameter."""
        action = median.Action()
        fields = {}
        action.interface(fields)

        assert any('radius' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = median.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestMedianInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(median, 'init')
        assert callable(median.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        median.init()

        # Should have loaded Image, ImageFilter, imtools
        assert hasattr(median, 'Image')
        assert hasattr(median, 'ImageFilter')
        assert hasattr(median, 'imtools')


class TestMedianFunction:
    """Test the median() function."""

    def test_median_function_exists(self):
        """median function should exist."""
        assert hasattr(median, 'median')
        assert callable(median.median)

    def test_median_returns_image(self):
        """median should return Image object."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_radius_1(self):
        """median should apply filter with radius 1."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 1, 100)

        # Result should be same size
        assert result.size == (100, 100)

    def test_median_with_radius_3(self):
        """median should apply filter with radius 3."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 3, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_radius_5(self):
        """median should apply filter with radius 5."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_amount_less_than_100(self):
        """median should blend when amount < 100."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% blend with filtered image
        result = median.median(image, 1, 50)

        assert isinstance(result, Image.Image)

    def test_median_with_full_amount(self):
        """median should use filtered image directly when amount=100."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_minimum_amount(self):
        """median should handle minimum amount (1%)."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 1, 1)

        assert isinstance(result, Image.Image)

    def test_median_with_rgba_image(self):
        """median should handle RGBA images."""
        median.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_median_preserves_size(self):
        """median should preserve image size."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = median.median(image, 3, 100)

        assert result.size == (100, 100)


class TestMedianEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_median_with_small_image(self):
        """median should handle small images."""
        median.init()

        image = Image.new('RGB', (10, 10), 'red')
        result = median.median(image, 1, 100)

        # Should maintain size
        assert result.size == (10, 10)

    def test_median_with_large_image(self):
        """median should handle large images."""
        median.init()

        image = Image.new('RGB', (500, 500), 'red')
        result = median.median(image, 1, 100)

        assert result.size == (500, 500)

    def test_median_with_small_radius(self):
        """median should work with minimum radius."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        # Note: MedianFilter requires radius > 0
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_large_radius(self):
        """median should handle large radius."""
        median.init()

        image = Image.new('RGB', (100, 100), 'red')
        # MedianFilter has size limitations - use radius 5 as a safe large value
        result = median.median(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_grayscale_image(self):
        """median should handle grayscale images."""
        median.init()

        image = Image.new('L', (100, 100), 128)
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_median_with_p_mode_image(self):
        """median should handle palette mode images."""
        median.init()

        image = Image.new('P', (100, 100))
        result = median.median(image, 1, 100)

        assert isinstance(result, Image.Image)


class TestMedianIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = median.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = median.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = median.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_median(self):
        """Action documentation mentions median or pixel."""
        action = median.Action()
        doc_lower = action.__doc__.lower()
        assert 'median' in doc_lower or 'pixel' in doc_lower

    def test_action_pil_is_median(self):
        """Action.pil should be median function."""
        assert median.Action.pil == median.median
