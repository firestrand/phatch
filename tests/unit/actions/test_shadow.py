"""Unit tests for phatch.actions.shadow module.

Tests the Shadow action (drops a blurred shadow under a photo).

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
from phatch.actions import shadow


class TestShadowAction:
    """Test the Shadow action class metadata."""

    def test_action_exists(self):
        """Shadow action class should exist."""
        assert hasattr(shadow, 'Action')
        assert shadow.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = shadow.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(shadow.Action, 'pil')
        assert callable(shadow.Action.pil)

    def test_action_has_cache(self):
        """Action should have cache enabled."""
        action = shadow.Action()
        assert action.cache is True


class TestShadowInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_offset_fields(self):
        """interface should define Horizontal and Vertical Offset parameters."""
        action = shadow.Action()
        fields = {}
        action.interface(fields)

        assert any('horizontal' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())
        assert any('vertical' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())

    def test_interface_has_seven_fields(self):
        """Shadow should have seven parameters."""
        action = shadow.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 7


class TestShadowFunction:
    """Test the drop_shadow() PIL function."""

    def test_drop_shadow_function_exists(self):
        """drop_shadow function should exist."""
        assert hasattr(shadow, 'drop_shadow')
        assert callable(shadow.drop_shadow)

    def test_drop_shadow_basic_rgb(self, rgb_image):
        """Drop shadow on RGB image."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image)

        assert isinstance(result, Image.Image)
        # Size should increase due to border
        assert result.size[0] > rgb_image.size[0]
        assert result.size[1] > rgb_image.size[1]

    def test_drop_shadow_rgba(self, rgba_image):
        """Drop shadow on RGBA image."""
        shadow.init()

        result = shadow.drop_shadow(rgba_image)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_drop_shadow_with_offset(self, rgb_image):
        """Drop shadow with custom offset."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, horizontal_offset=10,
                                    vertical_offset=10)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_with_border(self, rgb_image):
        """Drop shadow with custom border."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, border=20)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_with_blur(self, rgb_image):
        """Drop shadow with blur applied."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, shadow_blur=5)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_grayscale(self, grayscale_image):
        """Drop shadow on grayscale image."""
        shadow.init()

        result = shadow.drop_shadow(grayscale_image)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_caching(self, rgb_image):
        """Drop shadow uses caching."""
        shadow.init()
        cache = {}

        # First call
        result1 = shadow.drop_shadow(rgb_image, cache=cache)
        cache_size_1 = len(cache)

        # Second call with same parameters
        result2 = shadow.drop_shadow(rgb_image, cache=cache)
        cache_size_2 = len(cache)

        # Cache should be reused
        assert cache_size_1 > 0
        assert cache_size_1 == cache_size_2
        assert result1.width >= rgb_image.width
        assert result2.width >= rgb_image.width
        assert result1.height >= rgb_image.height
        assert result2.height >= rgb_image.height


class TestShadowEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_drop_shadow_zero_offset(self, rgb_image):
        """Drop shadow with zero offset."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, horizontal_offset=0,
                                    vertical_offset=0)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_negative_offset(self, rgb_image):
        """Drop shadow with negative offset."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, horizontal_offset=-5,
                                    vertical_offset=-5)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_minimal_blur(self, rgb_image):
        """Drop shadow with minimal blur."""
        shadow.init()

        result = shadow.drop_shadow(rgb_image, shadow_blur=1)

        assert isinstance(result, Image.Image)

    def test_drop_shadow_small_image(self, small_image):
        """Drop shadow works with small images."""
        shadow.init()

        result = shadow.drop_shadow(small_image)

        assert isinstance(result, Image.Image)


class TestShadowIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_drop_shadow(self, multicolor_image):
        """Action.pil should call drop_shadow function."""
        shadow.init()

        result = shadow.Action.pil(multicolor_image)

        assert isinstance(result, Image.Image)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = shadow.Action()
        assert action is not None

    def test_action_pil_points_to_drop_shadow(self):
        """Action.pil should point to drop_shadow function."""
        assert shadow.Action.pil == shadow.drop_shadow

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        shadow.init()
        assert hasattr(shadow, 'Image')
        assert hasattr(shadow, 'ImageChops')
        assert hasattr(shadow, 'ImageFilter')
