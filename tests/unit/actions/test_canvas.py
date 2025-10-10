"""Unit tests for phatch.actions.canvas module.

Tests the Canvas action (crop or expand canvas without scaling).

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
from phatch.actions import canvas


class TestCanvasAction:
    """Test the Canvas action class metadata."""

    def test_action_exists(self):
        """Canvas action class should exist."""
        assert hasattr(canvas, 'Action')
        assert canvas.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = canvas.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = canvas.Action()
        assert 'canvas' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(canvas.Action, 'pil')
        assert callable(canvas.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(canvas.Action, 'init')
        assert callable(canvas.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = canvas.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = canvas.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = canvas.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower

    def test_action_all_layers(self):
        """Canvas action should have all_layers=True."""
        action = canvas.Action()
        assert hasattr(action, 'all_layers')
        assert action.all_layers is True


class TestCanvasInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_width_field(self):
        """interface should define Canvas Width parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Width field
        assert any('width' in k.lower() for k in fields.keys())

    def test_interface_defines_height_field(self):
        """interface should define Canvas Height parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Height field
        assert any('height' in k.lower() for k in fields.keys())

    def test_interface_defines_resolution_field(self):
        """interface should define Resolution parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Resolution field
        assert any('resolution' in k.lower() for k in fields.keys())

    def test_interface_defines_align_horizontal_field(self):
        """interface should define Align Horizontal parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Align Horizontal field
        assert any('align' in k.lower() and 'horizontal' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_align_vertical_field(self):
        """interface should define Align Vertical parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Align Vertical field
        assert any('align' in k.lower() and 'vertical' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_background_color_field(self):
        """interface should define Background Color parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Background Color field
        assert any('background' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Should have Opacity field
        assert any('opacity' in k.lower() for k in fields.keys())

    def test_interface_width_is_pixel_field(self):
        """Width field should be a PixelField."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Get the Width field
        width_field = None
        for key, value in fields.items():
            if 'width' in key.lower():
                width_field = value
                break

        assert width_field is not None
        assert type(width_field).__name__ == 'PixelField'

    def test_interface_align_horizontal_is_slider(self):
        """Align Horizontal field should be a SliderField."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        # Get the Align Horizontal field
        align_field = None
        for key, value in fields.items():
            if 'align' in key.lower() and 'horizontal' in key.lower():
                align_field = value
                break

        assert align_field is not None
        assert type(align_field).__name__ == 'SliderField'

    def test_interface_background_color_is_color_field(self):
        """Background Color should be a ColorField."""
        action = canvas.Action()
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

    def test_interface_has_seven_fields(self):
        """Canvas should have seven parameters."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 7


class TestCanvasSizeFunction:
    """Test the canvas_size() PIL function."""

    def test_canvas_size_function_exists(self):
        """canvas_size function should exist."""
        assert hasattr(canvas, 'canvas_size')
        assert callable(canvas.canvas_size)

    def test_canvas_size_expand_both(self, rgb_image):
        """Expand canvas in both dimensions."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        # Canvas should be expanded
        assert result.size == (200, 200)

    def test_canvas_size_expand_width(self, rgb_image):
        """Expand canvas width only."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 100), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 100)

    def test_canvas_size_expand_height(self, rgb_image):
        """Expand canvas height only."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (100, 200), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (100, 200)

    def test_canvas_size_same_size(self, rgb_image):
        """Canvas same size as image returns original."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (100, 100), (50, 50),
                                   '#FFFFFF', 255)

        # Should return original image when size is same
        assert result is rgb_image or result.size == (100, 100)

    def test_canvas_size_center_alignment(self, rgb_image):
        """Canvas with center alignment (50, 50)."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_left_top_alignment(self, rgb_image):
        """Canvas with left-top alignment (0, 0)."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (0, 0),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_right_bottom_alignment(self, rgb_image):
        """Canvas with right-bottom alignment (100, 100)."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (100, 100),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_custom_color(self, rgb_image):
        """Canvas with custom background color."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FF0000', 255)

        assert isinstance(result, Image.Image)
        # Check background is red (corners should be red)
        corner_pixel = result.getpixel((0, 0))
        assert corner_pixel == (255, 0, 0)

    def test_canvas_size_rgba_image(self, rgba_image):
        """Canvas with RGBA image preserves alpha."""
        canvas.init()

        result = canvas.canvas_size(rgba_image, (200, 200), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        # Should preserve RGBA mode
        assert result.mode == 'RGBA'

    def test_canvas_size_grayscale(self, grayscale_image):
        """Canvas with grayscale image."""
        canvas.init()

        result = canvas.canvas_size(grayscale_image, (200, 200), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)


class TestCanvasEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_canvas_size_zero_opacity(self, rgb_image):
        """Canvas with zero opacity (no image)."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FFFFFF', 0)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_partial_opacity(self, rgb_image):
        """Canvas with partial opacity."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FFFFFF', 128)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_small_image(self, small_image):
        """Canvas works with small images."""
        canvas.init()

        result = canvas.canvas_size(small_image, (50, 50), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_canvas_size_large_expansion(self, rgb_image):
        """Canvas with large expansion."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (500, 500), (50, 50),
                                   '#FFFFFF', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (500, 500)

    def test_canvas_size_with_old_size(self, rgb_image):
        """Canvas with explicit old_size parameter."""
        canvas.init()

        result = canvas.canvas_size(rgb_image, (200, 200), (50, 50),
                                   '#FFFFFF', 255, old_size=(100, 100))

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_canvas_size_multicolor(self, multicolor_image):
        """Canvas with multicolor image."""
        canvas.init()

        result = canvas.canvas_size(multicolor_image, (200, 200), (50, 50),
                                   '#000000', 255)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)


class TestCanvasIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_canvas_size(self, multicolor_image):
        """Action.pil should call canvas_size function."""
        canvas.init()

        result = canvas.Action.pil(multicolor_image, new_size=(200, 200),
                                  centering=(50, 50),
                                  background_color='#FFFFFF', opacity=255)

        assert isinstance(result, Image.Image)
        # Verify it actually expanded canvas
        assert result.size == (200, 200)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = canvas.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = canvas.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 7

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = canvas.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower

    def test_action_docstring_mentions_canvas(self):
        """Action documentation mentions canvas or expand."""
        action = canvas.Action()
        doc_lower = action.__doc__.lower()
        assert 'canvas' in doc_lower or 'expand' in doc_lower or 'crop' in doc_lower

    def test_action_pil_points_to_canvas_size(self):
        """Action.pil should point to canvas_size function."""
        # The action's pil staticmethod should be the canvas_size function
        assert canvas.Action.pil == canvas.canvas_size

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        canvas.init()
        # After init, Image should be available in the module
        assert hasattr(canvas, 'Image')

    def test_init_loads_imtools(self):
        """init() should load imtools module."""
        canvas.init()
        # After init, imtools should be available
        assert hasattr(canvas, 'imtools')

    def test_init_loads_colors(self):
        """init() should load color conversion function."""
        canvas.init()
        # After init, HTMLColorToRGBA should be available
        assert hasattr(canvas, 'HTMLColorToRGBA')
