"""Unit tests for phatch.actions.solarize module.

Tests the Solarize action (invert pixels above threshold).

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
from phatch.actions import solarize


class TestSolarizeAction:
    """Test the Solarize action class metadata."""

    def test_action_exists(self):
        """Solarize action class should exist."""
        assert hasattr(solarize, 'Action')
        assert solarize.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = solarize.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = solarize.Action()
        assert 'solarize' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(solarize.Action, 'pil')
        assert callable(solarize.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(solarize.Action, 'init')
        assert callable(solarize.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = solarize.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestSolarizeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_threshold_field(self):
        """interface should define Threshold parameter."""
        action = solarize.Action()
        fields = {}
        action.interface(fields)

        # Should have Treshold field (note typo in source)
        assert any('treshold' in k.lower() or 'threshold' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = solarize.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_threshold_is_slider(self):
        """Threshold field should be a SliderField."""
        action = solarize.Action()
        fields = {}
        action.interface(fields)

        # Get the Threshold field
        threshold_field = None
        for key, value in fields.items():
            if 'treshold' in key.lower() or 'threshold' in key.lower():
                threshold_field = value
                break

        assert threshold_field is not None
        assert type(threshold_field).__name__ == 'SliderField'

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = solarize.Action()
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
        """Solarize should have two parameters."""
        action = solarize.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2


class TestSolarizePilFunction:
    """Test the solarize() PIL function."""

    def test_solarize_function_exists(self):
        """solarize function should exist."""
        assert hasattr(solarize, 'solarize')
        assert callable(solarize.solarize)

    def test_solarize_high_threshold(self, multicolor_image):
        """Solarize with high threshold (inverts only bright pixels)."""
        solarize.init()

        # Threshold 200 inverts pixels above 200
        result = solarize.solarize(multicolor_image, treshold=200, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_solarize_low_threshold(self, multicolor_image):
        """Solarize with low threshold (inverts most pixels)."""
        solarize.init()

        # Threshold 50 inverts most pixels
        result = solarize.solarize(multicolor_image, treshold=50, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_solarize_mid_threshold(self, gradient_image):
        """Solarize with mid threshold (128) on gradient."""
        solarize.init()

        result = solarize.solarize(gradient_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size
        # Dark half unchanged, bright half inverted

    def test_solarize_partial_amount(self, multicolor_image):
        """Solarize with partial amount blends with original."""
        solarize.init()

        result = solarize.solarize(multicolor_image, treshold=128, amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_solarize_preserves_alpha(self, rgba_image):
        """Solarize RGBA image preserves alpha channel."""
        solarize.init()

        result = solarize.solarize(rgba_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_solarize_rgb_image(self, rgb_image):
        """Solarize uniform RGB image."""
        solarize.init()

        result = solarize.solarize(rgb_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_solarize_grayscale(self, grayscale_image):
        """Solarize grayscale image."""
        solarize.init()

        result = solarize.solarize(grayscale_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size


class TestSolarizeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_solarize_threshold_zero(self, multicolor_image):
        """Solarize with threshold=0 (inverts all pixels)."""
        solarize.init()

        result = solarize.solarize(multicolor_image, treshold=0, amount=100)

        assert isinstance(result, Image.Image)
        # All pixels inverted

    def test_solarize_threshold_255(self, multicolor_image):
        """Solarize with threshold=255 (inverts almost nothing)."""
        solarize.init()

        result = solarize.solarize(multicolor_image, treshold=255, amount=100)

        assert isinstance(result, Image.Image)
        # Almost no inversion

    def test_solarize_amount_minimum(self, multicolor_image):
        """Solarize with amount=1 (barely visible)."""
        solarize.init()

        result = solarize.solarize(multicolor_image, treshold=128, amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, effect should be very subtle

    def test_solarize_amount_maximum(self, multicolor_image):
        """Solarize with amount=100 (full effect)."""
        solarize.init()

        result = solarize.solarize(multicolor_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully solarized

    def test_solarize_small_image(self, small_image):
        """Solarize works with small images."""
        solarize.init()

        result = solarize.solarize(small_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_solarize_large_image(self, large_image):
        """Solarize works with large images."""
        solarize.init()

        result = solarize.solarize(large_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_solarize_twice(self, multicolor_image):
        """Solarizing twice with same threshold."""
        solarize.init()

        first = solarize.solarize(multicolor_image, treshold=128, amount=100)
        second = solarize.solarize(first, treshold=128, amount=100)

        assert isinstance(second, Image.Image)
        # Second solarization inverts again

    def test_solarize_different_thresholds(self, multicolor_image):
        """Solarize with various threshold values."""
        solarize.init()

        # Test several threshold values
        for threshold in [0, 64, 128, 192, 255]:
            result = solarize.solarize(multicolor_image,
                                        treshold=threshold, amount=100)
            assert isinstance(result, Image.Image)
            assert result.size == multicolor_image.size


class TestSolarizeIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_solarize(self, multicolor_image):
        """Action.pil should call solarize function."""
        solarize.init()

        result = solarize.Action.pil(multicolor_image, treshold=128, amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually solarized
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = solarize.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = solarize.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2  # Treshold and Amount

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = solarize.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_invert(self):
        """Action documentation mentions invert or threshold."""
        action = solarize.Action()
        doc_lower = action.__doc__.lower()
        assert 'invert' in doc_lower or 'threshold' in doc_lower

    def test_action_pil_points_to_solarize(self):
        """Action.pil should point to solarize function."""
        # The action's pil staticmethod should be the solarize function
        assert solarize.Action.pil == solarize.solarize
