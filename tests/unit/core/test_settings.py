"""Unit tests for phatch.core.settings module.

Tests settings dictionary creation and configuration merging.
"""

import builtins
from unittest.mock import Mock, patch

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import settings


class TestCreateSettings:
    """Test create_settings function."""

    def test_create_settings_returns_dict(self):
        """create_settings should return a dictionary."""
        result = settings.create_settings(config_paths={})
        assert isinstance(result, dict)

    def test_create_settings_has_required_keys(self):
        """create_settings should include required setting keys."""
        result = settings.create_settings(config_paths={})

        # Execute settings
        assert 'extensions' in result
        assert 'recursive' in result
        assert 'stop_for_errors' in result
        assert 'overwrite_existing_images' in result
        assert 'no_save' in result
        assert 'check_images_first' in result
        assert 'always_show_status_dialog' in result
        assert 'desktop' in result
        assert 'safe' in result
        assert 'repeat' in result

    def test_create_settings_console_keys(self):
        """create_settings should include console setting keys."""
        result = settings.create_settings(config_paths={})

        assert 'console' in result
        assert 'init_fonts' in result
        assert 'interactive' in result
        assert 'verbose' in result

    def test_create_settings_gui_keys(self):
        """create_settings should include GUI setting keys."""
        result = settings.create_settings(config_paths={})

        assert 'browse_source' in result
        assert 'tag_actions' in result
        assert 'description' in result
        assert 'collapse_automatic' in result
        assert 'droplet' in result
        assert 'droplet_path' in result
        assert 'file_history' in result
        assert 'image_inspector' in result
        assert 'paths' in result

    def test_create_settings_internal_keys(self):
        """create_settings should include internal setting keys."""
        result = settings.create_settings(config_paths={})

        assert 'overwrite_existing_images_forced' in result


class TestDefaultValues:
    """Test default values of settings."""

    def test_default_boolean_values(self):
        """Test default boolean setting values."""
        result = settings.create_settings(config_paths={})

        assert result['recursive'] is False
        assert result['stop_for_errors'] is True
        assert result['overwrite_existing_images'] is True
        assert result['no_save'] is False
        assert result['check_images_first'] is True
        assert result['always_show_status_dialog'] is True
        assert result['desktop'] is False
        assert result['safe'] is True
        assert result['console'] is False
        assert result['init_fonts'] is False
        assert result['interactive'] is False
        assert result['verbose'] is False
        assert result['description'] is True
        assert result['collapse_automatic'] is False
        assert result['droplet'] is False
        assert result['image_inspector'] is False
        assert result['overwrite_existing_images_forced'] is False

    def test_default_numeric_values(self):
        """Test default numeric setting values."""
        result = settings.create_settings(config_paths={})

        assert result['repeat'] == 1
        assert result['browse_source'] == 0

    def test_default_list_values(self):
        """Test default list setting values."""
        result = settings.create_settings(config_paths={})

        assert isinstance(result['file_history'], list)
        assert len(result['file_history']) == 0
        assert isinstance(result['paths'], list)
        assert len(result['paths']) > 0  # Should have at least USER_PATH

    def test_default_extensions(self):
        """Test that extensions are set from IMAGE_READ_EXTENSIONS."""
        result = settings.create_settings(config_paths={})

        assert 'extensions' in result
        # Should be a list/tuple of image extensions
        assert isinstance(result['extensions'], (list, tuple))
        # Should contain common image formats
        extensions_str = ' '.join(str(e).lower() for e in result['extensions'])
        assert any(fmt in extensions_str for fmt in ['jpg', 'png', 'gif', 'bmp'])


class TestOptionsOverride:
    """Test that options parameter overrides defaults."""

    def test_options_override_boolean(self):
        """Options should override boolean settings."""
        options = Mock()
        options.recursive = True
        options.verbose = False

        result = settings.create_settings(config_paths={}, options=options)

        assert result['recursive'] is True
        assert result['verbose'] is False

    def test_options_override_numeric(self):
        """Options should override numeric settings."""
        options = Mock()
        options.repeat = 5
        options.browse_source = 2

        result = settings.create_settings(config_paths={}, options=options)

        assert result['repeat'] == 5
        assert result['browse_source'] == 2

    def test_options_override_list(self):
        """Options should override list settings."""
        options = Mock()
        options.paths = ['/custom/path1', '/custom/path2']

        result = settings.create_settings(config_paths={}, options=options)

        assert result['paths'] == ['/custom/path1', '/custom/path2']

    def test_options_partial_override(self):
        """Options should only override specified attributes."""
        options = Mock()
        options.recursive = True
        # Don't set verbose, should keep default

        # Mock hasattr to only return True for recursive
        original_hasattr = hasattr
        def mock_hasattr(obj, name):
            if obj is options and name == 'recursive':
                return True
            if obj is options and name in ['verbose', 'console']:
                return False
            return original_hasattr(obj, name)

        with patch('builtins.hasattr', side_effect=mock_hasattr):
            result = settings.create_settings(config_paths={}, options=options)

        assert result['recursive'] is True
        assert result['verbose'] is False  # Should keep default

    def test_options_none_keeps_defaults(self):
        """None options should keep all defaults."""
        result = settings.create_settings(config_paths={}, options=None)

        # Should have default values
        assert result['recursive'] is False
        assert result['verbose'] is False


