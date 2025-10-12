"""Unit tests for phatch.actions.copy module.

Tests the Copy action (copy original image to specified location).

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

from phatch.actions import copy as copy_action


class TestCopyAction:
    """Test the Copy action class metadata."""

    def test_action_exists(self):
        """Copy action class should exist."""
        assert hasattr(copy_action, 'Action')
        assert copy_action.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = copy_action.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = copy_action.Action()
        assert 'copy' in action.label.lower()

    def test_action_has_apply_method(self):
        """Action should have apply method (file operations use apply, not pil)."""
        action = copy_action.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = copy_action.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_valid_last(self):
        """Copy action should be valid as last action."""
        action = copy_action.Action()
        assert action.valid_last is True

    def test_action_tags(self):
        """Action should have file tag."""
        action = copy_action.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'file' in tags_lower


class TestCopyInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_filename_field(self):
        """interface should define File Name parameter."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)

        assert any('file' in k.lower() and 'name' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_folder_field(self):
        """interface should define In (folder) parameter."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)

        assert any('in' == k.lower() or 'folder' in k.lower()
                   for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Copy should have two parameters (filename and folder)."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_filename_is_field(self):
        """File Name should be a FileNameField."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)

        # Get the File Name field
        filename_field = None
        for key, value in fields.items():
            if 'file' in key.lower() and 'name' in key.lower():
                filename_field = value
                break

        assert filename_field is not None
        assert type(filename_field).__name__ == 'FileNameField'

    def test_interface_folder_is_field(self):
        """In should be a FolderField."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)

        # Get the In field
        folder_field = None
        for key, value in fields.items():
            if 'in' == key.lower():
                folder_field = value
                break

        assert folder_field is not None
        assert type(folder_field).__name__ == 'FolderField'


class TestIsDoneInfo:
    """Test the is_done_info() method."""

    def test_is_done_info_method_exists(self):
        """is_done_info method should exist."""
        action = copy_action.Action()
        assert hasattr(action, 'is_done_info')
        assert callable(action.is_done_info)

    @patch.object(copy_action.Action, 'get_field')
    def test_is_done_info_returns_tuple(self, mock_get_field):
        """is_done_info should return (folder, filename, type) tuple."""
        action = copy_action.Action()
        mock_get_field.side_effect = ['/test/folder', 'testfile']

        info = {'type': 'jpg'}
        result = action.is_done_info(info)

        assert isinstance(result, tuple)
        assert len(result) == 3

    @patch.object(copy_action.Action, 'get_field')
    def test_is_done_info_constructs_path(self, mock_get_field):
        """is_done_info should construct full path from folder and filename."""
        action = copy_action.Action()
        mock_get_field.side_effect = ['/test/folder', 'myfile']

        info = {'type': 'png'}
        folder, full_path, typ = action.is_done_info(info)

        assert folder == '/test/folder'
        assert 'myfile.png' in full_path
        assert typ == 'png'


class TestIsOverwriteForced:
    """Test the is_overwrite_existing_images_forced() method."""

    def test_is_overwrite_forced_method_exists(self):
        """is_overwrite_existing_images_forced method should exist."""
        action = copy_action.Action()
        assert hasattr(action, 'is_overwrite_existing_images_forced')
        assert callable(action.is_overwrite_existing_images_forced)

    @patch.object(copy_action.Action, 'get_field_string')
    def test_is_overwrite_forced_same_location(self, mock_get_field_string):
        """Should force overwrite when copying to same location."""
        action = copy_action.Action()
        # Mock that In field == FOLDER and File Name == FILENAME
        mock_get_field_string.side_effect = [action.FOLDER, action.FILENAME]

        result = action.is_overwrite_existing_images_forced()

        assert result is True

    @patch.object(copy_action.Action, 'get_field_string')
    def test_is_overwrite_not_forced_different_folder(self,
                                                       mock_get_field_string):
        """Should not force overwrite when copying to different folder."""
        action = copy_action.Action()
        # Mock that In field != FOLDER
        mock_get_field_string.side_effect = ['/different/folder',
                                            action.FILENAME]

        result = action.is_overwrite_existing_images_forced()

        assert result is False

    @patch.object(copy_action.Action, 'get_field_string')
    def test_is_overwrite_not_forced_different_filename(self,
                                                        mock_get_field_string):
        """Should not force overwrite when using different filename."""
        action = copy_action.Action()
        # Mock that File Name != FILENAME
        mock_get_field_string.side_effect = [action.FOLDER, 'newname']

        result = action.is_overwrite_existing_images_forced()

        assert result is False


class TestCopyApply:
    """Test the apply() method."""

    @patch('phatch.actions.copy.shutil.copy2')
    @patch('phatch.actions.copy.os.path.exists')
    @patch.object(copy_action.Action, 'ensure_path_or_desktop')
    @patch.object(copy_action.Action, 'is_done_info')
    def test_apply_copies_file_when_not_exists(self, mock_is_done_info,
                                               mock_ensure_path,
                                               mock_exists, mock_copy2):
        """apply should copy file when destination doesn't exist."""
        action = copy_action.Action()

        # Setup mocks
        mock_is_done_info.return_value = (
            '/dest/folder',
            '/dest/folder/file.jpg',
            'jpg'
        )
        mock_exists.return_value = False  # File doesn't exist
        mock_ensure_path.return_value = '/dest/folder/file.jpg'

        # Create mock photo and setting
        photo = Mock()
        photo.info = {'path': '/source/image.jpg', 'type': 'jpg'}
        setting = Mock(return_value=False)  # overwrite_existing_images=False

        result = action.apply(photo, setting, {})

        # Should call copy2
        mock_copy2.assert_called_once_with('/source/image.jpg',
                                          '/dest/folder/file.jpg')
        assert result == photo

    @patch('phatch.actions.copy.shutil.copy2')
    @patch('phatch.actions.copy.os.path.exists')
    @patch.object(copy_action.Action, 'is_done_info')
    def test_apply_skips_when_exists_no_overwrite(self, mock_is_done_info,
                                                  mock_exists, mock_copy2):
        """apply should skip copy when file exists and overwrite disabled."""
        action = copy_action.Action()

        mock_is_done_info.return_value = (
            '/dest/folder',
            '/dest/folder/file.jpg',
            'jpg'
        )
        mock_exists.return_value = True  # File exists

        photo = Mock()
        photo.info = {'path': '/source/image.jpg', 'type': 'jpg'}
        setting = Mock(return_value=False)  # overwrite_existing_images=False

        result = action.apply(photo, setting, {})

        # Should NOT call copy2
        mock_copy2.assert_not_called()
        assert result == photo

    @patch('phatch.actions.copy.shutil.copy2')
    @patch('phatch.actions.copy.os.path.exists')
    @patch.object(copy_action.Action, 'ensure_path_or_desktop')
    @patch.object(copy_action.Action, 'is_done_info')
    def test_apply_copies_when_exists_with_overwrite(self, mock_is_done_info,
                                                     mock_ensure_path,
                                                     mock_exists, mock_copy2):
        """apply should copy when file exists but overwrite enabled."""
        action = copy_action.Action()

        mock_is_done_info.return_value = (
            '/dest/folder',
            '/dest/folder/file.jpg',
            'jpg'
        )
        mock_exists.return_value = True  # File exists
        mock_ensure_path.return_value = '/dest/folder/file.jpg'

        photo = Mock()
        photo.info = {'path': '/source/image.jpg', 'type': 'jpg'}
        setting = Mock(return_value=True)  # overwrite_existing_images=True

        result = action.apply(photo, setting, {})

        # Should call copy2
        mock_copy2.assert_called_once()
        assert result == photo

    @patch('phatch.actions.copy.shutil.copy2')
    @patch('phatch.actions.copy.os.path.exists')
    @patch.object(copy_action.Action, 'ensure_path_or_desktop')
    @patch.object(copy_action.Action, 'is_done_info')
    def test_apply_ensures_path(self, mock_is_done_info, mock_ensure_path,
                               mock_exists, mock_copy2):
        """apply should ensure destination path exists."""
        action = copy_action.Action()

        mock_is_done_info.return_value = (
            '/dest/folder',
            '/dest/folder/file.jpg',
            'jpg'
        )
        mock_exists.return_value = False
        mock_ensure_path.return_value = '/actual/path/file.jpg'

        photo = Mock()
        photo.info = {'path': '/source/image.jpg', 'type': 'jpg'}
        setting = Mock(return_value=False)

        result = action.apply(photo, setting, {})

        # Should call ensure_path_or_desktop
        mock_ensure_path.assert_called_once()
        # Should use the path returned by ensure_path_or_desktop
        mock_copy2.assert_called_with('/source/image.jpg',
                                     '/actual/path/file.jpg')
        # Should return the original photo for chaining
        assert result is photo


class TestCopyIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = copy_action.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = copy_action.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = copy_action.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'file' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_copy(self):
        """Action documentation mentions copy."""
        action = copy_action.Action()
        doc_lower = action.__doc__.lower()
        assert 'copy' in doc_lower

    def test_action_uses_apply_not_pil(self):
        """Action uses apply() method (file operation, not image processing)."""
        action = copy_action.Action()
        # Should have apply method
        assert hasattr(action, 'apply')
        # pil should be None (not a staticmethod for file operations)
        assert copy_action.Action.pil is None
