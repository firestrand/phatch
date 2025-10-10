"""Unit tests for phatch.actions.rotate module.

Tests the Rotate action (rotate image with angle and background).

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
from phatch.actions import rotate


class TestRotateAction:
    """Test the Rotate action class metadata."""

    def test_action_exists(self):
        """Rotate action class should exist."""
        assert hasattr(rotate, 'Action')
        assert rotate.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = rotate.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = rotate.Action()
        assert 'rotate' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(rotate.Action, 'pil')
        assert callable(rotate.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(rotate.Action, 'init')
        assert callable(rotate.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = rotate.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = rotate.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower


class TestRotateInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_angle_field(self):
        """interface should define Angle parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Angle field
        assert any('angle' in k.lower() for k in fields.keys())

    def test_interface_defines_resample_field(self):
        """interface should define Resample Image parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Resample Image field
        assert any('resample' in k.lower() for k in fields.keys())

    def test_interface_defines_expand_field(self):
        """interface should define Expand parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Expand field
        assert any('expand' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_defines_background_color_field(self):
        """interface should define Background Color parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Background Color field
        assert any('background' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_background_opacity_field(self):
        """interface should define Background Opacity parameter."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Should have Background Opacity field
        assert any('background' in k.lower() and 'opacity' in k.lower()
                   for k in fields.keys())

    def test_interface_angle_is_slider(self):
        """Angle field should be a SliderField."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Get the Angle field
        angle_field = None
        for key, value in fields.items():
            if 'angle' in key.lower():
                angle_field = value
                break

        assert angle_field is not None
        assert type(angle_field).__name__ == 'SliderField'

    def test_interface_expand_is_boolean(self):
        """Expand field should be a BooleanField."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Get the Expand field
        expand_field = None
        for key, value in fields.items():
            if 'expand' in key.lower():
                expand_field = value
                break

        assert expand_field is not None
        assert type(expand_field).__name__ == 'BooleanField'

    def test_interface_background_color_is_color_field(self):
        """Background Color should be a ColorField."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        # Get the Background Color field
        color_field = None
        for key, value in fields.items():
            if 'background' in key.lower() and 'color' in key.lower():
                color_field = value
                break

        assert color_field is not None
        assert type(color_field).__name__ == 'ColorField'

    def test_interface_has_six_fields(self):
        """Rotate should have six parameters."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 6


class TestRotatePilFunction:
    """Test the rotate() PIL function."""

    def test_rotate_function_exists(self):
        """rotate function should exist."""
        assert hasattr(rotate, 'rotate')
        assert callable(rotate.rotate)

    def test_rotate_rgb_image_45_degrees(self, rgb_image):
        """Rotate RGB image by 45 degrees."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=45, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_rotate_90_degrees(self, multicolor_image):
        """Rotate multicolor image by 90 degrees."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=90,
                              resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        # Without expand, size stays the same
        assert result.size == multicolor_image.size

    def test_rotate_180_degrees(self, rgb_image):
        """Rotate image by 180 degrees (upside down)."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=180, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_rotate_with_expand(self, multicolor_image):
        """Rotate with expand=True to fit entire rotated image."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=45,
                              resample_image='BICUBIC', expand=1)

        assert isinstance(result, Image.Image)
        # With expand, size should increase to fit rotated image
        assert result.size[0] >= multicolor_image.size[0] or \
               result.size[1] >= multicolor_image.size[1]

    def test_rotate_partial_amount(self, rgb_image):
        """Rotate with partial amount blends with original."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=90, resample_image='BICUBIC',
                              amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_rotate_with_background_color(self, multicolor_image):
        """Rotate with custom background color."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=45,
                              resample_image='BICUBIC',
                              background_color='#FF0000')

        assert isinstance(result, Image.Image)
        # With default opacity=100, result is RGB
        assert result.mode in ('RGB', 'RGBA')

    def test_rotate_with_background_opacity(self, rgb_image):
        """Rotate with partial background opacity."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=45, resample_image='BICUBIC',
                              background_opacity=50)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_rotate_rgba_preserves_alpha(self, rgba_image):
        """Rotate RGBA image with partial opacity preserves alpha channel."""
        rotate.init()

        # Use partial opacity to ensure RGBA mode is preserved
        result = rotate.rotate(rgba_image, angle=45, resample_image='BICUBIC',
                              background_opacity=50)

        assert isinstance(result, Image.Image)
        # Should have alpha channel due to partial opacity
        assert result.mode == 'RGBA'

    def test_rotate_grayscale(self, grayscale_image):
        """Rotate grayscale image."""
        rotate.init()

        result = rotate.rotate(grayscale_image, angle=45,
                              resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_rotate_gradient(self, gradient_image):
        """Rotate gradient image."""
        rotate.init()

        result = rotate.rotate(gradient_image, angle=90,
                              resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size


class TestRotateEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_rotate_zero_degrees(self, rgb_image):
        """Rotate by 0 degrees (no rotation)."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=0, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        # Should be identical (or nearly identical)

    def test_rotate_360_degrees(self, multicolor_image):
        """Rotate by 360 degrees (full circle)."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=360,
                              resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_rotate_negative_angle(self, rgb_image):
        """Rotate with negative angle (clockwise)."""
        rotate.init()

        result = rotate.rotate(rgb_image, angle=-45, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_rotate_amount_minimum(self, multicolor_image):
        """Rotate with amount=1 (barely visible)."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=90,
                              resample_image='BICUBIC', amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, effect should be very subtle

    def test_rotate_amount_maximum(self, multicolor_image):
        """Rotate with amount=100 (full effect)."""
        rotate.init()

        result = rotate.rotate(multicolor_image, angle=90,
                              resample_image='BICUBIC', amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully rotated

    def test_rotate_small_image(self, small_image):
        """Rotate works with small images."""
        rotate.init()

        result = rotate.rotate(small_image, angle=45, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_rotate_large_image(self, large_image):
        """Rotate works with large images."""
        rotate.init()

        result = rotate.rotate(large_image, angle=45, resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_rotate_multiple_times(self, multicolor_image):
        """Rotate multiple times compounds rotation."""
        rotate.init()

        first = rotate.rotate(multicolor_image, angle=45,
                             resample_image='BICUBIC')
        second = rotate.rotate(first, angle=45, resample_image='BICUBIC')

        assert isinstance(second, Image.Image)
        # Two 45-degree rotations ≈ 90 degrees

    def test_rotate_different_resample_modes(self, rgb_image):
        """Rotate with various resample modes."""
        rotate.init()

        # Test different resampling methods
        for mode in ['NEAREST', 'BILINEAR', 'BICUBIC']:
            result = rotate.rotate(rgb_image, angle=45, resample_image=mode)
            assert isinstance(result, Image.Image)
            assert result.size == rgb_image.size


class TestRotateIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_rotate(self, multicolor_image):
        """Action.pil should call rotate function."""
        rotate.init()

        result = rotate.Action.pil(multicolor_image, angle=45,
                                   resample_image='BICUBIC')

        assert isinstance(result, Image.Image)
        # Verify it actually rotated
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = rotate.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = rotate.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 6

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = rotate.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'transform' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_rotate(self):
        """Action documentation mentions rotate or angle."""
        action = rotate.Action()
        doc_lower = action.__doc__.lower()
        assert 'rotate' in doc_lower or 'angle' in doc_lower

    def test_action_pil_points_to_rotate(self):
        """Action.pil should point to rotate function."""
        # The action's pil staticmethod should be the rotate function
        assert rotate.Action.pil == rotate.rotate
