"""Unit tests for phatch.actions.autocontrast module.

Tests the Auto Contrast action.

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
from phatch.actions import autocontrast


class TestAutocontrastAction:
    """Test the Autocontrast action class metadata."""

    def test_action_exists(self):
        """Autocontrast action class should exist."""
        assert hasattr(autocontrast, 'Action')
        assert autocontrast.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = autocontrast.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = autocontrast.Action()
        assert 'contrast' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(autocontrast.Action, 'pil')
        assert callable(autocontrast.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(autocontrast.Action, 'init')
        assert callable(autocontrast.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = autocontrast.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestAutocontrastInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_cutoff_field(self):
        """interface should define Cutoff parameter."""
        action = autocontrast.Action()
        fields = {}
        action.interface(fields)

        # Should have Cutoff field
        assert any('cutoff' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = autocontrast.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_both_are_sliders(self):
        """Both Cutoff and Amount should be SliderFields."""
        action = autocontrast.Action()
        fields = {}
        action.interface(fields)

        # Should have 2 SliderFields
        slider_count = sum(1 for v in fields.values()
                          if type(v).__name__ == 'SliderField')
        assert slider_count == 2


class TestAutocontrastPilFunction:
    """Test the autocontrast() PIL function."""

    def test_autocontrast_function_exists(self):
        """autocontrast function should exist."""
        assert hasattr(autocontrast, 'autocontrast')
        assert callable(autocontrast.autocontrast)

    def test_autocontrast_full_amount_rgb(self, gradient_image):
        """Autocontrast gradient with amount=100."""
        autocontrast.init()

        result = autocontrast.autocontrast(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # After autocontrast, darkest should be near 0, brightest near 255
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        left_brightness = sum(left_pixel) / 3
        right_brightness = sum(right_pixel) / 3

        # Should maximize contrast
        assert left_brightness < 50  # Dark end darker
        assert right_brightness > 200  # Bright end brighter

    def test_autocontrast_partial_amount(self, gradient_image):
        """Autocontrast with partial amount (50%)."""
        autocontrast.init()

        result = autocontrast.autocontrast(gradient_image, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

        # With 50% blend, contrast increase should be moderate
        # (blend of original and fully contrasted)

    def test_autocontrast_with_cutoff(self, gradient_image):
        """Autocontrast with cutoff parameter."""
        autocontrast.init()

        # Cutoff ignores some percentage of extremes
        result = autocontrast.autocontrast(gradient_image, amount=100, cutoff=10)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size

    def test_autocontrast_preserves_alpha(self, rgba_image):
        """Autocontrast RGBA image preserves alpha channel."""
        autocontrast.init()

        result = autocontrast.autocontrast(rgba_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode in ('RGBA', 'LA')

        # Check a semi-transparent pixel
        pixel_with_alpha = result.getpixel((25, 25))
        if len(pixel_with_alpha) == 4:
            assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_autocontrast_grayscale(self, grayscale_image):
        """Autocontrast grayscale image."""
        autocontrast.init()

        result = autocontrast.autocontrast(grayscale_image, amount=100)

        assert isinstance(result, Image.Image)
        # Result should be same size
        assert result.size == grayscale_image.size

    def test_autocontrast_uniform_color(self, rgb_image):
        """Autocontrast on uniform color image."""
        autocontrast.init()

        # Uniform red image has no contrast to maximize
        result = autocontrast.autocontrast(rgb_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should handle gracefully (no change or minimal change)
        pixel = result.getpixel((50, 50))
        # Uniform image may stay similar
        assert isinstance(pixel, tuple)
        assert len(pixel) == 3

    def test_autocontrast_multicolor(self, multicolor_image):
        """Autocontrast on image with multiple colors."""
        autocontrast.init()

        result = autocontrast.autocontrast(multicolor_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

        # Autocontrast should maximize the dynamic range
        # Check that we still have distinct regions
        red_region = result.getpixel((25, 25))
        white_region = result.getpixel((75, 75))

        # Red and white should still be different
        assert red_region != white_region


class TestAutocontrastEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_autocontrast_amount_minimum(self, gradient_image):
        """Autocontrast with amount=1 (minimum from interface)."""
        autocontrast.init()

        result = autocontrast.autocontrast(gradient_image, amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, should be very close to original

    def test_autocontrast_amount_maximum(self, gradient_image):
        """Autocontrast with amount=100 (maximum)."""
        autocontrast.init()

        result = autocontrast.autocontrast(gradient_image, amount=100)

        assert isinstance(result, Image.Image)
        # Should apply full autocontrast

    def test_autocontrast_cutoff_zero(self, gradient_image):
        """Autocontrast with cutoff=0 (no cutoff)."""
        autocontrast.init()

        result = autocontrast.autocontrast(gradient_image, amount=100, cutoff=0)

        assert isinstance(result, Image.Image)

    def test_autocontrast_cutoff_maximum(self, gradient_image):
        """Autocontrast with cutoff=100 (maximum from interface)."""
        autocontrast.init()

        # Cutoff=100 is extreme but should handle gracefully
        result = autocontrast.autocontrast(gradient_image, amount=100, cutoff=100)

        assert isinstance(result, Image.Image)

    def test_autocontrast_small_image(self, small_image):
        """Autocontrast works with small images."""
        autocontrast.init()

        result = autocontrast.autocontrast(small_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_autocontrast_large_image(self, large_image):
        """Autocontrast works with large images."""
        autocontrast.init()

        result = autocontrast.autocontrast(large_image, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size


class TestAutocontrastIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_autocontrast(self, gradient_image):
        """Action.pil should call autocontrast function."""
        autocontrast.init()

        result = autocontrast.Action.pil(gradient_image, amount=100, cutoff=0)

        assert isinstance(result, Image.Image)
        # Verify it actually applied autocontrast
        # Gradient should have maximized contrast
        left = result.getpixel((0, 50))
        right = result.getpixel((99, 50))
        # Should have more contrast than original
        assert left != right

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = autocontrast.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = autocontrast.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2  # Cutoff and Amount

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = autocontrast.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]
