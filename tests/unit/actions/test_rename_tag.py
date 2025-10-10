"""Unit tests for phatch.actions.rename_tag module.

Tests the Rename Tag action (rename Exif/Iptc tag).

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

from phatch.actions import rename_tag


class TestRenameTagAction:
    """Test the Rename Tag action class metadata."""

    def test_action_exists(self):
        """Rename Tag action class should exist."""
        assert hasattr(rename_tag, 'Action')
        assert rename_tag.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = rename_tag.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = rename_tag.Action()
        assert 'rename' in action.label.lower() and 'tag' in action.label.lower()

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = rename_tag.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = rename_tag.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have metadata tag."""
        action = rename_tag.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'metadata' in tags_lower

    def test_action_pil_is_none(self):
        """pil should be None (metadata operation, not image processing)."""
        assert rename_tag.Action.pil is None


class TestRenameTagInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_from_field(self):
        """interface should define From (Exif, Iptc) parameter."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)

        assert any('from' in k.lower() and ('exif' in k.lower() or 'iptc' in k.lower())
                   for k in fields.keys())

    def test_interface_defines_to_field(self):
        """interface should define To (Exif, Iptc) parameter."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)

        assert any('to' in k.lower() and ('exif' in k.lower() or 'iptc' in k.lower())
                   for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Rename Tag should have two parameters."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_from_is_exif_iptc_field(self):
        """From should be an ExifItpcField."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)

        # Get the From field
        from_field = None
        for key, value in fields.items():
            if 'from' in key.lower() and ('exif' in key.lower() or 'iptc' in key.lower()):
                from_field = value
                break

        assert from_field is not None
        assert type(from_field).__name__ == 'ExifItpcField'

    def test_interface_to_is_exif_iptc_field(self):
        """To should be an ExifItpcField."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)

        # Get the To field
        to_field = None
        for key, value in fields.items():
            if 'to' in key.lower() and ('exif' in key.lower() or 'iptc' in key.lower()):
                to_field = value
                break

        assert to_field is not None
        assert type(to_field).__name__ == 'ExifItpcField'


class TestRenameTagApply:
    """Test the apply() method with different tag renames."""

    def test_apply_rename_exif_tag(self):
        """apply should rename specified Exif tag."""
        action = rename_tag.Action()

        # Mock photo with metadata
        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Model': 'EOS',
            'Iptc_Caption': 'Test'
        }

        # Mock get_field to return old and new tag names
        action.get_field = Mock(side_effect=['Exif_Image_Make', 'Exif_Image_Manufacturer'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have renamed the tag
        assert 'Exif_Image_Make' not in photo.info
        assert 'Exif_Image_Manufacturer' in photo.info
        assert photo.info['Exif_Image_Manufacturer'] == 'Canon'
        # Should keep other tags
        assert 'Exif_Image_Model' in photo.info
        assert 'Iptc_Caption' in photo.info
        assert result == photo

    def test_apply_rename_iptc_tag(self):
        """apply should rename specified Iptc tag."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Iptc_Caption': 'Test Caption',
        }

        action.get_field = Mock(side_effect=['Iptc_Caption', 'Iptc_Description'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have renamed the tag
        assert 'Iptc_Caption' not in photo.info
        assert 'Iptc_Description' in photo.info
        assert photo.info['Iptc_Description'] == 'Test Caption'
        assert result == photo

    def test_apply_does_not_rename_if_same_name(self):
        """apply should not modify tag if old and new names are the same."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Model': 'EOS',
        }

        # Same tag name for from and to
        action.get_field = Mock(side_effect=['Exif_Image_Make', 'Exif_Image_Make'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not have changed anything
        assert 'Exif_Image_Make' in photo.info
        assert photo.info['Exif_Image_Make'] == 'Canon'
        assert 'Exif_Image_Model' in photo.info
        assert result == photo

    def test_apply_does_not_rename_if_old_tag_missing(self):
        """apply should do nothing if old tag doesn't exist."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Try to rename a non-existent tag
        action.get_field = Mock(side_effect=['Exif_Image_NonExistent', 'Exif_Image_Something'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not have added new tag
        assert 'Exif_Image_NonExistent' not in photo.info
        assert 'Exif_Image_Something' not in photo.info
        # Should keep existing tags
        assert 'Exif_Image_Make' in photo.info
        assert result == photo

    def test_apply_strips_whitespace_from_names(self):
        """apply should strip whitespace from tag names."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Tag names with whitespace
        action.get_field = Mock(side_effect=['  Exif_Image_Make  ', '  Exif_Image_Manufacturer  '])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have renamed the tag (after stripping)
        assert 'Exif_Image_Make' not in photo.info
        assert 'Exif_Image_Manufacturer' in photo.info
        assert photo.info['Exif_Image_Manufacturer'] == 'Canon'
        assert result == photo

    def test_apply_does_not_rename_if_old_name_empty(self):
        """apply should do nothing if old tag name is empty."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Empty old tag name
        action.get_field = Mock(side_effect=['', 'Exif_Image_Something'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not have changed anything
        assert 'Exif_Image_Make' in photo.info
        assert 'Exif_Image_Something' not in photo.info
        assert result == photo

    def test_apply_does_not_rename_if_new_name_empty(self):
        """apply should do nothing if new tag name is empty."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Empty new tag name
        action.get_field = Mock(side_effect=['Exif_Image_Make', ''])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not have changed anything
        assert 'Exif_Image_Make' in photo.info
        assert result == photo

    def test_apply_overwrites_if_new_name_exists(self):
        """apply should overwrite if new tag name already exists."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Manufacturer': 'Nikon',  # Already exists
        }

        action.get_field = Mock(side_effect=['Exif_Image_Make', 'Exif_Image_Manufacturer'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have overwritten the existing tag
        assert 'Exif_Image_Make' not in photo.info
        assert 'Exif_Image_Manufacturer' in photo.info
        assert photo.info['Exif_Image_Manufacturer'] == 'Canon'  # Overwritten
        assert result == photo


class TestRenameTagEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_apply_with_empty_info(self):
        """apply should handle empty info dictionary."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {}

        action.get_field = Mock(side_effect=['Exif_Image_Make', 'Exif_Image_Manufacturer'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle empty dict without error
        assert photo.info == {}
        assert result == photo

    def test_apply_preserves_value_type(self):
        """apply should preserve the type of tag value."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Copyright': '© 2025 Phatch',
        }

        action.get_field = Mock(side_effect=['Exif_Image_Copyright', 'Exif_Image_CopyrightNotice'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should preserve Unicode string
        assert photo.info['Exif_Image_CopyrightNotice'] == '© 2025 Phatch'
        assert isinstance(photo.info['Exif_Image_CopyrightNotice'], str)
        assert result == photo

    def test_apply_with_none_value(self):
        """apply should handle None values."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Copyright': None,
        }

        action.get_field = Mock(side_effect=['Exif_Image_Copyright', 'Exif_Image_CopyrightNotice'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should copy None value
        assert 'Exif_Image_Copyright' not in photo.info
        assert 'Exif_Image_CopyrightNotice' in photo.info
        assert photo.info['Exif_Image_CopyrightNotice'] is None
        assert result == photo

    def test_apply_whitespace_only_names_treated_as_empty(self):
        """apply should treat whitespace-only names as empty."""
        action = rename_tag.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Whitespace-only old name
        action.get_field = Mock(side_effect=['   ', 'Exif_Image_Manufacturer'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not have changed anything
        assert 'Exif_Image_Make' in photo.info
        assert 'Exif_Image_Manufacturer' not in photo.info
        assert result == photo


class TestRenameTagIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = rename_tag.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = rename_tag.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = rename_tag.Action()
        assert action.author == 'Juho Vepsäläinen'
        assert action.version == '0.1'
        assert 'metadata' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_rename(self):
        """Action documentation mentions rename and tag."""
        action = rename_tag.Action()
        doc_lower = action.__doc__.lower()
        assert 'rename' in doc_lower and 'tag' in doc_lower
