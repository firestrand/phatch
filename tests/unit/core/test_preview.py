"""Unit tests for phatch.core.preview module.

Tests preview thumbnail generation for action icons.

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies (filesystem, PIL)
- Each test has single responsibility
"""

import builtins
import os
from unittest.mock import patch, MagicMock

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import preview


class TestGenerateFunctionSignature:
    """Test generate() function signature and defaults."""

    def test_generate_function_exists(self):
        """generate function should exist."""
        assert hasattr(preview, 'generate')
        assert callable(preview.generate)

    def test_generate_has_expected_parameters(self):
        """generate should have source, size, path, force parameters."""
        import inspect
        sig = inspect.signature(preview.generate)
        params = list(sig.parameters.keys())

        assert 'source' in params
        assert 'size' in params
        assert 'path' in params
        assert 'force' in params

    def test_generate_default_size(self):
        """generate should default to (48, 48) size."""
        import inspect
        sig = inspect.signature(preview.generate)
        assert sig.parameters['size'].default == (48, 48)

    def test_generate_default_force(self):
        """generate should default to force=True."""
        import inspect
        sig = inspect.signature(preview.generate)
        assert sig.parameters['force'].default is True


class TestGenerateBasicBehavior:
    """Test basic preview generation behavior."""

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_opens_source_image(self, mock_open, mock_api, mock_ensure):
        """generate should open source image."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_open.return_value = mock_image

        preview.generate('/test/image.jpg')

        mock_open.assert_called_once_with('/test/image.jpg')

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_creates_thumbnail(self, mock_open, mock_api, mock_ensure):
        """generate should create thumbnail of source image."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (200, 200)
        mock_open.return_value = mock_image

        preview.generate('/test/image.jpg', size=(50, 50))

        # Should call thumbnail method
        assert mock_image.thumbnail.called

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_ensures_path_exists(self, mock_open, mock_api, mock_ensure):
        """generate should ensure output path exists."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_open.return_value = mock_image

        custom_path = '/custom/preview/path'
        preview.generate('/test/image.jpg', path=custom_path)

        mock_ensure.assert_called_once_with(custom_path)


class TestGenerateWithActions:
    """Test preview generation for multiple actions."""

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_processes_all_actions(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate should process all actions from api.ACTIONS."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = False

        # Create mock actions
        mock_action1 = MagicMock()
        mock_action1.return_value.label = 'Action1'
        mock_action1.return_value.apply_pil.return_value = MagicMock()

        mock_action2 = MagicMock()
        mock_action2.return_value.label = 'Action2'
        mock_action2.return_value.apply_pil.return_value = MagicMock()

        mock_api.ACTIONS = {'action1': mock_action1, 'action2': mock_action2}
        preview.generate('/test/image.jpg')

        # Both actions should be instantiated
        mock_action1.assert_called_once()
        mock_action2.assert_called_once()

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_initializes_each_action(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate should call init() on each action."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = False

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'TestAction'
        action_instance.apply_pil.return_value = MagicMock()
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'test': mock_action}
        preview.generate('/test/image.jpg')

        # Should call init on action instance
        action_instance.init.assert_called_once()

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_applies_action_to_copy(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate should apply action to copy of image."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_copy = MagicMock()
        mock_image.copy.return_value = mock_copy
        mock_open.return_value = mock_image
        mock_exists.return_value = False

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'TestAction'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'test': mock_action}
        preview.generate('/test/image.jpg')

        # Should apply action to copy
        action_instance.apply_pil.assert_called_once_with(mock_copy)

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_saves_result_with_action_label(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate should save result using action label as filename."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = False

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'Rotate'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        test_path = '/test/preview'
        mock_api.ACTIONS = {'rotate': mock_action}
        preview.generate('/test/image.jpg', path=test_path)

        # Should save with action label
        expected_filename = os.path.join(test_path, 'Rotate.png')
        result_image.save.assert_called_once_with(expected_filename)


class TestGenerateForceParameter:
    """Test force parameter behavior."""

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_force_true_overwrites_existing(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate with force=True should overwrite existing previews."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = True  # File exists

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'TestAction'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'test': mock_action}
        preview.generate('/test/image.jpg', force=True)

        # Should save even though file exists
        assert result_image.save.called

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_force_false_skips_existing(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate with force=False should skip existing previews."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = True  # File exists

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'TestAction'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'test': mock_action}
        preview.generate('/test/image.jpg', force=False)

        # Should NOT save since file exists
        assert not result_image.save.called

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_force_false_generates_missing(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate with force=False should generate missing previews."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = False  # File doesn't exist

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'TestAction'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'test': mock_action}
        preview.generate('/test/image.jpg', force=False)

        # Should save since file doesn't exist
        assert result_image.save.called


class TestGenerateSizeParameter:
    """Test custom size parameter."""

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_custom_size_small(self, mock_open, mock_api, mock_ensure):
        """generate should handle small custom size."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (200, 200)
        mock_open.return_value = mock_image

        preview.generate('/test/image.jpg', size=(32, 32))

        # Should call thumbnail (exact args depend on implementation)
        assert mock_image.thumbnail.called

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_custom_size_large(self, mock_open, mock_api, mock_ensure):
        """generate should handle large custom size."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (200, 200)
        mock_open.return_value = mock_image

        preview.generate('/test/image.jpg', size=(128, 128))

        assert mock_image.thumbnail.called


class TestGenerateDependencies:
    """Test module dependencies."""

    def test_imports_from_api(self):
        """preview should import from api module."""
        from phatch.core import api
        # ACTIONS is created dynamically by import_actions()
        # Just verify api module can be imported
        assert api is not None

    def test_imports_from_config(self):
        """preview should import USER_PREVIEW_PATH from config."""
        from phatch.core.config import USER_PREVIEW_PATH
        assert USER_PREVIEW_PATH is not None

    def test_imports_from_lib(self):
        """preview should import from lib modules."""
        from phatch.lib import openImage
        from phatch.lib.system import ensure_path
        assert hasattr(openImage, 'open')
        assert callable(ensure_path)


class TestGenerateEdgeCases:
    """Test edge cases and error conditions."""

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    def test_generate_with_no_actions(self, mock_open, mock_api, mock_ensure):
        """generate should handle empty ACTIONS dict."""
        mock_api.ACTIONS = {}
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_open.return_value = mock_image

        # Should not raise error with empty ACTIONS
        preview.generate('/test/image.jpg')

        # Should still open image and ensure path
        assert mock_open.called
        assert mock_ensure.called

    @patch('phatch.core.preview.ensure_path')
    @patch('phatch.core.preview.api')
    @patch('phatch.core.preview.openImage.open')
    @patch('phatch.core.preview.os.path.exists')
    def test_generate_with_single_action(self, mock_exists, mock_open, mock_api, mock_ensure):
        """generate should handle single action."""
        mock_image = MagicMock()
        mock_image.size = (100, 100)
        mock_image.copy.return_value = MagicMock()
        mock_open.return_value = mock_image
        mock_exists.return_value = False

        mock_action = MagicMock()
        action_instance = MagicMock()
        action_instance.label = 'OnlyAction'
        result_image = MagicMock()
        action_instance.apply_pil.return_value = result_image
        mock_action.return_value = action_instance

        mock_api.ACTIONS = {'only': mock_action}
        preview.generate('/test/image.jpg')

        # Should process the single action
        mock_action.assert_called_once()
        result_image.save.assert_called_once()


class TestModuleConstants:
    """Test module-level constants and imports."""

    def test_user_preview_path_imported(self):
        """USER_PREVIEW_PATH should be imported."""
        assert hasattr(preview, 'USER_PREVIEW_PATH')
        assert preview.USER_PREVIEW_PATH is not None
