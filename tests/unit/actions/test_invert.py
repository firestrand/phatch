"""Unit tests for phatch.actions.invert module.

Tests the Invert color action.

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
from phatch.actions import invert


class TestInvertAction:
    """Test the Invert action class metadata."""

    def test_action_exists(self):
        """Invert action class should exist."""
        assert hasattr(invert, 'Action')
        assert invert.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = invert.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = invert.Action()
        assert 'invert' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(invert.Action, 'pil')
        assert callable(invert.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(invert.Action, 'init')
        assert callable(invert.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = invert.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestInvertInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = invert.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert 'Amount' in fields or any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = invert.Action()
        fields = {}
        action.interface(fields)

        # Get the Amount field (handle translation)
        amount_field = None
        for key, value in fields.items():
            if 'amount' in key.lower():
                amount_field = value
                break

        assert amount_field is not None
        # SliderField is from formField module
        assert type(amount_field).__name__ == 'SliderField'


class TestInvertPilFunction:
    """Test the invert() PIL function."""

    def test_invert_function_exists(self):
        """invert function should exist."""
        assert hasattr(invert, 'invert')
        assert callable(invert.invert)

    def test_invert_full_amount_rgb(self, rgb_image):
        """Invert RGB image with amount=100."""
        # Initialize module first
        invert.init()

        result = invert.invert(rgb_image, amount=100)

        # Result should be an Image
        assert isinstance(result, Image.Image)
        # Should have same size
        assert result.size == rgb_image.size
        # Red (255,0,0) should become Cyan (0,255,255)
        pixel = result.getpixel((50, 50))
        assert pixel[0] < 50  # Red channel inverted (was 255, now ~0)
        assert pixel[1] > 200  # Green channel inverted (was 0, now ~255)
        assert pixel[2] > 200  # Blue channel inverted (was 0, now ~255)

    def test_invert_partial_amount_rgb(self, rgb_image):
        """Invert RGB image with partial amount (50%)."""
        invert.init()

        result = invert.invert(rgb_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

        # With 50% blend, colors should be between original and inverted
        pixel = result.getpixel((50, 50))
        # Should be blend of red (255,0,0) and cyan (0,255,255)
        # So roughly (127, 127, 127) - grayish
        assert 100 < pixel[0] < 180  # Blended red channel
        assert 100 < pixel[1] < 180  # Blended green channel
        assert 100 < pixel[2] < 180  # Blended blue channel

    def test_invert_preserves_alpha(self, rgba_image):
        """Invert RGBA image preserves alpha channel."""
        invert.init()

        result = invert.invert(rgba_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode in ('RGBA', 'LA')

        # Alpha values should be preserved
        # Check a semi-transparent pixel
        pixel_with_alpha = result.getpixel((25, 25))
        if len(pixel_with_alpha) == 4:
            assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_invert_grayscale(self, grayscale_image):
        """Invert grayscale image."""
        invert.init()

        result = invert.invert(grayscale_image, amount=100)

        assert isinstance(result, Image.Image)
        # 128 gray should become ~127 gray (inverted)
        pixel = result.getpixel((50, 50))
        # Grayscale is single value or tuple with one value
        if isinstance(pixel, tuple):
            pixel = pixel[0]
        assert 100 < pixel < 155  # Inverted ~128

    def test_invert_gradient(self, gradient_image):
        """Invert gradient image."""
        invert.init()

        result = invert.invert(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Left side was dark, should be light after invert
        left_pixel = result.getpixel((10, 50))
        # Right side was light, should be dark after invert
        right_pixel = result.getpixel((90, 50))

        left_brightness = sum(left_pixel) / 3
        right_brightness = sum(right_pixel) / 3

        # After inversion, left should be brighter than right
        assert left_brightness > right_brightness


class TestInvertEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_invert_amount_zero(self, rgb_image):
        """Invert with amount=0 should return near-original."""
        invert.init()

        # amount=0 is theoretically no change, but might blend differently
        # Let's use amount=1 (minimum from interface)
        result = invert.invert(rgb_image, amount=1)

        assert isinstance(result, Image.Image)
        # Should be mostly original
        pixel = result.getpixel((50, 50))
        # Should be very close to red (255,0,0)
        assert pixel[0] > 250

    def test_invert_amount_100(self, rgb_image):
        """Invert with amount=100 should fully invert."""
        invert.init()

        result = invert.invert(rgb_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully inverted to cyan
        pixel = result.getpixel((50, 50))
        assert pixel[0] < 10
        assert pixel[1] > 245
        assert pixel[2] > 245

    def test_invert_small_image(self, small_image):
        """Invert works with small images."""
        invert.init()

        result = invert.invert(small_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_invert_large_image(self, large_image):
        """Invert works with large images."""
        invert.init()

        result = invert.invert(large_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size


class TestInvertIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_invert(self, rgb_image):
        """Action.pil should call invert function."""
        invert.init()

        # Action.pil is staticmethod pointing to invert.invert
        result = invert.Action.pil(rgb_image, amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually inverted
        pixel = result.getpixel((50, 50))
        assert pixel[0] < 50  # Red inverted

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = invert.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = invert.Action()
        fields = {}
        # Should not raise
        action.interface(fields)
        assert len(fields) > 0
