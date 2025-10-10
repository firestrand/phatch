"""Unit tests for phatch.actions.write_tag module.

Tests the Write Tag action (write new value to Exif/Iptc tag).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import write_tag


class TestWriteTagAction:
    """Test the Write Tag action class metadata."""

    def test_action_exists(self):
        """Write Tag action class should exist."""
        assert hasattr(write_tag, 'Action')
        assert write_tag.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = write_tag.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = write_tag.Action()
        assert 'write' in action.label.lower() and 'tag' in action.label.lower()

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = write_tag.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = write_tag.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have metadata tag."""
        action = write_tag.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'metadata' in tags_lower

    def test_action_pil_is_none(self):
        """pil should be None (metadata operation, not image processing)."""
        assert write_tag.Action.pil is None


class TestWriteTagInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_tag_field(self):
        """interface should define Tag (Exif, Iptc) parameter."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        assert any('tag' in k.lower() and ('exif' in k.lower() or 'iptc' in k.lower())
                   for k in fields.keys())

    def test_interface_defines_value_field(self):
        """interface should define Value parameter."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        assert any('value' == k.lower() for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Write Tag should have two parameters."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_tag_is_exif_iptc_field(self):
        """Tag should be an ExifItpcField."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        # Get the Tag field
        tag_field = None
        for key, value in fields.items():
            if 'tag' in key.lower() and ('exif' in key.lower() or 'iptc' in key.lower()):
                tag_field = value
                break

        assert tag_field is not None
        assert type(tag_field).__name__ == 'ExifItpcField'

    def test_interface_value_is_char_field(self):
        """Value should be a CharField."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        # Get the Value field
        value_field = None
        for key, value in fields.items():
            if 'value' == key.lower():
                value_field = value
                break

        assert value_field is not None
        assert type(value_field).__name__ == 'CharField'

    def test_interface_creates_fields_with_defaults(self):
        """Interface should create fields with default values."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)

        # Both fields should be created (defaults are implementation details)
        assert len(fields) == 2
        # Tag field should be ExifItpcField
        tag_field = None
        for key, value in fields.items():
            if 'tag' in key.lower() and ('exif' in key.lower() or 'iptc' in key.lower()):
                tag_field = value
                break
        assert tag_field is not None
        assert type(tag_field).__name__ == 'ExifItpcField'

        # Value field should be CharField
        value_field = None
        for key, value in fields.items():
            if 'value' == key.lower():
                value_field = value
                break
        assert value_field is not None
        assert type(value_field).__name__ == 'CharField'


class TestWriteTagApply:
    """Test the apply() method with different tag writes."""

    def test_apply_write_exif_tag(self):
        """apply should write value to specified Exif tag."""
        action = write_tag.Action()

        # Mock photo with metadata
        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Iptc_Caption': 'Test'
        }

        # Mock get_field to return tag name and value
        action.get_field = Mock(side_effect=['Exif_Image_Copyright', 'My Copyright'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have written the tag
        assert 'Exif_Image_Copyright' in photo.info
        assert photo.info['Exif_Image_Copyright'] == 'My Copyright'
        # Should keep other tags
        assert 'Exif_Image_Make' in photo.info
        assert 'Iptc_Caption' in photo.info
        assert result == photo

    def test_apply_write_iptc_tag(self):
        """apply should write value to specified Iptc tag."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        action.get_field = Mock(side_effect=['Iptc_Caption', 'My Caption'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have written the tag
        assert 'Iptc_Caption' in photo.info
        assert photo.info['Iptc_Caption'] == 'My Caption'
        assert result == photo

    def test_apply_overwrite_existing_tag(self):
        """apply should overwrite existing tag value."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Copyright': 'Old Copyright',
            'Exif_Image_Make': 'Canon',
        }

        action.get_field = Mock(side_effect=['Exif_Image_Copyright', 'New Copyright'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have overwritten the tag
        assert photo.info['Exif_Image_Copyright'] == 'New Copyright'
        assert result == photo

    def test_apply_write_empty_string_becomes_none(self):
        """apply should convert empty string to None."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Empty string value
        action.get_field = Mock(side_effect=['Exif_Image_Copyright', ''])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have written None (not empty string)
        assert 'Exif_Image_Copyright' in photo.info
        assert photo.info['Exif_Image_Copyright'] is None
        assert result == photo

    def test_apply_write_whitespace_string_becomes_none(self):
        """apply should strip whitespace and convert to None if empty."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        # Whitespace-only value
        action.get_field = Mock(side_effect=['Exif_Image_Copyright', '   '])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have written None (after stripping)
        assert 'Exif_Image_Copyright' in photo.info
        assert photo.info['Exif_Image_Copyright'] is None
        assert result == photo

    def test_apply_strips_whitespace_from_value(self):
        """apply should strip leading/trailing whitespace from value."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        # Value with whitespace
        action.get_field = Mock(side_effect=['Exif_Image_Copyright', '  My Copyright  '])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have stripped whitespace
        assert photo.info['Exif_Image_Copyright'] == 'My Copyright'
        assert result == photo


class TestWriteTagEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_apply_with_empty_info(self):
        """apply should handle empty info dictionary."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        action.get_field = Mock(side_effect=['Exif_Image_Copyright', 'My Copyright'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should add the tag
        assert 'Exif_Image_Copyright' in photo.info
        assert photo.info['Exif_Image_Copyright'] == 'My Copyright'
        assert result == photo

    def test_apply_with_unicode_value(self):
        """apply should handle Unicode values."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        # Unicode value with special characters
        action.get_field = Mock(side_effect=['Exif_Image_Copyright', '© 2025 Phatch'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle Unicode
        assert photo.info['Exif_Image_Copyright'] == '© 2025 Phatch'
        assert result == photo

    def test_apply_with_long_value(self):
        """apply should handle long string values."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        # Long value
        long_value = 'A' * 1000
        action.get_field = Mock(side_effect=['Iptc_Caption', long_value])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle long values
        assert photo.info['Iptc_Caption'] == long_value
        assert result == photo

    def test_apply_with_numeric_string_value(self):
        """apply should handle numeric string values."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        action.get_field = Mock(side_effect=['Exif_Image_Copyright', '12345'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should keep as string
        assert photo.info['Exif_Image_Copyright'] == '12345'
        assert isinstance(photo.info['Exif_Image_Copyright'], str)
        assert result == photo

    def test_apply_with_multiline_value(self):
        """apply should handle multiline string values."""
        action = write_tag.Action()

        photo = Mock()
        photo.info = {}

        multiline_value = 'Line 1\nLine 2\nLine 3'
        action.get_field = Mock(side_effect=['Iptc_Caption', multiline_value])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle multiline
        assert photo.info['Iptc_Caption'] == multiline_value
        assert result == photo


class TestWriteTagIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = write_tag.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = write_tag.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = write_tag.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'metadata' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_tags(self):
        """Action documentation mentions tags."""
        action = write_tag.Action()
        doc_lower = action.__doc__.lower()
        assert 'tag' in doc_lower or 'value' in doc_lower or 'write' in doc_lower
