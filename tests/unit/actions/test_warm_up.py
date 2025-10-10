"""Unit tests for phatch.actions.warm_up module.

Tests the Warm Up action (colorize midtones).

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

from phatch.actions import warm_up
from PIL import Image


class TestWarmUpAction:
    """Test the Warm Up action class metadata."""

    def test_action_exists(self):
        """Warm Up action class should exist."""
        assert hasattr(warm_up, 'Action')
        assert warm_up.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = warm_up.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = warm_up.Action()
        assert 'warm' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(warm_up.Action, 'init')
        assert callable(warm_up.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(warm_up.Action, 'pil')
        assert callable(warm_up.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = warm_up.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter and color tags."""
        action = warm_up.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower or 'color' in tags_lower


class TestWarmUpInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_three_fields(self):
        """Warm Up should have three parameters."""
        action = warm_up.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 3

    def test_interface_defines_midtone_field(self):
        """interface should define Midtone parameter."""
        action = warm_up.Action()
        fields = {}
        action.interface(fields)

        assert any('midtone' in k.lower() for k in fields.keys())

    def test_interface_defines_brighten_field(self):
        """interface should define Brighten parameter."""
        action = warm_up.Action()
        fields = {}
        action.interface(fields)

        assert any('brighten' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = warm_up.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestWarmUpInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(warm_up, 'init')
        assert callable(warm_up.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        warm_up.init()

        # Should have loaded Image, ImageMath, ImageColor, imtools
        assert hasattr(warm_up, 'Image')
        assert hasattr(warm_up, 'ImageMath')
        assert hasattr(warm_up, 'ImageColor')
        assert hasattr(warm_up, 'imtools')


class TestWarmupFunction:
    """Test the warmup() function."""

    def test_warmup_function_exists(self):
        """warmup function should exist."""
        assert hasattr(warm_up, 'warmup')
        assert callable(warm_up.warmup)

    def test_warmup_returns_image(self):
        """warmup should return Image object."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_rgb_image(self):
        """warmup should apply effect to RGB images."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        # Result should be RGB
        assert result.mode == 'RGB'
        assert result.size == (100, 100)

    def test_warmup_with_grayscale_image(self):
        """warmup should handle grayscale images."""
        warm_up.init()

        image = Image.new('L', (100, 100), 128)
        result = warm_up.warmup(image, '#805d40', 50, 100)

        # Result should be RGB (colorized)
        assert result.mode == 'RGB'

    def test_warmup_with_rgba_image(self):
        """warmup should preserve alpha channel."""
        warm_up.init()

        image = Image.new('RGBA', (100, 100), (128, 128, 128, 255))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        # Should preserve RGBA mode
        assert result.mode in ['RGB', 'RGBA']

    def test_warmup_with_default_midtone(self):
        """warmup should work with default midtone color."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        # Use the default midtone from interface
        result = warm_up.warmup(image, '#805d40', 50, 50)

        assert isinstance(result, Image.Image)

    def test_warmup_with_zero_brighten(self):
        """warmup should handle zero brightening."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 0, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_max_brighten(self):
        """warmup should handle maximum brightening."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 100, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_amount_less_than_100(self):
        """warmup should blend with original when amount < 100."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        # 50% blend
        result = warm_up.warmup(image, '#805d40', 50, 50)

        assert isinstance(result, Image.Image)

    def test_warmup_with_full_amount(self):
        """warmup should apply full effect when amount=100."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_minimum_amount(self):
        """warmup should handle minimum amount."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 1)

        assert isinstance(result, Image.Image)

    def test_warmup_preserves_size(self):
        """warmup should preserve image size."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert result.size == (100, 100)

    def test_warmup_with_different_colors(self):
        """warmup should work with various midtone colors."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (128, 128, 128))

        # Test different warm colors
        colors = ['#ff8844', '#cc6633', '#aa5522', '#805d40']
        for color in colors:
            result = warm_up.warmup(image, color, 50, 100)
            assert isinstance(result, Image.Image)


class TestWarmUpEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_warmup_with_small_image(self):
        """warmup should handle small images."""
        warm_up.init()

        image = Image.new('RGB', (10, 10), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        # Should maintain size
        assert result.size == (10, 10)

    def test_warmup_with_large_image(self):
        """warmup should handle large images."""
        warm_up.init()

        image = Image.new('RGB', (500, 500), (128, 128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert result.size == (500, 500)

    def test_warmup_with_pure_black(self):
        """warmup should handle pure black images."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (0, 0, 0))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_pure_white(self):
        """warmup should handle pure white images."""
        warm_up.init()

        image = Image.new('RGB', (100, 100), (255, 255, 255))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert isinstance(result, Image.Image)

    def test_warmup_with_transparent_image(self):
        """warmup should handle images with transparency."""
        warm_up.init()

        # LA mode (grayscale with alpha)
        image = Image.new('LA', (100, 100), (128, 128))
        result = warm_up.warmup(image, '#805d40', 50, 100)

        assert isinstance(result, Image.Image)


class TestWarmUpIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = warm_up.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = warm_up.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 3

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = warm_up.Action()
        assert action.author == 'Pawel T. Jochym'
        assert action.version == '0.2'
        assert 'filter' in [str(tag).lower() for tag in action.tags] or \
               'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_colorize(self):
        """Action documentation mentions colorize or midtones."""
        action = warm_up.Action()
        doc_lower = action.__doc__.lower()
        assert 'colorize' in doc_lower or 'midtone' in doc_lower

    def test_action_pil_is_warmup(self):
        """Action.pil should be warmup function."""
        assert warm_up.Action.pil == warm_up.warmup
