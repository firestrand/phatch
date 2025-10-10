"""Unit tests for phatch.actions.border module.

Tests the Border action (draw border inside or outside).

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
from phatch.actions import border


class TestBorderAction:
    """Test the Border action class metadata."""

    def test_action_exists(self):
        """Border action class should exist."""
        assert hasattr(border, 'Action')
        assert border.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = border.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = border.Action()
        assert 'border' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(border.Action, 'pil')
        assert callable(border.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(border.Action, 'init')
        assert callable(border.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = border.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = border.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_has_get_relevant_field_labels(self):
        """Action should have get_relevant_field_labels method."""
        action = border.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = border.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestBorderConstants:
    """Test module-level constants."""

    def test_options_constant_exists(self):
        """OPTIONS constant should exist."""
        assert hasattr(border, 'OPTIONS')
        assert isinstance(border.OPTIONS, list)

    def test_options_has_two_values(self):
        """OPTIONS should have two values."""
        assert len(border.OPTIONS) == 2

    def test_options_has_equal_option(self):
        """OPTIONS should include Equal for all sides."""
        options_lower = [str(o).lower() for o in border.OPTIONS]
        assert any('equal' in o for o in options_lower)

    def test_options_has_different_option(self):
        """OPTIONS should include Different for each side."""
        options_lower = [str(o).lower() for o in border.OPTIONS]
        assert any('different' in o for o in options_lower)

    def test_choices_constant_exists(self):
        """CHOICES constant should exist."""
        assert hasattr(border, 'CHOICES')
        assert isinstance(border.CHOICES, list)

    def test_choices_has_values(self):
        """CHOICES should have multiple values."""
        assert len(border.CHOICES) > 0

    def test_choices_includes_negatives(self):
        """CHOICES should include negative values for cropping."""
        assert '-25' in border.CHOICES or '-10' in border.CHOICES


class TestBorderInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_method_field(self):
        """interface should define Method parameter."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Should have Method field
        assert any('method' in k.lower() for k in fields.keys())

    def test_interface_defines_border_width_field(self):
        """interface should define Border Width parameter."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Should have Border Width field
        assert any('border' in k.lower() and 'width' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_side_fields(self):
        """interface should define Left, Right, Top, Bottom parameters."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Should have all four side fields
        assert any('left' in k.lower() for k in fields.keys())
        assert any('right' in k.lower() for k in fields.keys())
        assert any('top' in k.lower() for k in fields.keys())
        assert any('bottom' in k.lower() for k in fields.keys())

    def test_interface_defines_color_field(self):
        """interface should define Color parameter."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Should have Color field
        assert any('color' in k.lower() for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Should have Opacity field
        assert any('opacity' in k.lower() for k in fields.keys())

    def test_interface_method_is_choice_field(self):
        """Method field should be a ChoiceField."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Get the Method field
        method_field = None
        for key, value in fields.items():
            if 'method' in key.lower():
                method_field = value
                break

        assert method_field is not None
        assert type(method_field).__name__ == 'ChoiceField'

    def test_interface_color_is_color_field(self):
        """Color field should be a ColorField."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Get the Color field
        color_field = None
        for key, value in fields.items():
            if 'color' in key.lower():
                color_field = value
                break

        assert color_field is not None
        assert type(color_field).__name__ == 'ColorField'

    def test_interface_opacity_is_slider(self):
        """Opacity field should be a SliderField."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        # Get the Opacity field
        opacity_field = None
        for key, value in fields.items():
            if 'opacity' in key.lower():
                opacity_field = value
                break

        assert opacity_field is not None
        assert type(opacity_field).__name__ == 'SliderField'

    def test_interface_has_eight_fields(self):
        """Border should have eight parameters."""
        action = border.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 8


class TestBorderFunction:
    """Test the border() PIL function."""

    def test_border_function_exists(self):
        """border function should exist."""
        assert hasattr(border, 'border')
        assert callable(border.border)

    def test_border_equal_positive(self, rgb_image):
        """Border with equal method and positive width."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=10, color=(255, 0, 0))

        assert isinstance(result, Image.Image)
        # Size should increase by border on all sides
        assert result.size == (120, 120)

    def test_border_equal_color(self, rgb_image):
        """Border with equal method has correct color."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=10, color=(255, 0, 0))

        assert isinstance(result, Image.Image)
        # Border pixel should be red
        border_pixel = result.getpixel((0, 0))
        assert border_pixel == (255, 0, 0)

    def test_border_different_all_positive(self, rgb_image):
        """Border with different method and all positive values."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[1],
                              left=5, right=10, top=15, bottom=20,
                              color=(0, 255, 0))

        assert isinstance(result, Image.Image)
        # Width: 100 + 5 + 10 = 115
        # Height: 100 + 15 + 20 = 135
        assert result.size == (115, 135)

    def test_border_different_asymmetric(self, rgb_image):
        """Border with different method, asymmetric values."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[1],
                              left=5, right=5, top=10, bottom=10,
                              color=(0, 0, 255))

        assert isinstance(result, Image.Image)
        assert result.size == (110, 120)

    def test_border_negative_crop(self, multicolor_image):
        """Border with negative values overlays transparency."""
        border.init()

        result = border.border(multicolor_image, border.OPTIONS[0],
                              border_width=-10, color=(0, 0, 0),
                              opacity=100)

        assert isinstance(result, Image.Image)
        # Negative borders don't change size, they overlay transparency
        assert result.size == multicolor_image.size

    def test_border_negative_with_opacity(self, multicolor_image):
        """Border with negative values and partial opacity."""
        border.init()

        result = border.border(multicolor_image, border.OPTIONS[1],
                              left=-10, right=-10, top=-10, bottom=-10,
                              color=(0, 0, 0), opacity=50)

        assert isinstance(result, Image.Image)
        # Should be RGBA due to opacity
        assert result.mode == 'RGBA'

    def test_border_rgba_transparency_preserved(self, rgba_image):
        """Border on RGBA image preserves transparency."""
        border.init()

        result = border.border(rgba_image, border.OPTIONS[0],
                              border_width=10, color=(255, 255, 255, 255))

        assert isinstance(result, Image.Image)
        # Should be RGBA mode
        assert result.mode == 'RGBA'

    def test_border_grayscale(self, grayscale_image):
        """Border on grayscale image."""
        border.init()

        result = border.border(grayscale_image, border.OPTIONS[0],
                              border_width=10, color=(128, 128, 128))

        assert isinstance(result, Image.Image)
        assert result.size == (120, 120)


class TestBorderEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_border_zero_width(self, rgb_image):
        """Border with zero width."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=0, color=(0, 0, 0))

        assert isinstance(result, Image.Image)
        # Size should remain same
        assert result.size == rgb_image.size

    def test_border_mixed_positive_negative(self, rgb_image):
        """Border with mixed positive and negative values."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[1],
                              left=10, right=-5, top=10, bottom=-5,
                              color=(255, 0, 0))

        assert isinstance(result, Image.Image)

    def test_border_small_image(self, small_image):
        """Border works with small images."""
        border.init()

        result = border.border(small_image, border.OPTIONS[0],
                              border_width=5, color=(255, 0, 0))

        assert isinstance(result, Image.Image)
        assert result.size == (20, 20)

    def test_border_large_border(self, rgb_image):
        """Border with large border width."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=50, color=(0, 255, 0))

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_border_opacity_minimum(self, rgb_image):
        """Border with minimum opacity."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=10, color=(255, 0, 0),
                              opacity=1)

        assert isinstance(result, Image.Image)

    def test_border_opacity_maximum(self, rgb_image):
        """Border with maximum opacity."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[0],
                              border_width=10, color=(255, 0, 0),
                              opacity=100)

        assert isinstance(result, Image.Image)

    def test_border_different_colors(self, rgb_image):
        """Border with various colors."""
        border.init()

        # Test different colors
        for color in [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255),
                      (255, 255, 0)]:
            result = border.border(rgb_image, border.OPTIONS[0],
                                  border_width=5, color=color)
            assert isinstance(result, Image.Image)

    def test_border_all_negative(self, rgb_image):
        """Border with all negative values (overlay)."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[1],
                              left=-10, right=-10, top=-10, bottom=-10,
                              color=(0, 0, 0), opacity=100)

        assert isinstance(result, Image.Image)
        # Negative borders overlay transparency, don't change size
        assert result.size == rgb_image.size

    def test_border_one_side_only(self, rgb_image):
        """Border on one side only."""
        border.init()

        result = border.border(rgb_image, border.OPTIONS[1],
                              left=20, right=0, top=0, bottom=0,
                              color=(255, 0, 0))

        assert isinstance(result, Image.Image)
        # Only width should change
        assert result.size == (120, 100)


class TestBorderIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_border(self, multicolor_image):
        """Action.pil should call border function."""
        border.init()

        result = border.Action.pil(multicolor_image, method=border.OPTIONS[0],
                                  border_width=10, color=(255, 255, 255))

        assert isinstance(result, Image.Image)
        # Verify it actually added border
        assert result.size == (120, 120)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = border.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = border.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 8

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = border.Action()
        assert action.author == 'Erich'
        assert action.version == '0.2'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower

    def test_action_docstring_mentions_border(self):
        """Action documentation mentions border."""
        action = border.Action()
        doc_lower = action.__doc__.lower()
        assert 'border' in doc_lower

    def test_action_pil_points_to_border(self):
        """Action.pil should point to border function."""
        # The action's pil staticmethod should be the border function
        assert border.Action.pil == border.border

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        border.init()
        # After init, Image should be available in the module
        assert hasattr(border, 'Image')

    def test_init_loads_image_draw(self):
        """init() should load ImageDraw module."""
        border.init()
        # After init, ImageDraw should be available
        assert hasattr(border, 'ImageDraw')

    def test_get_relevant_field_labels_equal_method(self):
        """get_relevant_field_labels with Equal method."""
        action = border.Action()
        # Set method to Equal for all sides
        action.get_field = lambda x: border.OPTIONS[0] if x == 'Method' else None
        action.get_field_string = lambda x: border.OPTIONS[0] if x == 'Method' else None

        relevant = action.get_relevant_field_labels()

        # Should include Method, Border Width, Color, Opacity
        # Should NOT include Left, Right, Top, Bottom
        assert 'Method' in relevant
        assert 'Border Width' in relevant
        assert 'Color' in relevant
        assert 'Opacity' in relevant

    def test_get_relevant_field_labels_different_method(self):
        """get_relevant_field_labels with Different method."""
        action = border.Action()
        # Set method to Different for each side
        action.get_field = lambda x: border.OPTIONS[1] if x == 'Method' else None
        action.get_field_string = lambda x: border.OPTIONS[1] if x == 'Method' else None

        relevant = action.get_relevant_field_labels()

        # Should include Method, Left, Right, Top, Bottom, Color, Opacity
        # Should NOT include Border Width
        assert 'Method' in relevant
        assert 'Left' in relevant
        assert 'Right' in relevant
        assert 'Top' in relevant
        assert 'Bottom' in relevant
        assert 'Color' in relevant
        assert 'Opacity' in relevant
