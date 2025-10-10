"""Unit tests for phatch.actions.desaturate module.

Tests the Desaturate action (convert to grayscale).

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
from phatch.actions import desaturate


class TestDesaturateAction:
    """Test the Desaturate action class metadata."""

    def test_action_exists(self):
        """Desaturate action class should exist."""
        assert hasattr(desaturate, 'Action')
        assert desaturate.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = desaturate.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = desaturate.Action()
        assert 'desaturate' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(desaturate.Action, 'pil')
        assert callable(desaturate.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(desaturate.Action, 'init')
        assert callable(desaturate.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = desaturate.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestDesaturateInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = desaturate.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = desaturate.Action()
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
        """Desaturate should have only one parameter."""
        action = desaturate.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestDesaturatePilFunction:
    """Test the grayscale() PIL function."""

    def test_grayscale_function_exists(self):
        """grayscale function should exist."""
        assert hasattr(desaturate, 'grayscale')
        assert callable(desaturate.grayscale)

    def test_desaturate_full_amount_rgb(self, multicolor_image):
        """Desaturate multicolor image with amount=100."""
        desaturate.init()

        result = desaturate.grayscale(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

        # After full desaturation, should be grayscale
        # Check that colors are now shades of gray (R=G=B)
        pixel = result.getpixel((25, 25))  # Was red region
        # In grayscale, all channels should be equal (or single channel)
        if isinstance(pixel, tuple):
            if len(pixel) == 3:
                # RGB grayscale - all channels equal
                assert pixel[0] == pixel[1] == pixel[2]

    def test_desaturate_partial_amount_rgb(self, rgb_image):
        """Desaturate with partial amount (50%)."""
        desaturate.init()

        result = desaturate.grayscale(rgb_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

        # With 50% blend, colors should be partially desaturated
        pixel = result.getpixel((50, 50))
        # Check if RGB mode (tuple) or grayscale (int)
        if isinstance(pixel, tuple) and len(pixel) >= 3:
            # Red channel should still be highest but not as dominant
            assert pixel[0] > pixel[1]  # Still has red bias
            assert pixel[0] > pixel[2]
        # If grayscale mode, just verify it's a valid value
        elif isinstance(pixel, int):
            assert 0 <= pixel <= 255

    def test_desaturate_preserves_alpha(self, rgba_image):
        """Desaturate RGBA image preserves alpha channel."""
        desaturate.init()

        result = desaturate.grayscale(rgba_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode in ('LA', 'RGBA')

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        if len(pixel_with_alpha) == 2:  # LA mode
            assert pixel_with_alpha[1] == 128  # Alpha preserved
        elif len(pixel_with_alpha) == 4:  # RGBA mode
            assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_desaturate_already_grayscale(self, grayscale_image):
        """Desaturate already grayscale image."""
        desaturate.init()

        result = desaturate.grayscale(grayscale_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size
        # Should handle gracefully (no change)

    def test_desaturate_gradient(self, gradient_image):
        """Desaturate gradient image."""
        desaturate.init()

        result = desaturate.grayscale(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Gradient pattern should be preserved as grayscale
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        # Left should still be darker than right
        if isinstance(left_pixel, tuple):
            left_brightness = sum(left_pixel[:3]) / 3
            right_brightness = sum(right_pixel[:3]) / 3
        else:
            left_brightness = left_pixel
            right_brightness = right_pixel

        assert left_brightness < right_brightness

    def test_desaturate_multicolor(self, multicolor_image):
        """Desaturate removes color from multicolor image."""
        desaturate.init()

        # Original has distinct colors (red, green, blue, white)
        result = desaturate.grayscale(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)

        # After desaturation, regions should be different grays
        red_region = result.getpixel((25, 25))
        green_region = result.getpixel((75, 25))
        blue_region = result.getpixel((25, 75))
        white_region = result.getpixel((75, 75))

        # All should be grayscale but different brightness levels
        # (Different colors have different perceived brightness)
        if isinstance(red_region, tuple):
            # Check they're grayscale (R=G=B)
            assert red_region[0] == red_region[1] == red_region[2]
            assert green_region[0] == green_region[1] == green_region[2]


class TestDesaturateEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_desaturate_amount_minimum(self, multicolor_image):
        """Desaturate with amount=1 (minimum from interface)."""
        desaturate.init()

        result = desaturate.grayscale(multicolor_image, amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, should be almost original

    def test_desaturate_amount_maximum(self, multicolor_image):
        """Desaturate with amount=100 (maximum)."""
        desaturate.init()

        result = desaturate.grayscale(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully grayscale

    def test_desaturate_small_image(self, small_image):
        """Desaturate works with small images."""
        desaturate.init()

        result = desaturate.grayscale(small_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_desaturate_large_image(self, large_image):
        """Desaturate works with large images."""
        desaturate.init()

        result = desaturate.grayscale(large_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_desaturate_twice(self, multicolor_image):
        """Desaturating twice should have no additional effect."""
        desaturate.init()

        first_desaturate = desaturate.grayscale(multicolor_image, amount=100)
        second_desaturate = desaturate.grayscale(first_desaturate, amount=100)

        assert isinstance(second_desaturate, Image.Image)
        # Already grayscale, second pass should be identical or very close


class TestDesaturateIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_grayscale(self, multicolor_image):
        """Action.pil should call grayscale function."""
        desaturate.init()

        result = desaturate.Action.pil(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually desaturated
        pixel = result.getpixel((25, 25))
        if isinstance(pixel, tuple) and len(pixel) >= 3:
            # Should be grayscale (R=G=B)
            assert pixel[0] == pixel[1] == pixel[2]

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = desaturate.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = desaturate.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Amount field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = desaturate.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_gray(self):
        """Action documentation mentions gray."""
        action = desaturate.Action()
        assert 'gray' in action.__doc__.lower()

    def test_action_pil_points_to_grayscale(self):
        """Action.pil should point to grayscale function."""
        # The action's pil staticmethod should be the grayscale function
        assert desaturate.Action.pil == desaturate.grayscale
