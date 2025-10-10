"""Unit tests for phatch.actions.colorize module.

Tests the Colorize action (apply color mapping to grayscale).

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
from phatch.actions import colorize


class TestColorizeAction:
    """Test the Colorize action class metadata."""

    def test_action_exists(self):
        """Colorize action class should exist."""
        assert hasattr(colorize, 'Action')
        assert colorize.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = colorize.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = colorize.Action()
        assert 'colorize' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(colorize.Action, 'pil')
        assert callable(colorize.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(colorize.Action, 'init')
        assert callable(colorize.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = colorize.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)


class TestColorizeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_black_field(self):
        """interface should define Black color parameter."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        # Should have Black field
        assert any('black' in k.lower() for k in fields.keys())

    def test_interface_defines_white_field(self):
        """interface should define White color parameter."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        # Should have White field
        assert any('white' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        # Should have Amount field
        assert any('amount' in k.lower() for k in fields.keys())

    def test_interface_black_is_color_field(self):
        """Black field should be a ColorField."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        # Get the Black field
        black_field = None
        for key, value in fields.items():
            if 'black' in key.lower():
                black_field = value
                break

        assert black_field is not None
        assert type(black_field).__name__ == 'ColorField'

    def test_interface_white_is_color_field(self):
        """White field should be a ColorField."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        # Get the White field
        white_field = None
        for key, value in fields.items():
            if 'white' in key.lower():
                white_field = value
                break

        assert white_field is not None
        assert type(white_field).__name__ == 'ColorField'

    def test_interface_amount_is_slider(self):
        """Amount field should be a SliderField."""
        action = colorize.Action()
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

    def test_interface_has_three_fields(self):
        """Colorize should have three parameters."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 3


class TestColorizePilFunction:
    """Test the colorize() PIL function."""

    def test_colorize_function_exists(self):
        """colorize function should exist."""
        assert hasattr(colorize, 'colorize')
        assert callable(colorize.colorize)

    def test_colorize_grayscale_image(self, grayscale_image):
        """Colorize grayscale image with full amount."""
        colorize.init()

        result = colorize.colorize(grayscale_image, 'black', 'white', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_colorize_rgb_to_sepia(self, rgb_image):
        """Colorize RGB image converts to grayscale first then applies sepia."""
        colorize.init()

        # Sepia-like colors
        result = colorize.colorize(rgb_image, '#704214', '#C8B098', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_colorize_with_custom_colors(self, grayscale_image):
        """Colorize with custom black and white colors."""
        colorize.init()

        # Blue tint
        result = colorize.colorize(grayscale_image, '#000080', '#4080FF', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_colorize_partial_amount(self, grayscale_image):
        """Colorize with partial amount blends with original."""
        colorize.init()

        result = colorize.colorize(grayscale_image, 'black', 'white', amount=50)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size

    def test_colorize_preserves_alpha(self, rgba_image):
        """Colorize RGBA image preserves alpha channel."""
        colorize.init()

        result = colorize.colorize(rgba_image, 'black', 'white', amount=100)

        assert isinstance(result, Image.Image)
        # Should still have alpha channel
        assert result.mode == 'RGBA'

        # Check a semi-transparent pixel preserves alpha
        pixel_with_alpha = result.getpixel((25, 25))
        assert len(pixel_with_alpha) == 4
        assert pixel_with_alpha[3] == 128  # Alpha preserved

    def test_colorize_gradient(self, gradient_image):
        """Colorize gradient maintains tonal range."""
        colorize.init()

        result = colorize.colorize(gradient_image, '#FF0000', '#00FF00', amount=100)

        assert isinstance(result, Image.Image)
        # Gradient pattern should be preserved
        left_pixel = result.getpixel((0, 50))
        right_pixel = result.getpixel((99, 50))

        # Left should map to black (red), right to white (green)
        # Red should dominate left pixel
        assert left_pixel[0] > left_pixel[1]
        # Green should dominate right pixel
        assert right_pixel[1] > right_pixel[0]

    def test_colorize_multicolor(self, multicolor_image):
        """Colorize multicolor converts to grayscale first."""
        colorize.init()

        result = colorize.colorize(multicolor_image, 'blue', 'yellow', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == multicolor_image.size
        # Different brightness levels should map to different colors along gradient


class TestColorizeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_colorize_amount_minimum(self, grayscale_image):
        """Colorize with amount=1 (barely visible)."""
        colorize.init()

        result = colorize.colorize(grayscale_image, 'red', 'blue', amount=1)

        assert isinstance(result, Image.Image)
        # With amount=1, effect should be very subtle

    def test_colorize_amount_maximum(self, grayscale_image):
        """Colorize with amount=100 (full effect)."""
        colorize.init()

        result = colorize.colorize(grayscale_image, 'red', 'blue', amount=100)

        assert isinstance(result, Image.Image)
        # Should be fully colorized

    def test_colorize_small_image(self, small_image):
        """Colorize works with small images."""
        colorize.init()

        result = colorize.colorize(small_image, 'black', 'white', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    def test_colorize_large_image(self, large_image):
        """Colorize works with large images."""
        colorize.init()

        result = colorize.colorize(large_image, 'black', 'white', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == large_image.size

    def test_colorize_twice(self, grayscale_image):
        """Colorizing twice applies second color scheme."""
        colorize.init()

        first = colorize.colorize(grayscale_image, 'red', 'yellow', amount=100)
        second = colorize.colorize(first, 'blue', 'green', amount=100)

        assert isinstance(second, Image.Image)
        # Second colorization replaces first

    def test_colorize_same_colors(self, grayscale_image):
        """Colorize with same black and white creates uniform tint."""
        colorize.init()

        result = colorize.colorize(grayscale_image, '#808080', '#808080', amount=100)

        assert isinstance(result, Image.Image)
        # Should create gray tint

    def test_colorize_already_grayscale(self, grayscale_image):
        """Colorize already grayscale image works efficiently."""
        colorize.init()

        # Should not need conversion
        result = colorize.colorize(grayscale_image, 'purple', 'orange', amount=100)

        assert isinstance(result, Image.Image)
        assert result.size == grayscale_image.size


class TestColorizeIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_colorize(self, grayscale_image):
        """Action.pil should call colorize function."""
        colorize.init()

        result = colorize.Action.pil(grayscale_image, black='black',
                                      white='white', amount=100)

        assert isinstance(result, Image.Image)
        # Verify it actually colorized
        assert result.size == grayscale_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = colorize.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = colorize.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 3  # Black, White, Amount

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = colorize.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_colorize(self):
        """Action documentation mentions colorize or grayscale."""
        action = colorize.Action()
        doc_lower = action.__doc__.lower()
        assert 'colorize' in doc_lower or 'grayscale' in doc_lower or 'gray' in doc_lower

    def test_action_pil_points_to_colorize(self):
        """Action.pil should point to colorize function."""
        # The action's pil staticmethod should be the colorize function
        assert colorize.Action.pil == colorize.colorize
