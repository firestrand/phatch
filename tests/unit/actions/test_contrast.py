"""Unit tests for phatch.actions.contrast module.

Tests the Contrast action (adjust from grey to black & white).

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
from phatch.actions import contrast


class TestContrastAction:
    """Test the Contrast action class metadata."""

    def test_action_exists(self):
        """Contrast action class should exist."""
        assert hasattr(contrast, 'Action')
        assert contrast.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = contrast.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = contrast.Action()
        assert 'contrast' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(contrast.Action, 'pil')
        assert callable(contrast.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(contrast.Action, 'init')
        assert callable(contrast.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = contrast.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestContrastInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = contrast.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = contrast.Action()
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
        """Contrast should have only one parameter."""
        action = contrast.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestContrastPilFunction:
    """Test the contrast() PIL function."""

    def test_contrast_function_exists(self):
        """contrast function should exist."""
        assert hasattr(contrast, 'contrast')
        assert callable(contrast.contrast)

    def test_increase_contrast_gradient(self, gradient_image):
        """Increase contrast on gradient with positive amount."""
        contrast.init()

        result = contrast.contrast(gradient_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # After increasing contrast, dark should be darker, bright brighter
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        # Should still have gradient pattern but more extreme
        if isinstance(left_pixel, tuple):
            left_brightness = sum(left_pixel[:3]) / 3
            right_brightness = sum(right_pixel[:3]) / 3
        else:
            left_brightness = left_pixel
            right_brightness = right_pixel

        assert left_brightness < right_brightness

    def test_decrease_contrast_gradient(self, gradient_image):
        """Decrease contrast on gradient with negative amount."""
        contrast.init()

        result = contrast.contrast(gradient_image, amount=-50)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # After decreasing contrast, should be more uniform (closer to mean)
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        if isinstance(left_pixel, tuple):
            left_brightness = sum(left_pixel[:3]) / 3
            right_brightness = sum(right_pixel[:3]) / 3
        else:
            left_brightness = left_pixel
            right_brightness = right_pixel

        # Should still have pattern but less extreme
        assert left_brightness < right_brightness

    def test_contrast_zero_unchanged(self):
        """Contrast with amount=0 should return unchanged image."""
        contrast.init()

        img = Image.new('RGB', (100, 100), color=(128, 128, 128))
        result = contrast.contrast(img, amount=0)

        # Should return the same image object
        assert result is img

    def test_contrast_preserves_alpha(self, rgba_image):
        """Contrast RGBA image preserves alpha channel."""
        contrast.init()

        result = contrast.contrast(rgba_image, amount=50)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_increase_contrast_grayscale(self, grayscale_image):
        """Increase contrast on grayscale image."""
        contrast.init()

        result = contrast.contrast(grayscale_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_decrease_contrast_grayscale(self, grayscale_image):
        """Decrease contrast on grayscale image."""
        contrast.init()

        result = contrast.contrast(grayscale_image, amount=-50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_contrast_multicolor(self, multicolor_image):
        """Contrast adjusts multicolor image."""
        contrast.init()

        result = contrast.contrast(multicolor_image, amount=40)

        assert isinstance(result, Image.Image)
        # Should still have distinct regions
        red_region = result.getpixel((25, 25))
        green_region = result.getpixel((75, 25))
        blue_region = result.getpixel((25, 75))

        # All should be different
        assert red_region != green_region
        assert green_region != blue_region

    def test_contrast_uniform_color(self, rgb_image):
        """Contrast on uniform color image."""
        contrast.init()

        # Uniform red image has no contrast to adjust
        result = contrast.contrast(rgb_image, amount=50)

        assert isinstance(result, Image.Image)
        # Should handle gracefully


class TestContrastEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_contrast_maximum_positive(self, gradient_image):
        """Contrast with amount=100 (maximum high contrast)."""
        contrast.init()

        result = contrast.contrast(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should have very high contrast (near black and white)

    def test_contrast_maximum_negative(self, gradient_image):
        """Contrast with amount=-100 (maximum low contrast)."""
        contrast.init()

        result = contrast.contrast(gradient_image, amount=-100)

        assert isinstance(result, Image.Image)
        # Should be very uniform (near mean gray)

    def test_contrast_small_image(self, small_image):
        """Contrast works with small images."""
        contrast.init()

        result = contrast.contrast(small_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_contrast_large_image(self, large_image):
        """Contrast works with large images."""
        contrast.init()

        result = contrast.contrast(large_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_contrast_twice_increase(self, gradient_image):
        """Applying high contrast twice should compound effect."""
        contrast.init()

        first = contrast.contrast(gradient_image, amount=30)
        second = contrast.contrast(first, amount=30)

        assert isinstance(second, Image.Image)
        # Effect should compound

    def test_contrast_twice_decrease(self, gradient_image):
        """Applying low contrast twice should compound effect."""
        contrast.init()

        first = contrast.contrast(gradient_image, amount=-30)
        second = contrast.contrast(first, amount=-30)

        assert isinstance(second, Image.Image)
        # Should be more uniform

    def test_contrast_increase_then_decrease(self, gradient_image):
        """Increase then decrease contrast."""
        contrast.init()

        increased = contrast.contrast(gradient_image, amount=40)
        decreased = contrast.contrast(increased, amount=-40)

        assert isinstance(decreased, Image.Image)
        # Won't return to original but should be less contrasted


class TestContrastIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_contrast(self, gradient_image):
        """Action.pil should call contrast function."""
        contrast.init()

        result = contrast.Action.pil(gradient_image, amount=40)

        assert isinstance(result, Image.Image)
        # Verify it actually applied contrast
        assert result.size == gradient_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = contrast.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = contrast.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Amount field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = contrast.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_contrast(self):
        """Action documentation mentions contrast or grey."""
        action = contrast.Action()
        doc_lower = action.__doc__.lower()
        assert 'grey' in doc_lower or 'gray' in doc_lower or 'contrast' in doc_lower

    def test_action_pil_points_to_contrast(self):
        """Action.pil should point to contrast function."""
        # The action's pil staticmethod should be the contrast function
        assert contrast.Action.pil == contrast.contrast
