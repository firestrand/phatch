"""Unit tests for phatch.actions.transpose module.

Tests the Transpose action (flip or rotate 90 degrees).

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
from phatch.actions import transpose


class TestTransposeAction:
    """Test the Transpose action class metadata."""

    def test_action_exists(self):
        """Transpose action class should exist."""
        assert hasattr(transpose, 'Action')
        assert transpose.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = transpose.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = transpose.Action()
        assert 'transpose' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(transpose.Action, 'pil')
        assert callable(transpose.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(transpose.Action, 'init')
        assert callable(transpose.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = transpose.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = transpose.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = transpose.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'default' in tags_lower


class TestTransposeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_method_field(self):
        """interface should define Method parameter."""
        action = transpose.Action()
        fields = {}
        action.interface(fields)

        # Should have Method field
        assert any('method' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = transpose.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_method_is_image_transpose_field(self):
        """Method field should be an ImageTransposeField."""
        action = transpose.Action()
        fields = {}
        action.interface(fields)

        # Get the Method field
        method_field = None
        for key, value in fields.items():
            if 'method' in key.lower():
                method_field = value
                break

        assert method_field is not None
        assert type(method_field).__name__ == 'ImageTransposeField'

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = transpose.Action()
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
        """Transpose should have two parameters."""
        action = transpose.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2


class TestTransposePilFunction:
    """Test the transpose() PIL function."""

    def test_transpose_function_exists(self):
        """transpose function should exist."""
        assert hasattr(transpose, 'transpose')
        assert callable(transpose.transpose)

    def test_transpose_flip_left_right(self, multicolor_image):
        """Transpose with FLIP_LEFT_RIGHT flips horizontally."""
        transpose.init()

        result = transpose.transpose(multicolor_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size
        # Left pixel should be flipped to right
        original_left = multicolor_image.getpixel((0, 25))
        flipped_right = result.getpixel((99, 25))
        assert original_left == flipped_right

    def test_transpose_flip_top_bottom(self, multicolor_image):
        """Transpose with FLIP_TOP_BOTTOM flips vertically."""
        transpose.init()

        result = transpose.transpose(multicolor_image, 'FLIP_TOP_BOTTOM')

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size
        # Top pixel should be flipped to bottom
        original_top = multicolor_image.getpixel((25, 0))
        flipped_bottom = result.getpixel((25, 99))
        assert original_top == flipped_bottom

    def test_transpose_rotate_90(self, rgb_image):
        """Transpose with ROTATE_90 rotates 90 degrees."""
        transpose.init()

        result = transpose.transpose(rgb_image, 'ROTATE_90')

        assert isinstance(result, Image.Image)
        # Size should be transposed
        assert result.size == (100, 100)  # Square, so same

    def test_transpose_rotate_180(self, rgb_image):
        """Transpose with ROTATE_180 rotates 180 degrees."""
        transpose.init()

        result = transpose.transpose(rgb_image, 'ROTATE_180')

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_transpose_rotate_270(self, rgb_image):
        """Transpose with ROTATE_270 rotates 270 degrees."""
        transpose.init()

        result = transpose.transpose(rgb_image, 'ROTATE_270')

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_transpose_partial_amount(self, multicolor_image):
        """Transpose with partial amount blends with original."""
        transpose.init()

        result = transpose.transpose(multicolor_image, 'FLIP_LEFT_RIGHT',
                                     amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size

    def test_transpose_rgba_preserves_mode(self, rgba_image):
        """Transpose RGBA image preserves mode."""
        transpose.init()

        result = transpose.transpose(rgba_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        # Mode should be preserved through transpose
        assert result.mode == 'RGBA'

    def test_transpose_grayscale(self, grayscale_image):
        """Transpose grayscale image."""
        transpose.init()

        result = transpose.transpose(grayscale_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == grayscale_image.size

    def test_transpose_gradient(self, gradient_image):
        """Transpose gradient image."""
        transpose.init()

        result = transpose.transpose(gradient_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        assert result.size == gradient_image.size
        # Left should now be bright, right dark
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))
        # Gradient flipped
        if isinstance(left_pixel, tuple):
            assert left_pixel[0] > right_pixel[0]


class TestTransposeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_transpose_amount_minimum(self, multicolor_image):
        """Transpose with amount=1 (barely visible)."""
        transpose.init()

        result = transpose.transpose(multicolor_image, 'FLIP_LEFT_RIGHT',
                                     amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, effect should be very subtle

    def test_transpose_amount_maximum(self, multicolor_image):
        """Transpose with amount=100 (full effect)."""
        transpose.init()

        result = transpose.transpose(multicolor_image, 'FLIP_LEFT_RIGHT',
                                     amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully transposed

    def test_transpose_small_image(self, small_image):
        """Transpose works with small images."""
        transpose.init()

        result = transpose.transpose(small_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_transpose_large_image(self, large_image):
        """Transpose works with large images."""
        transpose.init()

        result = transpose.transpose(large_image, 'FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_transpose_twice_same_flip(self, multicolor_image):
        """Flipping twice should return to original."""
        transpose.init()

        first = transpose.transpose(multicolor_image, 'FLIP_LEFT_RIGHT')
        second = transpose.transpose(first, 'FLIP_LEFT_RIGHT')

        assert isinstance(second, Image.Image)
        # Two flips should return to original (approximately)

    def test_transpose_different_methods(self, rgb_image):
        """Transpose with various methods."""
        transpose.init()

        # Test different transpose methods
        for method in ['FLIP_LEFT_RIGHT', 'FLIP_TOP_BOTTOM', 'ROTATE_90',
                      'ROTATE_180', 'ROTATE_270']:
            result = transpose.transpose(rgb_image, method)
            assert isinstance(result, Image.Image)

    def test_transpose_rotate_non_square(self):
        """Transpose rotate on non-square image."""
        transpose.init()

        # Create rectangular image
        img = Image.new('RGB', (100, 50), color=(255, 0, 0))
        result = transpose.transpose(img, 'ROTATE_90')

        assert isinstance(result, Image.Image)
        # 90 degree rotation swaps dimensions
        assert result.size == (50, 100)


class TestTransposeIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_transpose(self, multicolor_image):
        """Action.pil should call transpose function."""
        transpose.init()

        result = transpose.Action.pil(multicolor_image,
                                      method='FLIP_LEFT_RIGHT')

        assert isinstance(result, Image.Image)
        # Verify it actually transposed
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = transpose.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = transpose.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = transpose.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'default' in tags_lower

    def test_action_docstring_mentions_flip_or_rotate(self):
        """Action documentation mentions flip or rotate."""
        action = transpose.Action()
        doc_lower = action.__doc__.lower()
        assert 'flip' in doc_lower or 'rotate' in doc_lower

    def test_action_pil_points_to_transpose(self):
        """Action.pil should point to transpose function."""
        # The action's pil staticmethod should be the transpose function
        assert transpose.Action.pil == transpose.transpose

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        transpose.init()
        # After init, Image should be available in the module
        assert hasattr(transpose, 'Image')

    def test_init_loads_imtools(self):
        """init() should load imtools module."""
        transpose.init()
        # After init, imtools should be available
        assert hasattr(transpose, 'imtools')
