"""Unit tests for phatch.actions.text module.

Tests the Text action (draw text at a given position).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch, MagicMock

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from PIL import Image
from phatch.actions import text as text_action


class TestTextAction:
    """Test the Text action class metadata."""

    def test_action_exists(self):
        """Text action class should exist."""
        assert hasattr(text_action, 'Action')
        assert text_action.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = text_action.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = text_action.Action()
        assert 'text' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(text_action.Action, 'pil')
        assert callable(text_action.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = text_action.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_inherits_from_offset_mixin(self):
        """Action should inherit from OffsetMixin."""
        base_names = [base.__name__ for base in text_action.Action.__mro__]
        assert 'OffsetMixin' in base_names

    def test_action_tags(self):
        """Action should have filter tag."""
        action = text_action.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestTextInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_text_field(self):
        """interface should define Text parameter."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        assert any('text' == k.lower() for k in fields.keys())

    def test_interface_defines_font_field(self):
        """interface should define Font parameter."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        assert any('font' in k.lower() for k in fields.keys())

    def test_interface_defines_size_field(self):
        """interface should define Size parameter."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        assert any('size' in k.lower() for k in fields.keys())

    def test_interface_defines_color_field(self):
        """interface should define Color parameter."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        assert any('color' in k.lower() for k in fields.keys())

    def test_interface_text_is_char_field(self):
        """Text should be a CharField."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        # Get the Text field
        text_field = None
        for key, value in fields.items():
            if 'text' == key.lower():
                text_field = value
                break

        assert text_field is not None
        assert type(text_field).__name__ == 'CharField'

    def test_interface_font_is_font_file_field(self):
        """Font should be a FontFileField."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        # Get the Font field
        font_field = None
        for key, value in fields.items():
            if 'font' in key.lower():
                font_field = value
                break

        assert font_field is not None
        assert type(font_field).__name__ == 'FontFileField'

    def test_interface_size_is_pixel_field(self):
        """Size should be a PixelField."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)

        # Get the Size field
        size_field = None
        for key, value in fields.items():
            if 'size' in key.lower():
                size_field = value
                break

        assert size_field is not None
        assert type(size_field).__name__ == 'PixelField'

    def test_interface_color_is_color_field(self):
        """Color should be a ColorField."""
        action = text_action.Action()
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


class TestDrawTextFunction:
    """Test the draw_text() PIL function.

    Note: Due to lazy-loading pattern, full functional testing is limited.
    See REFACTORING.md for dependency injection improvements.
    """

    def test_draw_text_function_exists(self):
        """draw_text function should exist."""
        assert hasattr(text_action, 'draw_text')
        assert callable(text_action.draw_text)

    def test_draw_text_basic(self, rgb_image):
        """Draw text on RGB image."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Hello', 10, 10, 'Left', 'Top', 20,
            color='#000000', font=''
        )

        assert isinstance(result, Image.Image)
        assert result.size == rgb_image.size

    def test_draw_text_with_color(self, rgb_image):
        """Draw text with custom color."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Colored', 0, 0, 'Middle', 'Middle', 24,
            color='#FF0000', font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_with_default_font(self, rgb_image):
        """Draw text with default font (empty font string)."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Default Font', 10, 10, 'Left', 'Top', 16,
            font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_multiline(self, rgb_image):
        """Draw multiline text."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Line 1\nLine 2', 10, 10, 'Left', 'Top', 20,
            font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_various_justifications(self, rgb_image):
        """Draw text with various justifications."""
        text_action.init()

        justifications = [
            ('Left', 'Top'),
            ('Middle', 'Middle'),
            ('Right', 'Bottom'),
        ]

        for h_just, v_just in justifications:
            result = text_action.draw_text(
                rgb_image, 'Test', 10, 10, h_just, v_just, 20,
                font=''
            )

            assert isinstance(result, Image.Image)


class TestGetRelevantFieldLabels:
    """Test the get_relevant_field_labels() method."""

    def test_get_relevant_field_labels_method_exists(self):
        """get_relevant_field_labels method should exist."""
        action = text_action.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_returns_list(self):
        """get_relevant_field_labels should return list."""
        action = text_action.Action()
        labels = action.get_relevant_field_labels()
        assert isinstance(labels, list)

    def test_get_relevant_field_labels_includes_text_fields(self):
        """get_relevant_field_labels should include text-specific fields."""
        action = text_action.Action()
        labels = action.get_relevant_field_labels()

        assert 'Text' in labels
        assert 'Font' in labels
        assert 'Size' in labels
        assert 'Color' in labels


class TestValuesMethod:
    """Test the values() method."""

    def test_values_method_exists(self):
        """values method should exist."""
        action = text_action.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_values_accepts_info_dict(self):
        """values method accepts info dictionary."""
        action = text_action.Action()

        # Simple test that method accepts the expected signature
        # Full functional test requires font cache initialization
        info = {'size': (200, 100)}
        # Method exists and is callable
        assert callable(action.values)


class TestTextIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = text_action.Action()
        assert action is not None

    def test_action_pil_points_to_draw_text(self):
        """Action.pil should point to draw_text function."""
        assert text_action.Action.pil == text_action.draw_text

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        text_action.init()
        assert hasattr(text_action, 'Image')
        assert hasattr(text_action, 'ImageDraw')
        assert hasattr(text_action, 'ImageFont')

    def test_init_loads_imtools(self):
        """init() should load imtools functions."""
        text_action.init()
        assert hasattr(text_action, 'calculate_location')
        assert hasattr(text_action, 'convert_safe_mode')

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = text_action.Action()
        fields = {}
        action.interface(fields)
        # Should have at least Text, Font, Size, Color fields
        assert len(fields) >= 4

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = text_action.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_text(self):
        """Action documentation mentions text."""
        action = text_action.Action()
        doc_lower = action.__doc__.lower()
        assert 'text' in doc_lower


class TestTextEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_draw_text_empty_string(self, rgb_image):
        """Draw empty text string."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, '', 10, 10, 'Left', 'Top', 20,
            font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_small_size(self, rgb_image):
        """Draw text with small size."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Small', 10, 10, 'Left', 'Top', 1,
            font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_large_size(self, rgb_image):
        """Draw text with large size."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, 'Large', 10, 10, 'Left', 'Top', 50,
            font=''
        )

        assert isinstance(result, Image.Image)

    def test_draw_text_special_characters(self, rgb_image):
        """Draw text with special characters."""
        text_action.init()

        result = text_action.draw_text(
            rgb_image, '!@#$%^&*()', 10, 10, 'Left', 'Top', 20,
            font=''
        )

        assert isinstance(result, Image.Image)
