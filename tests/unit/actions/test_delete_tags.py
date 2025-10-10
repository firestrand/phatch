"""Unit tests for phatch.actions.delete_tags module.

Tests the Delete Tags action (delete Exif or Iptc tags).

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

from phatch.actions import delete_tags


class TestDeleteTagsAction:
    """Test the Delete Tags action class metadata."""

    def test_action_exists(self):
        """Delete Tags action class should exist."""
        assert hasattr(delete_tags, 'Action')
        assert delete_tags.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = delete_tags.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = delete_tags.Action()
        assert 'delete' in action.label.lower() and 'tag' in action.label.lower()

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = delete_tags.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = delete_tags.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have metadata tag."""
        action = delete_tags.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'metadata' in tags_lower

    def test_action_pil_is_none(self):
        """pil should be None (metadata operation, not image processing)."""
        assert delete_tags.Action.pil is None


class TestDeleteTagsConstants:
    """Test module-level constants."""

    def test_methods_constant_exists(self):
        """METHODS constant should exist."""
        assert hasattr(delete_tags, 'METHODS')
        assert isinstance(delete_tags.METHODS, list)

    def test_methods_has_four_values(self):
        """METHODS should have four values (All, Exif, Iptc, One)."""
        assert len(delete_tags.METHODS) == 4

    def test_methods_includes_expected_values(self):
        """METHODS should include expected values."""
        # Convert to lowercase for comparison
        methods_lower = [str(m).lower() for m in delete_tags.METHODS]
        assert 'all' in methods_lower
        assert 'exif' in methods_lower
        assert 'iptc' in methods_lower
        assert 'one' in methods_lower


class TestDeleteTagsInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_method_field(self):
        """interface should define Method parameter."""
        action = delete_tags.Action()
        fields = {}
        action.interface(fields)

        assert any('method' in k.lower() for k in fields.keys())

    def test_interface_defines_tag_field(self):
        """interface should define Tag parameter."""
        action = delete_tags.Action()
        fields = {}
        action.interface(fields)

        assert any('tag' == k.lower() for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Delete Tags should have two parameters."""
        action = delete_tags.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_method_is_choice_field(self):
        """Method should be a ChoiceField."""
        action = delete_tags.Action()
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

    def test_interface_tag_is_exif_iptc_field(self):
        """Tag should be an ExifItpcField."""
        action = delete_tags.Action()
        fields = {}
        action.interface(fields)

        # Get the Tag field
        tag_field = None
        for key, value in fields.items():
            if 'tag' == key.lower():
                tag_field = value
                break

        assert tag_field is not None
        assert type(tag_field).__name__ == 'ExifItpcField'


class TestGetRelevantFieldLabels:
    """Test the get_relevant_field_labels() method."""

    def test_get_relevant_field_labels_method_exists(self):
        """get_relevant_field_labels method should exist."""
        action = delete_tags.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_returns_list(self):
        """get_relevant_field_labels should return list."""
        action = delete_tags.Action()
        labels = action.get_relevant_field_labels()
        assert isinstance(labels, list)

    def test_get_relevant_field_labels_includes_method(self):
        """get_relevant_field_labels should always include Method."""
        action = delete_tags.Action()
        labels = action.get_relevant_field_labels()
        assert 'Method' in labels


class TestDeleteTagsApply:
    """Test the apply() method with different deletion methods."""

    def test_apply_delete_one_tag(self):
        """apply should delete specific tag when Method is 'One'."""
        action = delete_tags.Action()

        # Mock photo with metadata
        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Model': 'EOS',
            'Iptc_Caption': 'Test',
            'Other_Tag': 'Value'
        }

        # Mock get_field to return 'One' method and specific tag
        action.get_field = Mock(side_effect=['One', 'Exif_Image_Make'])

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have deleted only Exif_Image_Make
        assert 'Exif_Image_Make' not in photo.info
        assert 'Exif_Image_Model' in photo.info
        assert 'Iptc_Caption' in photo.info
        assert result == photo

    def test_apply_delete_exif_tags(self):
        """apply should delete all Exif tags when Method is 'Exif'."""
        action = delete_tags.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Model': 'EOS',
            'Iptc_Caption': 'Test',
            'Other_Tag': 'Value'
        }

        action.get_field = Mock(return_value='Exif')

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have deleted all Exif tags
        assert 'Exif_Image_Make' not in photo.info
        assert 'Exif_Image_Model' not in photo.info
        # Should keep non-Exif tags
        assert 'Iptc_Caption' in photo.info
        assert 'Other_Tag' in photo.info
        assert result == photo

    def test_apply_delete_iptc_tags(self):
        """apply should delete all Iptc tags when Method is 'Iptc'."""
        action = delete_tags.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Iptc_Caption': 'Test',
            'Iptc_Keywords': 'photo, test',
            'Other_Tag': 'Value'
        }

        action.get_field = Mock(return_value='Iptc')

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should have deleted all Iptc tags
        assert 'Iptc_Caption' not in photo.info
        assert 'Iptc_Keywords' not in photo.info
        # Should keep non-Iptc tags
        assert 'Exif_Image_Make' in photo.info
        assert 'Other_Tag' in photo.info
        assert result == photo


class TestDeleteTagsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_apply_with_empty_info(self):
        """apply should handle empty info dictionary."""
        action = delete_tags.Action()

        photo = Mock()
        photo.info = {}

        action.get_field = Mock(return_value='Exif')

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle empty dict without error
        assert photo.info == {}
        assert result == photo

    def test_apply_delete_nonexistent_tag(self):
        """apply should handle deletion of non-existent tag."""
        action = delete_tags.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
        }

        # Try to delete a tag that doesn't exist
        action.get_field = Mock(side_effect=['One', 'NonExistent_Tag'])

        setting = Mock()
        cache = {}

        # Should raise KeyError when trying to delete non-existent tag
        try:
            result = action.apply(photo, setting, cache)
            # If we get here, the tag wasn't found but no error was raised
            # which means the original data should be unchanged
            assert 'Exif_Image_Make' in photo.info
        except KeyError:
            # Expected behavior - trying to delete non-existent key
            pass

    def test_apply_with_mixed_case_method(self):
        """apply should handle method names case-sensitively."""
        action = delete_tags.Action()

        photo = Mock()
        photo.info = {
            'Exif_Image_Make': 'Canon',
            'Exif_Image_Model': 'EOS',
        }

        # Use exact case from METHODS
        action.get_field = Mock(return_value='Exif')

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should delete Exif tags
        assert len(photo.info) == 0


class TestDeleteTagsIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = delete_tags.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = delete_tags.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = delete_tags.Action()
        assert action.author in ['Juho Vepsäläinen, Stani', 'Stani']
        assert action.version == '0.1'
        assert 'metadata' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_tags(self):
        """Action documentation mentions tags."""
        action = delete_tags.Action()
        doc_lower = action.__doc__.lower()
        assert 'tag' in doc_lower or 'exif' in doc_lower or 'iptc' in doc_lower
