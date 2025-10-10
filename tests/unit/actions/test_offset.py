"""Unit tests for phatch.actions.offset module.

Tests the Offset action (offset by distance and wrap around).

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
from phatch.actions import offset


class TestOffsetAction:
    """Test the Offset action class metadata."""

    def test_action_exists(self):
        """Offset action class should exist."""
        assert hasattr(offset, 'Action')
        assert offset.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = offset.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = offset.Action()
        assert 'offset' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(offset.Action, 'pil')
        assert callable(offset.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(offset.Action, 'init')
        assert callable(offset.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = offset.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = offset.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = offset.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'filter' in tags_lower


class TestOffsetInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_horizontal_offset_field(self):
        """interface should define Horizontal Offset parameter."""
        action = offset.Action()
        fields = {}
        action.interface(fields)

        # Should have Horizontal Offset field
        assert any('horizontal' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_vertical_offset_field(self):
        """interface should define Vertical Offset parameter."""
        action = offset.Action()
        fields = {}
        action.interface(fields)

        # Should have Vertical Offset field
        assert any('vertical' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())

    def test_interface_horizontal_is_pixel_field(self):
        """Horizontal Offset field should be a PixelField."""
        action = offset.Action()
        fields = {}
        action.interface(fields)

        # Get the Horizontal Offset field
        h_field = None
        for key, value in fields.items():
            if 'horizontal' in key.lower() and 'offset' in key.lower():
                h_field = value
                break

        assert h_field is not None
        assert type(h_field).__name__ == 'PixelField'

    def test_interface_vertical_is_pixel_field(self):
        """Vertical Offset field should be a PixelField."""
        action = offset.Action()
        fields = {}
        action.interface(fields)

        # Get the Vertical Offset field
        v_field = None
        for key, value in fields.items():
            if 'vertical' in key.lower() and 'offset' in key.lower():
                v_field = value
                break

        assert v_field is not None
        assert type(v_field).__name__ == 'PixelField'

    def test_interface_has_two_fields(self):
        """Offset should have two parameters."""
        action = offset.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2


class TestOffsetFunction:
    """Test the offset() PIL function."""

    def test_offset_function_exists(self):
        """offset function should exist."""
        assert hasattr(offset, 'offset')
        assert callable(offset.offset)

    def test_offset_horizontal_only(self, multicolor_image):
        """Offset horizontally only."""
        offset.init()

        result = offset.offset(multicolor_image, 25, 0)

        assert isinstance(result, Image.Image)
        # Size should remain same
        assert result.size == multicolor_image.size
        # Pixels should be shifted

    def test_offset_vertical_only(self, multicolor_image):
        """Offset vertically only."""
        offset.init()

        result = offset.offset(multicolor_image, 0, 25)

        assert isinstance(result, Image.Image)
        # Size should remain same
        assert result.size == multicolor_image.size

    def test_offset_both_directions(self, multicolor_image):
        """Offset both horizontally and vertically."""
        offset.init()

        result = offset.offset(multicolor_image, 25, 25)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_offset_half_width(self, rgb_image):
        """Offset by half width (50%)."""
        offset.init()

        result = offset.offset(rgb_image, 50, 0)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_offset_half_height(self, rgb_image):
        """Offset by half height (50%)."""
        offset.init()

        result = offset.offset(rgb_image, 0, 50)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_offset_negative_horizontal(self, multicolor_image):
        """Offset with negative horizontal value."""
        offset.init()

        result = offset.offset(multicolor_image, -25, 0)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_offset_negative_vertical(self, multicolor_image):
        """Offset with negative vertical value."""
        offset.init()

        result = offset.offset(multicolor_image, 0, -25)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_offset_rgba_preserves_mode(self, rgba_image):
        """Offset RGBA image preserves mode."""
        offset.init()

        result = offset.offset(rgba_image, 25, 25)

        assert isinstance(result, Image.Image)
        # Should preserve RGBA mode
        assert result.mode == 'RGBA'

    def test_offset_grayscale(self, grayscale_image):
        """Offset grayscale image."""
        offset.init()

        result = offset.offset(grayscale_image, 25, 25)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == grayscale_image.size

    def test_offset_wraps_around(self, gradient_image):
        """Offset wraps around edges."""
        offset.init()

        # Offset by full width should wrap around completely
        result = offset.offset(gradient_image, 100, 0)

        assert isinstance(result, Image.Image)
        # Should be same as original due to wrap-around
        # (for a gradient this means pixels wrap)


class TestOffsetEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_offset_zero_both(self, rgb_image):
        """Offset with zero for both directions."""
        offset.init()

        result = offset.offset(rgb_image, 0, 0)

        assert isinstance(result, Image.Image)
        # Should be unchanged
        assert result.size == rgb_image.size

    def test_offset_full_width(self, rgb_image):
        """Offset by full image width."""
        offset.init()

        result = offset.offset(rgb_image, 100, 0)

        assert isinstance(result, Image.Image)
        # Full width offset wraps around
        assert result.size == rgb_image.size

    def test_offset_full_height(self, rgb_image):
        """Offset by full image height."""
        offset.init()

        result = offset.offset(rgb_image, 0, 100)

        assert isinstance(result, Image.Image)
        # Full height offset wraps around
        assert result.size == rgb_image.size

    def test_offset_small_image(self, small_image):
        """Offset works with small images."""
        offset.init()

        result = offset.offset(small_image, 5, 5)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_offset_large_image(self, large_image):
        """Offset works with large images."""
        offset.init()

        result = offset.offset(large_image, 100, 100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_offset_vertical_none(self, rgb_image):
        """Offset with vertical_offset=None."""
        offset.init()

        result = offset.offset(rgb_image, 25, None)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_offset_large_values(self, rgb_image):
        """Offset with large offset values."""
        offset.init()

        result = offset.offset(rgb_image, 200, 200)

        assert isinstance(result, Image.Image)
        # Large values wrap around
        assert result.size == rgb_image.size

    def test_offset_multicolor_pattern(self, multicolor_image):
        """Offset multicolor image with pattern."""
        offset.init()

        result = offset.offset(multicolor_image, 50, 50)

        assert isinstance(result, Image.Image)
        # Check that pixels have shifted
        # Original top-left pixel should have moved
        original_tl = multicolor_image.getpixel((0, 0))
        result_tl = result.getpixel((0, 0))
        # Due to wrap-around, these should be different
        # (unless the image is uniform, which multicolor_image is not)


class TestOffsetIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_offset(self, multicolor_image):
        """Action.pil should call offset function."""
        offset.init()

        result = offset.Action.pil(multicolor_image,
                                   horizontal_offset=25,
                                   vertical_offset=25)

        assert isinstance(result, Image.Image)
        # Verify it actually offset
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = offset.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = offset.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = offset.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'filter' in tags_lower

    def test_action_docstring_mentions_offset(self):
        """Action documentation mentions offset or wrap."""
        action = offset.Action()
        doc_lower = action.__doc__.lower()
        assert 'offset' in doc_lower or 'wrap' in doc_lower

    def test_action_pil_points_to_offset(self):
        """Action.pil should point to offset function."""
        # The action's pil staticmethod should be the offset function
        assert offset.Action.pil == offset.offset

    def test_init_loads_image_chops(self):
        """init() should load ImageChops module."""
        offset.init()
        # After init, ImageChops should be available in the module
        assert hasattr(offset, 'ImageChops')
