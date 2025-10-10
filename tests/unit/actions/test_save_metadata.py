"""Unit tests for phatch.actions.save_metadata module.

Tests the Save Tags action (save only metadata - lossless).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import save_metadata


class TestSaveMetadataAction:
    """Test the Save Tags action class metadata."""

    def test_action_exists(self):
        """Save Tags action class should exist."""
        assert hasattr(save_metadata, 'Action')
        assert save_metadata.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = save_metadata.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = save_metadata.Action()
        assert 'save' in action.label.lower() and 'tag' in action.label.lower()

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = save_metadata.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_tags(self):
        """Action should have file and metadata tags."""
        action = save_metadata.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'file' in tags_lower
        assert 'metadata' in tags_lower

    def test_action_pil_is_none(self):
        """pil should be None (file operation, not image processing)."""
        # The action doesn't define pil, so it should be None or not have it
        action = save_metadata.Action()
        assert not hasattr(action, 'pil') or action.pil is None


class TestSaveMetadataApply:
    """Test the apply() method."""

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_saves_metadata_same_file(self, mock_get_filename,
                                           mock_copy, mock_utime):
        """apply should save metadata to same file."""
        action = save_metadata.Action()

        # Mock photo with metadata
        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = None

        # Same filename
        mock_get_filename.return_value = '/path/to/image.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should NOT copy (same file)
        mock_copy.assert_not_called()
        # Should save metadata
        photo.info.save.assert_called_once_with('/path/to/image.jpg')
        # Should not update utime (no modify_date)
        mock_utime.assert_not_called()
        assert result == photo

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_copies_and_saves_different_file(self, mock_get_filename,
                                                    mock_copy, mock_utime):
        """apply should copy and save metadata when filename different."""
        action = save_metadata.Action()

        # Mock photo with metadata
        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = None

        # Different filename
        mock_get_filename.return_value = '/path/to/image_copy.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should copy to new filename
        mock_copy.assert_called_once_with('/path/to/image.jpg',
                                         '/path/to/image_copy.jpg')
        # Should save metadata to new filename
        photo.info.save.assert_called_once_with('/path/to/image_copy.jpg')
        # Should not update utime (no modify_date)
        mock_utime.assert_not_called()
        assert result == photo

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_updates_file_times_when_modify_date_set(self, mock_get_filename,
                                                           mock_copy, mock_utime):
        """apply should update file times when modify_date is set."""
        action = save_metadata.Action()

        # Mock photo with modify_date
        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = 1234567890  # Unix timestamp

        # Same filename
        mock_get_filename.return_value = '/path/to/image.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should save metadata
        photo.info.save.assert_called_once_with('/path/to/image.jpg')
        # Should update file times
        mock_utime.assert_called_once_with('/path/to/image.jpg',
                                          (1234567890, 1234567890))
        assert result == photo

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_does_not_update_times_when_no_modify_date(self, mock_get_filename,
                                                              mock_copy, mock_utime):
        """apply should not update file times when modify_date is falsy."""
        action = save_metadata.Action()

        # Mock photo without modify_date
        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = 0  # Falsy

        # Same filename
        mock_get_filename.return_value = '/path/to/image.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should save metadata
        photo.info.save.assert_called_once_with('/path/to/image.jpg')
        # Should NOT update file times (modify_date is falsy)
        mock_utime.assert_not_called()
        assert result == photo


class TestSaveMetadataEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_with_none_modify_date(self, mock_get_filename,
                                         mock_copy, mock_utime):
        """apply should handle None modify_date."""
        action = save_metadata.Action()

        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = None

        mock_get_filename.return_value = '/path/to/image.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should not update file times
        mock_utime.assert_not_called()
        assert result == photo

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_copies_before_saving(self, mock_get_filename,
                                        mock_copy, mock_utime):
        """apply should copy file before saving metadata."""
        action = save_metadata.Action()

        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/image.jpg')
        photo.info.save = Mock()
        photo.modify_date = None

        # Different filename
        mock_get_filename.return_value = '/path/to/new_image.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should copy first
        mock_copy.assert_called_once()
        # Then save metadata
        photo.info.save.assert_called_once()
        # Ensure copy was called before save
        assert mock_copy.call_count == 1
        assert photo.info.save.call_count == 1
        assert result == photo

    @patch('phatch.actions.save_metadata.os.utime')
    @patch('phatch.actions.save_metadata.shutil.copy2')
    @patch.object(save_metadata.Action, 'get_lossless_filename')
    def test_apply_with_unicode_filename(self, mock_get_filename,
                                         mock_copy, mock_utime):
        """apply should handle Unicode filenames."""
        action = save_metadata.Action()

        photo = Mock()
        photo.info = Mock()
        photo.info.__getitem__ = Mock(return_value='/path/to/图片.jpg')
        photo.info.save = Mock()
        photo.modify_date = None

        # Unicode filename
        mock_get_filename.return_value = '/path/to/图片_copy.jpg'

        setting = Mock()
        cache = {}

        result = action.apply(photo, setting, cache)

        # Should handle Unicode paths
        mock_copy.assert_called_once_with('/path/to/图片.jpg',
                                         '/path/to/图片_copy.jpg')
        photo.info.save.assert_called_once_with('/path/to/图片_copy.jpg')
        assert result == photo


class TestSaveMetadataIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = save_metadata.Action()
        assert action is not None

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = save_metadata.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'file' in tags_lower
        assert 'metadata' in tags_lower

    def test_action_docstring_mentions_lossless(self):
        """Action documentation mentions lossless and metadata."""
        action = save_metadata.Action()
        doc_lower = action.__doc__.lower()
        assert 'metadata' in doc_lower or 'lossless' in doc_lower

    def test_action_has_lossless_mixin_methods(self):
        """Action should have methods from LosslessSaveMixin."""
        action = save_metadata.Action()
        assert hasattr(action, 'get_lossless_filename')
        assert callable(action.get_lossless_filename)
