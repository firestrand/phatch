"""Unit tests for phatch.actions.crop module.

Tests the Crop action (crop edges from image).

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
from phatch.actions import crop


class TestCropAction:
    """Test the Crop action class metadata."""

    def test_action_exists(self):
        """Crop action class should exist."""
        assert hasattr(crop, 'Action')
        assert crop.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = crop.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = crop.Action()
        assert 'crop' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(crop.Action, 'pil')
        assert callable(crop.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(crop.Action, 'init')
        assert callable(crop.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = crop.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = crop.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower


class TestCropInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_mode_field(self):
        """interface should define Mode parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have Mode field
        assert any('mode' in k.lower() for k in fields.keys())

    def test_interface_defines_all_field(self):
        """interface should define All parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have All field
        assert 'All' in fields.keys()

    def test_interface_defines_left_field(self):
        """interface should define Left parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have Left field
        assert 'Left' in fields.keys()

    def test_interface_defines_right_field(self):
        """interface should define Right parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have Right field
        assert 'Right' in fields.keys()

    def test_interface_defines_top_field(self):
        """interface should define Top parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have Top field
        assert 'Top' in fields.keys()

    def test_interface_defines_bottom_field(self):
        """interface should define Bottom parameter."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Should have Bottom field
        assert 'Bottom' in fields.keys()

    def test_interface_mode_is_choice_field(self):
        """Mode field should be a ChoiceField."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Get the Mode field
        mode_field = None
        for key, value in fields.items():
            if 'mode' in key.lower():
                mode_field = value
                break

        assert mode_field is not None
        assert type(mode_field).__name__ == 'ChoiceField'

    def test_interface_left_is_pixel_field(self):
        """Left field should be a PixelField."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        # Get the Left field
        left_field = fields.get('Left')

        assert left_field is not None
        assert type(left_field).__name__ == 'PixelField'

    def test_interface_has_six_fields(self):
        """Crop should have six parameters."""
        action = crop.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 6


class TestCropPilFunction:
    """Test the crop() PIL function."""

    def test_crop_function_exists(self):
        """crop function should exist."""
        assert hasattr(crop, 'crop')
        assert callable(crop.crop)

    def test_crop_custom_mode_all_sides(self, rgb_image):
        """Crop custom mode with all sides specified."""
        crop.init()

        result = crop.crop(rgb_image, mode='Custom',
                          left=10, right=10, top=10, bottom=10)

        assert isinstance(result, Image.Image)
        # Size should be reduced by crop amounts
        assert result.size == (80, 80)  # 100-10-10 on each dimension

    def test_crop_custom_mode_left_right(self, multicolor_image):
        """Crop custom mode with left and right only."""
        crop.init()

        result = crop.crop(multicolor_image, mode='Custom',
                          left=20, right=20, top=0, bottom=0)

        assert isinstance(result, Image.Image)
        assert result.size[0] == 60  # 100 - 20 - 20

    def test_crop_custom_mode_top_bottom(self, multicolor_image):
        """Crop custom mode with top and bottom only."""
        crop.init()

        result = crop.crop(multicolor_image, mode='Custom',
                          left=0, right=0, top=15, bottom=15)

        assert isinstance(result, Image.Image)
        assert result.size[1] == 70  # 100 - 15 - 15

    def test_crop_all_mode(self, rgb_image):
        """Crop All mode with equal crop on all sides."""
        crop.init()

        result = crop.crop(rgb_image, mode='All', all=10)

        assert isinstance(result, Image.Image)
        # All sides cropped by 10
        assert result.size == (80, 80)

    def test_crop_auto_mode(self, rgb_image):
        """Crop Auto mode uses auto_crop."""
        crop.init()

        # Auto crop on uniform image should work
        result = crop.crop(rgb_image, mode='Auto')

        assert isinstance(result, Image.Image)
        # Auto crop might reduce size or keep it same depending on borders

    def test_crop_rgba_preserves_alpha(self, rgba_image):
        """Crop RGBA image preserves alpha channel."""
        crop.init()

        result = crop.crop(rgba_image, mode='Custom',
                          left=10, right=10, top=10, bottom=10)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'
        assert result.size == (80, 80)

    def test_crop_grayscale(self, grayscale_image):
        """Crop grayscale image."""
        crop.init()

        result = crop.crop(grayscale_image, mode='Custom',
                          left=5, right=5, top=5, bottom=5)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == (90, 90)

    def test_crop_gradient(self, gradient_image):
        """Crop gradient image."""
        crop.init()

        result = crop.crop(gradient_image, mode='Custom',
                          left=10, right=10, top=0, bottom=0)

        assert isinstance(result, Image.Image)
        # Width reduced, height unchanged
        assert result.size == (80, 100)


class TestCropEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_crop_zero_amounts(self, rgb_image):
        """Crop with all zero amounts (no crop)."""
        crop.init()

        result = crop.crop(rgb_image, mode='Custom',
                          left=0, right=0, top=0, bottom=0)

        assert isinstance(result, Image.Image)
        # Should be same size
        assert result.size == rgb_image.size

    def test_crop_all_mode_zero(self, multicolor_image):
        """Crop All mode with zero amount (no crop)."""
        crop.init()

        result = crop.crop(multicolor_image, mode='All', all=0)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_crop_small_amount(self, rgb_image):
        """Crop with very small amount."""
        crop.init()

        result = crop.crop(rgb_image, mode='Custom',
                          left=1, right=1, top=1, bottom=1)

        assert isinstance(result, Image.Image)
        assert result.size == (98, 98)

    def test_crop_large_amount(self, rgb_image):
        """Crop with large amount."""
        crop.init()

        result = crop.crop(rgb_image, mode='Custom',
                          left=40, right=40, top=40, bottom=40)

        assert isinstance(result, Image.Image)
        # Should result in small image
        assert result.size == (20, 20)

    def test_crop_small_image(self, small_image):
        """Crop works with small images."""
        crop.init()

        result = crop.crop(small_image, mode='Custom',
                          left=1, right=1, top=1, bottom=1)

        assert isinstance(result, Image.Image)
        assert result.size == (8, 8)

    def test_crop_large_image(self, large_image):
        """Crop works with large images."""
        crop.init()

        result = crop.crop(large_image, mode='Custom',
                          left=50, right=50, top=50, bottom=50)

        assert isinstance(result, Image.Image)
        assert result.size == (400, 400)

    def test_crop_twice(self, multicolor_image):
        """Cropping twice compounds the crop."""
        crop.init()

        first = crop.crop(multicolor_image, mode='Custom',
                         left=10, right=10, top=10, bottom=10)
        second = crop.crop(first, mode='Custom',
                          left=5, right=5, top=5, bottom=5)

        assert isinstance(second, Image.Image)
        # First crop: 100 -> 80, second crop: 80 -> 70
        assert second.size == (70, 70)

    def test_crop_asymmetric(self, rgb_image):
        """Crop with different amounts on each side."""
        crop.init()

        result = crop.crop(rgb_image, mode='Custom',
                          left=5, right=15, top=20, bottom=10)

        assert isinstance(result, Image.Image)
        # Width: 100 - 5 - 15 = 80
        # Height: 100 - 20 - 10 = 70
        assert result.size == (80, 70)


class TestCropIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_crop(self, multicolor_image):
        """Action.pil should call crop function."""
        crop.init()

        result = crop.Action.pil(multicolor_image, mode='Custom',
                                 left=10, right=10, top=10, bottom=10)

        assert isinstance(result, Image.Image)
        # Verify it actually cropped
        assert result.size == (80, 80)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = crop.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = crop.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 6

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = crop.Action()
        assert action.author == 'Nadia Alramli'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower

    def test_action_docstring_mentions_crop(self):
        """Action documentation mentions crop."""
        action = crop.Action()
        doc_lower = action.__doc__.lower()
        assert 'crop' in doc_lower

    def test_action_pil_points_to_crop(self):
        """Action.pil should point to crop function."""
        # The action's pil staticmethod should be the crop function
        assert crop.Action.pil == crop.crop
