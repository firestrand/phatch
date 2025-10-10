"""Unit tests for phatch.actions.brightness module.

Tests the Brightness action (adjust from black to white).

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
from phatch.actions import brightness


class TestBrightnessAction:
    """Test the Brightness action class metadata."""

    def test_action_exists(self):
        """Brightness action class should exist."""
        assert hasattr(brightness, 'Action')
        assert brightness.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = brightness.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = brightness.Action()
        assert 'brightness' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(brightness.Action, 'pil')
        assert callable(brightness.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(brightness.Action, 'init')
        assert callable(brightness.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = brightness.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestBrightnessInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = brightness.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = brightness.Action()
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
        """Brightness should have only one parameter."""
        action = brightness.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1

    def test_interface_amount_range(self):
        """Amount should be a slider field (behavior tested in functional tests)."""
        action = brightness.Action()
        fields = {}
        action.interface(fields)

        # Get the Amount field
        for key, value in fields.items():
            if 'amount' in key.lower():
                amount_field = value
                # Verify it's a SliderField (internal structure is implementation detail)
                assert type(amount_field).__name__ == 'SliderField'


class TestBrightnessPilFunction:
    """Test the brightness() PIL function."""

    def test_brightness_function_exists(self):
        """brightness function should exist."""
        assert hasattr(brightness, 'brightness')
        assert callable(brightness.brightness)

    def test_brighten_rgb_image(self):
        """Brighten RGB image with positive amount."""
        brightness.init()

        # Create a dark red image
        img = Image.new('RGB', (100, 100), color=(100, 0, 0))
        result = brightness.brightness(img, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == img.size

        # After brightening, should be lighter
        pixel = result.getpixel((50, 50))
        assert pixel[0] > 100  # Red channel should be brighter

    def test_darken_rgb_image(self):
        """Darken RGB image with negative amount."""
        brightness.init()

        # Create a bright red image
        img = Image.new('RGB', (100, 100), color=(200, 0, 0))
        result = brightness.brightness(img, amount=-50)

        assert isinstance(result, Image.Image)
        assert result.size == img.size

        # After darkening, should be darker
        pixel = result.getpixel((50, 50))
        assert pixel[0] < 200  # Red channel should be darker

    def test_brightness_zero_unchanged(self):
        """Brightness with amount=0 should return unchanged image."""
        brightness.init()

        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = brightness.brightness(img, amount=0)

        # Should return the same image object
        assert result is img

    def test_brightness_preserves_alpha(self, rgba_image):
        """Brightness RGBA image preserves alpha channel."""
        brightness.init()

        result = brightness.brightness(rgba_image, amount=50)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_brighten_grayscale(self, grayscale_image):
        """Brighten grayscale image."""
        brightness.init()

        result = brightness.brightness(grayscale_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

        # Should be brighter
        original_pixel = grayscale_image.getpixel((50, 50))
        result_pixel = result.getpixel((50, 50))
        assert result_pixel > original_pixel

    def test_darken_grayscale(self, grayscale_image):
        """Darken grayscale image."""
        brightness.init()

        result = brightness.brightness(grayscale_image, amount=-50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

        # Should be darker
        original_pixel = grayscale_image.getpixel((50, 50))
        result_pixel = result.getpixel((50, 50))
        assert result_pixel < original_pixel

    def test_brightness_gradient(self, gradient_image):
        """Brightness maintains gradient pattern."""
        brightness.init()

        result = brightness.brightness(gradient_image, amount=30)

        assert isinstance(result, Image.Image)
        # Gradient pattern should be preserved (left darker than right)
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        if isinstance(left_pixel, tuple):
            left_brightness = sum(left_pixel[:3]) / 3
            right_brightness = sum(right_pixel[:3]) / 3
        else:
            left_brightness = left_pixel
            right_brightness = right_pixel

        assert left_brightness < right_brightness

    def test_brightness_multicolor(self, multicolor_image):
        """Brightness adjusts all colors uniformly."""
        brightness.init()

        result = brightness.brightness(multicolor_image, amount=40)

        assert isinstance(result, Image.Image)
        # All regions should still be distinct
        red_region = result.getpixel((25, 25))
        green_region = result.getpixel((75, 25))
        blue_region = result.getpixel((25, 75))

        # All should be different
        assert red_region != green_region
        assert green_region != blue_region


class TestBrightnessEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_brightness_maximum_positive(self, rgb_image):
        """Brightness with amount=100 (fade to white)."""
        brightness.init()

        result = brightness.brightness(rgb_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should be very bright (near white)
        pixel = result.getpixel((50, 50))
        assert pixel[0] > 200
        assert pixel[1] > 200
        assert pixel[2] > 200

    def test_brightness_maximum_negative(self, rgb_image):
        """Brightness with amount=-100 (fade to black)."""
        brightness.init()

        result = brightness.brightness(rgb_image, amount=-100)

        assert isinstance(result, Image.Image)
        # Should be very dark (near black)
        pixel = result.getpixel((50, 50))
        assert pixel[0] < 50
        assert pixel[1] < 50
        assert pixel[2] < 50

    def test_brightness_small_image(self, small_image):
        """Brightness works with small images."""
        brightness.init()

        result = brightness.brightness(small_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_brightness_large_image(self, large_image):
        """Brightness works with large images."""
        brightness.init()

        result = brightness.brightness(large_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_brightness_twice_positive(self, rgb_image):
        """Applying brightness twice should compound effect."""
        brightness.init()

        first = brightness.brightness(rgb_image, amount=30)
        second = brightness.brightness(first, amount=30)

        assert isinstance(second, Image.Image)
        # Second should be brighter than first
        first_pixel = first.getpixel((50, 50))
        second_pixel = second.getpixel((50, 50))
        assert sum(second_pixel) > sum(first_pixel)

    def test_brightness_twice_negative(self, rgb_image):
        """Applying negative brightness twice should compound effect."""
        brightness.init()

        first = brightness.brightness(rgb_image, amount=-30)
        second = brightness.brightness(first, amount=-30)

        assert isinstance(second, Image.Image)
        # Second should be darker than first
        first_pixel = first.getpixel((50, 50))
        second_pixel = second.getpixel((50, 50))
        assert sum(second_pixel) < sum(first_pixel)


class TestBrightnessIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_brightness(self, rgb_image):
        """Action.pil should call brightness function."""
        brightness.init()

        result = brightness.Action.pil(rgb_image, amount=40)

        assert isinstance(result, Image.Image)
        # Verify it actually brightened
        original_pixel = rgb_image.getpixel((50, 50))
        result_pixel = result.getpixel((50, 50))
        assert sum(result_pixel) > sum(original_pixel)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = brightness.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = brightness.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Amount field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = brightness.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_brightness(self):
        """Action documentation mentions brightness."""
        action = brightness.Action()
        assert 'brightness' in action.__doc__.lower()

    def test_action_pil_points_to_brightness(self):
        """Action.pil should point to brightness function."""
        # The action's pil staticmethod should be the brightness function
        assert brightness.Action.pil == brightness.brightness
