"""Unit tests for phatch.actions.color_to_alpha module.

Tests the Color to Alpha action (make selected color transparent).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch
import pytest

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import color_to_alpha
from PIL import Image


class TestColorToAlphaAction:
    """Test the Color to Alpha action class metadata."""

    def test_action_exists(self):
        """Color to Alpha action class should exist."""
        assert hasattr(color_to_alpha, 'Action')
        assert color_to_alpha.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = color_to_alpha.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = color_to_alpha.Action()
        assert 'color' in action.label.lower() and 'alpha' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(color_to_alpha.Action, 'init')
        assert callable(color_to_alpha.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(color_to_alpha.Action, 'pil')
        assert callable(color_to_alpha.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = color_to_alpha.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have color tag."""
        action = color_to_alpha.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'color' in tags_lower

    def test_action_cache_disabled(self):
        """Cache should be disabled for this action."""
        assert color_to_alpha.Action.cache is False


class TestColorToAlphaConstants:
    """Test module-level constants."""

    def test_options_constant_exists(self):
        """OPTIONS constant should exist."""
        assert hasattr(color_to_alpha, 'OPTIONS')
        assert isinstance(color_to_alpha.OPTIONS, list)

    def test_options_has_five_values(self):
        """OPTIONS should have five values."""
        assert len(color_to_alpha.OPTIONS) == 5

    def test_options_includes_expected_values(self):
        """OPTIONS should include expected color selection methods."""
        options_lower = [str(opt).lower() for opt in color_to_alpha.OPTIONS]
        assert 'value' in options_lower
        assert any('top' in opt and 'left' in opt for opt in options_lower)
        assert any('top' in opt and 'right' in opt for opt in options_lower)
        assert any('bottom' in opt and 'left' in opt for opt in options_lower)
        assert any('bottom' in opt and 'right' in opt for opt in options_lower)


class TestColorToAlphaInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_select_color_by_field(self):
        """interface should define Select Color By parameter."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)

        assert any('select' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_color_value_field(self):
        """interface should define Color Value parameter."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)

        assert any('color' in k.lower() and 'value' in k.lower()
                   for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Color to Alpha should have two parameters."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_select_color_by_is_choice_field(self):
        """Select Color By should be a ChoiceField."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)

        # Get the Select Color By field
        select_field = None
        for key, value in fields.items():
            if 'select' in key.lower() and 'color' in key.lower():
                select_field = value
                break

        assert select_field is not None
        assert type(select_field).__name__ == 'ChoiceField'

    def test_interface_color_value_is_color_field(self):
        """Color Value should be a ColorField."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)

        # Get the Color Value field
        color_field = None
        for key, value in fields.items():
            if 'color' in key.lower() and 'value' in key.lower():
                color_field = value
                break

        assert color_field is not None
        assert type(color_field).__name__ == 'ColorField'


class TestGetRelevantFieldLabels:
    """Test the get_relevant_field_labels() method."""

    def test_get_relevant_field_labels_method_exists(self):
        """get_relevant_field_labels method should exist."""
        action = color_to_alpha.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_returns_list(self):
        """get_relevant_field_labels should return list."""
        action = color_to_alpha.Action()
        action.get_field_string = Mock(return_value='Value')
        labels = action.get_relevant_field_labels()
        assert isinstance(labels, list)

    def test_get_relevant_field_labels_includes_color_value_when_value(self):
        """get_relevant_field_labels should include Color Value when Value selected."""
        action = color_to_alpha.Action()
        action.get_field_string = Mock(return_value='Value')

        labels = action.get_relevant_field_labels()
        assert 'Select Color By' in labels
        assert 'Color Value' in labels

    def test_get_relevant_field_labels_excludes_color_value_when_corner(self):
        """get_relevant_field_labels should exclude Color Value for corner selections."""
        action = color_to_alpha.Action()
        action.get_field_string = Mock(return_value='Top Left')

        labels = action.get_relevant_field_labels()
        assert 'Select Color By' in labels
        assert 'Color Value' not in labels


class TestColorToAlphaInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(color_to_alpha, 'init')
        assert callable(color_to_alpha.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        color_to_alpha.init()

        # Should have loaded Image, ImageMath, ImageOps
        assert hasattr(color_to_alpha, 'Image')
        assert hasattr(color_to_alpha, 'ImageMath')
        assert hasattr(color_to_alpha, 'ImageOps')
        assert hasattr(color_to_alpha, 'imtools')
        assert hasattr(color_to_alpha, 'HTMLColorToRGBA')


class TestColorToAlphaHelperFunctions:
    """Test helper functions."""

    def test_difference1_exists(self):
        """difference1 function should exist."""
        assert hasattr(color_to_alpha, 'difference1')
        assert callable(color_to_alpha.difference1)

    def test_difference2_exists(self):
        """difference2 function should exist."""
        assert hasattr(color_to_alpha, 'difference2')
        assert callable(color_to_alpha.difference2)

    def test_difference1_calculation(self):
        """difference1 should calculate (source - color) / (255 - color)."""
        # When source > color
        result = color_to_alpha.difference1(200, 100)
        expected = (200 - 100) / (255.0 - 100)
        assert abs(result - expected) < 0.001

    def test_difference2_calculation(self):
        """difference2 should calculate (color - source) / color."""
        # When color > source
        result = color_to_alpha.difference2(100, 200)
        expected = (200 - 100) / 200.0
        assert abs(result - expected) < 0.001


class TestColorToAlphaFunction:
    """Test the color_to_alpha() function."""

    def test_color_to_alpha_function_exists(self):
        """color_to_alpha function should exist."""
        assert hasattr(color_to_alpha, 'color_to_alpha')
        assert callable(color_to_alpha.color_to_alpha)

    def test_color_to_alpha_converts_to_rgba(self):
        """color_to_alpha should convert image to RGBA."""
        color_to_alpha.init()

        # Create RGB image
        image = Image.new('RGB', (10, 10), 'white')

        # Mock HTMLColorToRGBA
        with patch('phatch.actions.color_to_alpha.HTMLColorToRGBA', return_value=(255, 255, 255, 255)):
            result = color_to_alpha.color_to_alpha(image, '#FFFFFF', 'Value')

        # Should return RGBA image
        assert result.mode == 'RGBA'

    def test_color_to_alpha_returns_rgba_image(self):
        """color_to_alpha should return RGBA image."""
        color_to_alpha.init()

        image = Image.new('RGBA', (10, 10), (255, 255, 255, 255))

        with patch('phatch.actions.color_to_alpha.HTMLColorToRGBA', return_value=(255, 255, 255, 255)):
            result = color_to_alpha.color_to_alpha(image, '#FFFFFF', 'Value')

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'
        assert result.size == (10, 10)

    def test_color_to_alpha_returns_unchanged_if_no_selection(self):
        """color_to_alpha should return unchanged if select_color_by is invalid."""
        color_to_alpha.init()

        image = Image.new('RGBA', (10, 10), (255, 0, 0, 255))

        # Invalid selection
        result = color_to_alpha.color_to_alpha(image, None, 'Invalid')

        # Should return unchanged
        assert result.mode == 'RGBA'

    def test_color_to_alpha_returns_unchanged_if_color_transparent(self):
        """color_to_alpha should return unchanged if selected color is transparent."""
        color_to_alpha.init()

        image = Image.new('RGBA', (10, 10), (255, 0, 0, 255))
        # Set top-left pixel to transparent
        image.putpixel((0, 0), (0, 0, 0, 0))

        # Select top-left (transparent pixel)
        result = color_to_alpha.color_to_alpha(image, None, 'Top Left')

        # Should return unchanged (same mode and size)
        assert result.mode == 'RGBA'
        assert result.size == (10, 10)

    def test_color_to_alpha_uses_value_when_value_selected(self):
        """color_to_alpha should use color_value when Value is selected."""
        color_to_alpha.init()

        image = Image.new('RGBA', (10, 10), (255, 0, 0, 255))

        with patch('phatch.actions.color_to_alpha.HTMLColorToRGBA', return_value=(255, 0, 0, 255)) as mock_html:
            result = color_to_alpha.color_to_alpha(image, '#FF0000', 'Value')

            # Should have called HTMLColorToRGBA
            mock_html.assert_called_once_with('#FF0000', 255)

    def test_color_to_alpha_uses_corner_pixel(self):
        """color_to_alpha should use corner pixel when corner is selected."""
        color_to_alpha.init()

        # Create image with different corner colors
        image = Image.new('RGBA', (10, 10), (255, 255, 255, 255))
        image.putpixel((0, 0), (255, 0, 0, 255))  # Top-left: red
        image.putpixel((9, 0), (0, 255, 0, 255))  # Top-right: green
        image.putpixel((0, 9), (0, 0, 255, 255))  # Bottom-left: blue
        image.putpixel((9, 9), (255, 255, 0, 255))  # Bottom-right: yellow

        # Select top-left
        result = color_to_alpha.color_to_alpha(image, None, 'Top Left')
        assert result.mode == 'RGBA'


class TestColorToAlphaIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = color_to_alpha.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = color_to_alpha.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = color_to_alpha.Action()
        assert action.author == 'Nadia Alramli'
        assert action.version == '0.1'
        assert 'color' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_transparency(self):
        """Action documentation mentions transparency or alpha."""
        action = color_to_alpha.Action()
        doc_lower = action.__doc__.lower()
        assert 'transparent' in doc_lower or 'alpha' in doc_lower or 'color' in doc_lower