class TestConfigPathsMerge:
    """Test that config_paths are merged into settings."""

    def test_config_paths_added_to_settings(self):
        """Config paths should be added to settings dict."""
        config_paths = {
            'PHATCH_DATA_PATH': '/test/data',
            'PHATCH_FONTS_PATH': '/test/fonts',
            'USER_PATH': '/test/user',
        }

        result = settings.create_settings(config_paths=config_paths)

        assert result['PHATCH_DATA_PATH'] == '/test/data'
        assert result['PHATCH_FONTS_PATH'] == '/test/fonts'
        # Note: USER_PATH in config_paths may override settings['paths']

    def test_config_paths_empty_dict(self):
        """Empty config_paths should not break settings."""
        result = settings.create_settings(config_paths={})

        # Should still have default settings
        assert 'recursive' in result
        assert 'verbose' in result

    def test_config_paths_override_defaults(self):
        """Config paths should override default setting keys if they conflict."""
        # If config_paths has a key that exists in default settings,
        # config_paths should win (due to update)
        config_paths = {
            'recursive': 'config_value',  # Normally boolean, but testing override
        }

        result = settings.create_settings(config_paths=config_paths)

        # Config paths are merged last, so they override
        assert result['recursive'] == 'config_value'

    @patch('phatch.core.config.init_config_paths')
    def test_config_paths_none_calls_init(self, mock_init):
        """None config_paths should trigger init_config_paths."""
        mock_init.return_value = {
            'PHATCH_DATA_PATH': '/initialized/data',
        }

        result = settings.create_settings(config_paths=None, options=None)

        # Should have called init_config_paths
        mock_init.assert_called_once()
        # Should have merged returned config
        assert result['PHATCH_DATA_PATH'] == '/initialized/data'


class TestDependencies:
    """Test module dependencies and imports."""

    def test_imports_from_ct(self):
        """Module should import from ct module."""
        # ct is imported and used for USER_PATH
        from phatch.core import ct
        assert hasattr(ct, 'USER_PATH')

    def test_imports_from_pil(self):
        """Module should import IMAGE_READ_EXTENSIONS from pil."""
        from phatch.core.pil import IMAGE_READ_EXTENSIONS
        assert IMAGE_READ_EXTENSIONS is not None

    def test_image_read_extensions_in_settings(self):
        """Settings should use IMAGE_READ_EXTENSIONS for extensions."""
        from phatch.core.pil import IMAGE_READ_EXTENSIONS
        result = settings.create_settings(config_paths={})

        # Should be the same reference or equal value
        assert result['extensions'] == IMAGE_READ_EXTENSIONS


class TestEdgeCases:
    """Test edge cases and unusual inputs."""

    def test_options_with_extra_attributes(self):
        """Options with extra attributes should not break."""
        options = Mock()
        options.recursive = True
        options.extra_unknown_attr = 'value'

        # Should not raise exception
        result = settings.create_settings(config_paths={}, options=options)
        assert result['recursive'] is True

    def test_config_paths_with_many_entries(self):
        """Config paths with many entries should all be included."""
        config_paths = {f'KEY_{i}': f'value_{i}' for i in range(100)}

        result = settings.create_settings(config_paths=config_paths)

        # All should be in result
        for i in range(100):
            assert result[f'KEY_{i}'] == f'value_{i}'

    def test_both_options_and_config_paths(self):
        """Both options and config_paths should be merged correctly."""
        options = Mock()
        options.recursive = True
        options.verbose = False

        config_paths = {
            'PHATCH_DATA_PATH': '/custom/data',
        }

        result = settings.create_settings(config_paths=config_paths, options=options)

        # Should have options overrides
        assert result['recursive'] is True
        assert result['verbose'] is False
        # Should have config paths
        assert result['PHATCH_DATA_PATH'] == '/custom/data'
        # Should have defaults for other keys
        assert 'stop_for_errors' in result


class TestIntegration:
    """Test realistic integration scenarios."""

    def test_cli_console_mode(self):
        """Test settings for CLI console mode."""
        options = Mock()
        options.console = True
        options.verbose = True
        options.recursive = True

        result = settings.create_settings(config_paths={}, options=options)

        assert result['console'] is True
        assert result['verbose'] is True
        assert result['recursive'] is True

    def test_gui_mode_defaults(self):
        """Test settings for GUI mode (no options)."""
        result = settings.create_settings(config_paths={})

        # GUI settings should be present
        assert result['console'] is False
        assert result['droplet'] is False
        assert result['image_inspector'] is False
        assert isinstance(result['file_history'], list)

    def test_droplet_mode(self):
        """Test settings for droplet mode."""
        options = Mock()
        options.droplet = True

        result = settings.create_settings(config_paths={}, options=options)

        assert result['droplet'] is True
        assert 'droplet_path' in result

    def test_batch_processing_settings(self):
        """Test settings for batch processing."""
        options = Mock()
        options.recursive = True
        options.repeat = 3
        options.overwrite_existing_images = True

        result = settings.create_settings(config_paths={}, options=options)

        assert result['recursive'] is True
        assert result['repeat'] == 3
        assert result['overwrite_existing_images'] is True
