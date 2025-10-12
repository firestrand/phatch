"""Unit tests for phatch.actions.minimum module.

Tests the Minimum action (apply minimum filter).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import minimum
from PIL import Image


class TestMinimumAction:
    """Test the Minimum action class metadata."""

    def test_action_exists(self):
        """Minimum action class should exist."""
        assert hasattr(minimum, 'Action')
        assert minimum.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = minimum.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = minimum.Action()
        assert 'minimum' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(minimum.Action, 'init')
        assert callable(minimum.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(minimum.Action, 'pil')
        assert callable(minimum.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = minimum.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = minimum.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestMinimumInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_two_fields(self):
        """Minimum should have two parameters."""
        action = minimum.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_defines_radius_field(self):
        """interface should define Radius parameter."""
        action = minimum.Action()
        fields = {}
        action.interface(fields)

        assert any('radius' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = minimum.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestMinimumInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(minimum, 'init')
        assert callable(minimum.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        minimum.init()

        # Should have loaded Image, ImageFilter, imtools
        assert hasattr(minimum, 'Image')
        assert hasattr(minimum, 'ImageFilter')
        assert hasattr(minimum, 'imtools')


class TestMinimumFunction:
    """Test the minimum() function."""

    def test_minimum_function_exists(self):
        """minimum function should exist."""
        assert hasattr(minimum, 'minimum')
        assert callable(minimum.minimum)

    def test_minimum_returns_image(self):
        """minimum should return Image object."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_radius_1(self):
        """minimum should apply filter with radius 1."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 1, 100)

        # Result should be same size
        assert result.size == (100, 100)

    def test_minimum_with_radius_3(self):
        """minimum should apply filter with radius 3."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 3, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_radius_5(self):
        """minimum should apply filter with radius 5."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_amount_less_than_100(self):
        """minimum should blend when amount < 100."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% blend with filtered image
        result = minimum.minimum(image, 1, 50)

        assert isinstance(result, Image.Image)

    def test_minimum_with_full_amount(self):
        """minimum should use filtered image directly when amount=100."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_minimum_amount(self):
        """minimum should handle minimum amount (1%)."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 1, 1)

        assert isinstance(result, Image.Image)

    def test_minimum_with_rgba_image(self):
        """minimum should handle RGBA images."""
        minimum.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_preserves_size(self):
        """minimum should preserve image size."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = minimum.minimum(image, 3, 100)

        assert result.size == (100, 100)


class TestMinimumEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_minimum_with_small_image(self):
        """minimum should handle small images."""
        minimum.init()

        image = Image.new('RGB', (10, 10), 'red')
        result = minimum.minimum(image, 1, 100)

        # Should maintain size
        assert result.size == (10, 10)

    def test_minimum_with_large_image(self):
        """minimum should handle large images."""
        minimum.init()

        image = Image.new('RGB', (500, 500), 'red')
        result = minimum.minimum(image, 1, 100)

        assert result.size == (500, 500)

    def test_minimum_with_small_radius(self):
        """minimum should work with minimum radius."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # Note: MinFilter requires radius > 0
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_large_radius(self):
        """minimum should handle large radius."""
        minimum.init()

        image = Image.new('RGB', (100, 100), 'red')
        # MinFilter has size limitations - use radius 5 as a safe large value
        result = minimum.minimum(image, 5, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_grayscale_image(self):
        """minimum should handle grayscale images."""
        minimum.init()

        image = Image.new('L', (100, 100), 128)
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)

    def test_minimum_with_p_mode_image(self):
        """minimum should handle palette mode images."""
        minimum.init()

        image = Image.new('P', (100, 100))
        result = minimum.minimum(image, 1, 100)

        assert isinstance(result, Image.Image)


class TestMinimumIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = minimum.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = minimum.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = minimum.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_minimum(self):
        """Action documentation mentions minimum or pixel."""
        action = minimum.Action()
        doc_lower = action.__doc__.lower()
        assert 'minimum' in doc_lower or 'pixel' in doc_lower

    def test_action_pil_is_minimum(self):
        """Action.pil should be minimum function."""
        assert minimum.Action.pil == minimum.minimum
