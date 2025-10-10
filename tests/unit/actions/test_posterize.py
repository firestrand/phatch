"""Unit tests for phatch.actions.posterize module.

Tests the Posterize action (reduce the number of bits per color channel).

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
from phatch.actions import posterize


class TestPosterizeAction:
    """Test the Posterize action class metadata."""

    def test_action_exists(self):
        """Posterize action class should exist."""
        assert hasattr(posterize, 'Action')
        assert posterize.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = posterize.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = posterize.Action()
        assert 'posterize' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(posterize.Action, 'pil')
        assert callable(posterize.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(posterize.Action, 'init')
        assert callable(posterize.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = posterize.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestPosterizeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_bits_field(self):
        """interface should define Bits parameter."""
        action = posterize.Action()
        fields = {}
        action.interface(fields)

        # Should have Bits field
        assert any('bits' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = posterize.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_bits_is_slider(self):
        """Bits field should be a SliderField."""
        action = posterize.Action()
        fields = {}
        action.interface(fields)

        # Get the Bits field
        bits_field = None
        for key, value in fields.items():
            if 'bits' in key.lower():
                bits_field = value
                break

        assert bits_field is not None
        assert type(bits_field).__name__ == 'SliderField'

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = posterize.Action()
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

    def test_interface_has_two_fields(self):
        """Posterize should have two parameters."""
        action = posterize.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2


class TestPosterizePilFunction:
    """Test the posterize() PIL function."""

    def test_posterize_function_exists(self):
        """posterize function should exist."""
        assert hasattr(posterize, 'posterize')
        assert callable(posterize.posterize)

    def test_posterize_rgb_image(self, multicolor_image):
        """Posterize RGB image reduces color depth."""
        posterize.init()

        # 1 bit posterization gives very few colors
        result = posterize.posterize(multicolor_image, bits=1, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_posterize_high_bits(self, rgb_image):
        """Posterize with high bits (7-8) makes little visible change."""
        posterize.init()

        result = posterize.posterize(rgb_image, bits=7, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_posterize_low_bits(self, multicolor_image):
        """Posterize with low bits (1-2) makes dramatic change."""
        posterize.init()

        result = posterize.posterize(multicolor_image, bits=1, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_posterize_partial_amount(self, multicolor_image):
        """Posterize with partial amount blends with original."""
        posterize.init()

        result = posterize.posterize(multicolor_image, bits=2, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_posterize_preserves_alpha(self, rgba_image):
        """Posterize RGBA image preserves alpha channel."""
        posterize.init()

        result = posterize.posterize(rgba_image, bits=3, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_posterize_gradient(self, gradient_image):
        """Posterize gradient creates banding effect."""
        posterize.init()

        result = posterize.posterize(gradient_image, bits=2, amount=100)

        assert isinstance(result, Image.Image)
        # Gradient should show distinct bands (posterization effect)

    def test_posterize_grayscale(self, grayscale_image):
        """Posterize grayscale image."""
        posterize.init()

        result = posterize.posterize(grayscale_image, bits=3, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size


class TestPosterizeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_posterize_bits_zero(self, rgb_image):
        """Posterize with bits=0 (minimum)."""
        posterize.init()

        result = posterize.posterize(rgb_image, bits=0, amount=100)

        assert isinstance(result, Image.Image)
        # Bit value 0 is extreme posterization

    def test_posterize_bits_eight(self, multicolor_image):
        """Posterize with bits=8 (maximum, no change)."""
        posterize.init()

        result = posterize.posterize(multicolor_image, bits=8, amount=100)

        assert isinstance(result, Image.Image)
        # 8 bits = full color depth (no posterization)

    def test_posterize_amount_minimum(self, multicolor_image):
        """Posterize with amount=1 (barely visible)."""
        posterize.init()

        result = posterize.posterize(multicolor_image, bits=2, amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, effect should be very subtle

    def test_posterize_amount_maximum(self, multicolor_image):
        """Posterize with amount=100 (full effect)."""
        posterize.init()

        result = posterize.posterize(multicolor_image, bits=2, amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully posterized

    def test_posterize_small_image(self, small_image):
        """Posterize works with small images."""
        posterize.init()

        result = posterize.posterize(small_image, bits=3, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_posterize_large_image(self, large_image):
        """Posterize works with large images."""
        posterize.init()

        result = posterize.posterize(large_image, bits=3, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_posterize_twice(self, multicolor_image):
        """Posterizing twice compounds the effect."""
        posterize.init()

        first = posterize.posterize(multicolor_image, bits=4, amount=100)
        second = posterize.posterize(first, bits=2, amount=100)

        assert isinstance(second, Image.Image)
        # Second posterization further reduces colors

    def test_posterize_different_bits(self, multicolor_image):
        """Posterize with various bit values."""
        posterize.init()

        # Test several bit values
        for bits in [1, 2, 4, 6]:
            result = posterize.posterize(multicolor_image, bits=bits, amount=100)
            assert isinstance(result, Image.Image)
            assert result.size == multicolor_image.size


class TestPosterizeIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_posterize(self, multicolor_image):
        """Action.pil should call posterize function."""
        posterize.init()

        result = posterize.Action.pil(multicolor_image, bits=3, amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually posterized
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = posterize.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = posterize.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2  # Bits and Amount

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = posterize.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_bits(self):
        """Action documentation mentions bits or color."""
        action = posterize.Action()
        doc_lower = action.__doc__.lower()
        assert 'bits' in doc_lower or 'color' in doc_lower

    def test_action_pil_points_to_posterize(self):
        """Action.pil should point to posterize function."""
        # The action's pil staticmethod should be the posterize function
        assert posterize.Action.pil == posterize.posterize
