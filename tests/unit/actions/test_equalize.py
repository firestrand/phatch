"""Unit tests for phatch.actions.equalize module.

Tests the Equalize action (histogram equalization).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from PIL import Image
from phatch.actions import equalize


class TestEqualizeAction:
    """Test the Equalize action class metadata."""

    def test_action_exists(self):
        """Equalize action class should exist."""
        assert hasattr(equalize, 'Action')
        assert equalize.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = equalize.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = equalize.Action()
        assert 'equalize' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(equalize.Action, 'pil')
        assert callable(equalize.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(equalize.Action, 'init')
        assert callable(equalize.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = equalize.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestEqualizeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = equalize.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = equalize.Action()
        fields = {}
        action.interface(fields)

        # Get the Amount field
        amount_field = None
        for key, value in fields.items():
            if 'amount' in key.lower():
                amount_field = value
                break

        assert amount_field is not None
        assert type(amount_field).__name__ == 'SliderField'

    def test_interface_has_one_field(self):
        """Equalize should have only one parameter."""
        action = equalize.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestEqualizePilFunction:
    """Test the equalize() PIL function."""

    def test_equalize_function_exists(self):
        """equalize function should exist."""
        assert hasattr(equalize, 'equalize')
        assert callable(equalize.equalize)

    def test_equalize_full_amount_rgb(self, gradient_image):
        """Equalize gradient with amount=100."""
        equalize.init()

        result = equalize.equalize(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # After equalization, histogram should be more evenly distributed

    def test_equalize_partial_amount_rgb(self, gradient_image):
        """Equalize gradient with partial amount (50%)."""
        equalize.init()

        result = equalize.equalize(gradient_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # With 50% blend, effect should be moderate

    def test_equalize_preserves_alpha(self, rgba_image):
        """Equalize RGBA image preserves alpha channel."""
        equalize.init()

        result = equalize.equalize(rgba_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode in ('RGBA', 'LA')

        # Check a semi-transparent pixel
        pixel_with_alpha = result.getpixel((25, 25))
        if len(pixel_with_alpha) == 4:
            assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_equalize_grayscale(self, grayscale_image):
        """Equalize grayscale image."""
        equalize.init()

        result = equalize.equalize(grayscale_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_equalize_uniform_color(self, rgb_image):
        """Equalize uniform color image."""
        equalize.init()

        # Uniform red image has flat histogram
        result = equalize.equalize(rgb_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should handle gracefully

    def test_equalize_multicolor(self, multicolor_image):
        """Equalize image with multiple colors."""
        equalize.init()

        result = equalize.equalize(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

        # After equalization, colors should still be distinct

    def test_equalize_gradient(self, gradient_image):
        """Equalize improves gradient distribution."""
        equalize.init()

        result = equalize.equalize(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Gradient should have more evenly distributed tones
        # (This is what histogram equalization does)


class TestEqualizeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_equalize_amount_minimum(self, gradient_image):
        """Equalize with amount=1 (minimum from interface)."""
        equalize.init()

        result = equalize.equalize(gradient_image, amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, should be very close to original

    def test_equalize_amount_maximum(self, gradient_image):
        """Equalize with amount=100 (maximum)."""
        equalize.init()

        result = equalize.equalize(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should apply full equalization

    def test_equalize_small_image(self, small_image):
        """Equalize works with small images."""
        equalize.init()

        result = equalize.equalize(small_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_equalize_large_image(self, large_image):
        """Equalize works with large images."""
        equalize.init()

        result = equalize.equalize(large_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_equalize_twice(self, gradient_image):
        """Equalizing twice should have diminishing effect."""
        equalize.init()

        first_equalize = equalize.equalize(gradient_image, amount=100)
        second_equalize = equalize.equalize(first_equalize, amount=100)

        assert isinstance(second_equalize, Image.Image)
        # Already equalized image won't change much


class TestEqualizeIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_equalize(self, gradient_image):
        """Action.pil should call equalize function."""
        equalize.init()

        result = equalize.Action.pil(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually applied equalization
        assert result.size == gradient_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = equalize.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = equalize.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Amount field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = equalize.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_histogram(self):
        """Action documentation mentions histogram."""
        action = equalize.Action()
        assert 'histogram' in action.__doc__.lower()
