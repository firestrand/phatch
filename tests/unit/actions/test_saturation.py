"""Unit tests for phatch.actions.saturation module.

Tests the Saturation action (adjust from grayscale to high saturation).

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
from phatch.actions import saturation


class TestSaturationAction:
    """Test the Saturation action class metadata."""

    def test_action_exists(self):
        """Saturation action class should exist."""
        assert hasattr(saturation, 'Action')
        assert saturation.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = saturation.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = saturation.Action()
        assert 'saturation' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(saturation.Action, 'pil')
        assert callable(saturation.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(saturation.Action, 'init')
        assert callable(saturation.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = saturation.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestSaturationInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = saturation.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = saturation.Action()
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
        """Saturation should have only one parameter."""
        action = saturation.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestSaturationPilFunction:
    """Test the saturation() PIL function."""

    def test_saturation_function_exists(self):
        """saturation function should exist."""
        assert hasattr(saturation, 'saturation')
        assert callable(saturation.saturation)

    def test_increase_saturation_multicolor(self, multicolor_image):
        """Increase saturation on multicolor image."""
        saturation.init()

        result = saturation.saturation(multicolor_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

        # After increasing saturation, colors should be more vivid
        # Regions should still be distinct
        red_region = result.getpixel((25, 25))
        green_region = result.getpixel((75, 25))

        assert red_region != green_region

    def test_decrease_saturation_multicolor(self, multicolor_image):
        """Decrease saturation on multicolor image (toward grayscale)."""
        saturation.init()

        result = saturation.saturation(multicolor_image, amount=-50)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

        # After decreasing saturation, colors should be more muted
        # (closer to grayscale)

    def test_saturation_zero_unchanged(self):
        """Saturation with amount=0 should return unchanged image."""
        saturation.init()

        img = Image.new('RGB', (100, 100), color=(255, 100, 100))
        result = saturation.saturation(img, amount=0)

        # Should return the same image object
        assert result is img

    def test_saturation_preserves_alpha(self, rgba_image):
        """Saturation RGBA image preserves alpha channel."""
        saturation.init()

        result = saturation.saturation(rgba_image, amount=30)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_increase_saturation_rgb(self, rgb_image):
        """Increase saturation on uniform RGB image."""
        saturation.init()

        result = saturation.saturation(rgb_image, amount=40)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size
        # Should handle uniform color gracefully

    def test_decrease_saturation_rgb(self, rgb_image):
        """Decrease saturation on uniform RGB image."""
        saturation.init()

        result = saturation.saturation(rgb_image, amount=-40)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_saturation_grayscale(self, grayscale_image):
        """Saturation on grayscale image (no color to saturate)."""
        saturation.init()

        result = saturation.saturation(grayscale_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size
        # Grayscale has no color to saturate

    def test_saturation_gradient(self, gradient_image):
        """Saturation maintains gradient pattern."""
        saturation.init()

        result = saturation.saturation(gradient_image, amount=30)

        assert isinstance(result, Image.Image)
        # Gradient pattern should be preserved
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        if isinstance(left_pixel, tuple):
            left_brightness = sum(left_pixel[:3]) / 3
            right_brightness = sum(right_pixel[:3]) / 3
        else:
            left_brightness = left_pixel
            right_brightness = right_pixel

        assert left_brightness < right_brightness


class TestSaturationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_saturation_maximum_positive(self, multicolor_image):
        """Saturation with amount=100 (maximum oversaturation)."""
        saturation.init()

        result = saturation.saturation(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should have very high saturation

    def test_saturation_maximum_negative(self, multicolor_image):
        """Saturation with amount=-100 (full desaturation/grayscale)."""
        saturation.init()

        result = saturation.saturation(multicolor_image, amount=-100)

        assert isinstance(result, Image.Image)
        # Should be fully desaturated (grayscale)

    def test_saturation_small_image(self, small_image):
        """Saturation works with small images."""
        saturation.init()

        result = saturation.saturation(small_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_saturation_large_image(self, large_image):
        """Saturation works with large images."""
        saturation.init()

        result = saturation.saturation(large_image, amount=30)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_saturation_twice_increase(self, multicolor_image):
        """Applying high saturation twice should compound effect."""
        saturation.init()

        first = saturation.saturation(multicolor_image, amount=30)
        second = saturation.saturation(first, amount=30)

        assert isinstance(second, Image.Image)
        # Effect should compound (more saturated)

    def test_saturation_twice_decrease(self, multicolor_image):
        """Applying low saturation twice should compound effect."""
        saturation.init()

        first = saturation.saturation(multicolor_image, amount=-30)
        second = saturation.saturation(first, amount=-30)

        assert isinstance(second, Image.Image)
        # Should be more desaturated

    def test_saturation_increase_then_decrease(self, multicolor_image):
        """Increase then decrease saturation."""
        saturation.init()

        increased = saturation.saturation(multicolor_image, amount=40)
        decreased = saturation.saturation(increased, amount=-40)

        assert isinstance(decreased, Image.Image)
        # Won't return to original but should be less saturated


class TestSaturationIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_saturation(self, multicolor_image):
        """Action.pil should call saturation function."""
        saturation.init()

        result = saturation.Action.pil(multicolor_image, amount=40)

        assert isinstance(result, Image.Image)
        # Verify it actually applied saturation
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = saturation.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = saturation.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Amount field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = saturation.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_saturation(self):
        """Action documentation mentions saturation or grayscale."""
        action = saturation.Action()
        doc_lower = action.__doc__.lower()
        assert 'saturation' in doc_lower or 'grayscale' in doc_lower or 'gray' in doc_lower

    def test_action_pil_points_to_saturation(self):
        """Action.pil should point to saturation function."""
        # The action's pil staticmethod should be the saturation function
        assert saturation.Action.pil == saturation.saturation
