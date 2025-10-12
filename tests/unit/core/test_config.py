"""Unit tests for phatch.core.config module.

Tests configuration path management, initialization, and platform-specific
path handling.
"""

import builtins
import locale
import os
import sys
from unittest.mock import Mock, patch



# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.core import config


class TestPathConstants:
    """Test that config module defines required path constants."""

    def test_user_path_defined(self):
        """USER_PATH should be defined."""
        assert hasattr(config, 'USER_PATH')
        assert config.USER_PATH is not None

    def test_user_cache_path_defined(self):
        """USER_CACHE_PATH should be defined."""
        assert hasattr(config, 'USER_CACHE_PATH')
        assert config.USER_CACHE_PATH is not None

    def test_user_config_path_defined(self):
        """USER_CONFIG_PATH should be defined."""
        assert hasattr(config, 'USER_CONFIG_PATH')
        assert config.USER_CONFIG_PATH is not None

    def test_user_data_path_defined(self):
        """USER_DATA_PATH should be defined."""
        assert hasattr(config, 'USER_DATA_PATH')
        assert config.USER_DATA_PATH is not None

    def test_user_paths_are_strings(self):
        """All USER_* paths should be strings."""
        user_paths = [
            config.USER_PATH,
            config.USER_CACHE_PATH,
            config.USER_CONFIG_PATH,
            config.USER_DATA_PATH,
        ]
        for path in user_paths:
            assert isinstance(path, str), f"Path {path} is not a string"

    def test_user_paths_contain_phatch(self):
        """User cache/config/data paths should contain 'phatch' subdirectory."""
        # USER_PATH is the home folder, others should be under it with 'phatch'
        assert 'phatch' in config.USER_CACHE_PATH.lower()
        assert 'phatch' in config.USER_CONFIG_PATH.lower()
        assert 'phatch' in config.USER_DATA_PATH.lower()

    def test_specific_user_paths_defined(self):
        """Specific user paths should be defined."""
        paths = [
            'USER_FONTS_CACHE_PATH',
            'USER_LOG_PATH',
            'USER_PREVIEW_PATH',
            'USER_SETTINGS_PATH',
            'USER_ACTIONS_PATH',
            'USER_ACTIONLISTS_PATH',
            'USER_BIN_PATH',
            'USER_FONTS_PATH',
            'USER_GEEK_PATH',
            'USER_MASKS_PATH',
            'USER_HIGHLIGHTS_PATH',
            'USER_WATERMARKS_PATH',
        ]
        for path_name in paths:
            assert hasattr(config, path_name), f"{path_name} not defined"
            path_value = getattr(config, path_name)
            assert path_value is not None, f"{path_name} is None"
            assert isinstance(path_value, str), f"{path_name} is not a string"


class TestWrapFunction:
    """Test the _wrap helper function."""

    def test_wrap_adds_phatch_subdirectory(self):
        """_wrap should append 'phatch' to the path."""
        result = config._wrap('/tmp/test')
        assert result == os.path.join('/tmp/test', 'phatch')

    def test_wrap_with_empty_string(self):
        """_wrap should handle empty string."""
        result = config._wrap('')
        assert result == 'phatch'

    def test_wrap_preserves_path_structure(self):
        """_wrap should preserve the original path structure."""
        test_path = '/home/user/.config'
        result = config._wrap(test_path)
        assert result.startswith(test_path)
        assert result.endswith('phatch')


class TestFixPythonPath:
    """Test fix_python_path function."""

    def test_fix_python_path_without_argument(self):
        """fix_python_path should determine path from __file__ if not provided."""
        # Store original sys.path
        original_path = sys.path.copy()
        try:
            result = config.fix_python_path()
            # Result should be a valid path
            assert isinstance(result, str)
            assert os.path.isabs(result)
            # Result should be in sys.path
            assert any(result == p for p in sys.path)
        finally:
            # Restore original sys.path
            sys.path[:] = original_path

    def test_fix_python_path_with_custom_path(self):
        """fix_python_path should add custom path to sys.path."""
        original_path = sys.path.copy()
        try:
            test_path = '/custom/test/path'
            result = config.fix_python_path(test_path)
            assert result == test_path
            # Path should be added to sys.path if not already there
            # (might already be there from previous tests, so check it's present)
            assert any(test_path == p for p in sys.path)
        finally:
            sys.path[:] = original_path

    def test_fix_python_path_no_duplicate(self):
        """fix_python_path should not add duplicates to sys.path."""
        original_path = sys.path.copy()
        try:
            test_path = '/unique/test/path'
            # Add it twice
            config.fix_python_path(test_path)
            config.fix_python_path(test_path)
            # Count occurrences
            count = sum(1 for p in sys.path if p == test_path)
            # Should only be added once
            assert count == 1
        finally:
            sys.path[:] = original_path


class TestCheckConfigPaths:
    """Test check_config_paths function."""

    def test_check_config_paths_with_provided_paths(self):
        """check_config_paths should use provided paths when given."""
        custom_paths = {
            'PHATCH_DATA_PATH': '/custom/data',
            'PHATCH_FONTS_PATH': '/custom/fonts',
            'PHATCH_FONTS_CACHE_PATH': '/custom/cache/fonts',
            'PHATCH_ACTIONLISTS_PATH': '/custom/actionlists',
        }
        result = config.check_config_paths(custom_paths)
        # Should return the same dict
        assert result == custom_paths
        # Should set SYSTEM_INSTALL to False
        assert config.SYSTEM_INSTALL is False

    def test_check_config_paths_without_paths(self):
        """check_config_paths should generate system paths when not provided."""
        # Pass None to trigger system install path generation
        result = config.check_config_paths(None)
        # Should return a dict
        assert isinstance(result, dict)
        # Should set SYSTEM_INSTALL to True
        assert config.SYSTEM_INSTALL is True
        # Should contain expected keys
        expected_keys = [
            'PHATCH_DATA_PATH',
            'PHATCH_FONTS_PATH',
            'PHATCH_FONTS_CACHE_PATH',
            'PHATCH_ACTIONLISTS_PATH',
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_check_config_paths_sets_globals(self):
        """check_config_paths should set global path variables."""
        custom_paths = {
            'PHATCH_DATA_PATH': '/test/data',
            'PHATCH_FONTS_PATH': '/test/fonts',
            'PHATCH_FONTS_CACHE_PATH': '/test/cache',
            'PHATCH_ACTIONLISTS_PATH': '/test/actionlists',
        }
        config.check_config_paths(custom_paths)
        # Check that globals were set
        assert config.PHATCH_DATA_PATH == '/test/data'
        assert config.PHATCH_FONTS_PATH == '/test/fonts'
        assert config.PHATCH_FONTS_CACHE_PATH == '/test/cache'
        assert config.PHATCH_ACTIONLISTS_PATH == '/test/actionlists'


class TestLocaleDetection:
    def test_detect_default_locale_prefers_environment(self):
        with patch.dict(os.environ, {'LC_ALL': 'fr_FR.UTF-8'}, clear=True):
            assert config._detect_default_locale() == 'fr_FR'

    def test_load_locale_falls_back_to_en(self, monkeypatch, tmp_path):
        # Force failing setlocale and no detected locale so fallback is used
        monkeypatch.setattr(config.locale, 'setlocale', Mock(side_effect=locale.Error('fail')))
        monkeypatch.setattr(config, '_detect_default_locale', lambda: None)

        captured = {}

        def fake_translation(app_name, translations_path, languages, fallback):
            captured['languages'] = languages

            class DummyTranslation:
                def install(self_inner):
                    captured['install_called'] = True

            return DummyTranslation()

        monkeypatch.setattr(config.gettext, 'translation', fake_translation)

        config.load_locale('phatch', str(tmp_path), canonical='default')

        assert captured['languages'][0] == 'en'
        assert captured.get('install_called') is True


class TestAddUserPaths:
    """Test add_user_paths function."""

    def test_add_user_paths_updates_dict(self):
        """add_user_paths should add USER_* paths to config dict."""
        config_paths = {}
        config.add_user_paths(config_paths)

        # Should contain all USER_* paths
        expected_keys = [
            'USER_PATH',
            'USER_ACTIONS_PATH',
            'USER_BIN_PATH',
            'USER_DATA_PATH',
            'USER_FONTS_PATH',
            'USER_GEEK_PATH',
            'USER_LOG_PATH',
            'USER_FONTS_CACHE_PATH',
            'USER_MASKS_PATH',
            'USER_HIGHLIGHTS_PATH',
            'USER_PREVIEW_PATH',
            'USER_SETTINGS_PATH',
            'USER_WATERMARKS_PATH',
        ]
        for key in expected_keys:
            assert key in config_paths, f"Missing key: {key}"
            assert config_paths[key] is not None

    def test_add_user_paths_preserves_existing(self):
        """add_user_paths should not remove existing keys."""
        config_paths = {'EXISTING_KEY': 'existing_value'}
        config.add_user_paths(config_paths)
        # Original key should still be there
        assert 'EXISTING_KEY' in config_paths
        assert config_paths['EXISTING_KEY'] == 'existing_value'


class TestPathsClass:
    """Test Paths class."""

    def test_paths_getitem(self):
        """Paths class should support subscript notation."""
        paths = config.Paths()
        # The mock class just returns 'path' for any key
        assert paths['any_key'] == 'path'
        assert paths['another_key'] == 'path'


class TestVerifyAppUserPaths:
    """Test verify_app_user_paths function."""

    @patch('phatch.core.config.system.ensure_path')
    @patch('phatch.core.config.os.path.isfile')
    @patch('phatch.core.config.shutil.copyfile')
    def test_verify_creates_paths(self, mock_copyfile, mock_isfile, mock_ensure_path):
        """verify_app_user_paths should create all required directories."""
        # Mock that geek.txt doesn't exist
        mock_isfile.return_value = False
        # Set PHATCH_DATA_PATH for the test
        original_data_path = config.PHATCH_DATA_PATH
        config.PHATCH_DATA_PATH = '/test/data'

        try:
            config.verify_app_user_paths()

            # Should call ensure_path for each user path
            assert mock_ensure_path.call_count >= 7  # At least 7 paths

            # Should copy geek.txt if it doesn't exist
            mock_copyfile.assert_called_once()
        finally:
            config.PHATCH_DATA_PATH = original_data_path

    @patch('phatch.core.config.system.ensure_path')
    @patch('phatch.core.config.os.path.isfile')
    @patch('phatch.core.config.shutil.copyfile')
    def test_verify_skips_copy_if_geek_exists(self, mock_copyfile, mock_isfile, mock_ensure_path):
        """verify_app_user_paths should skip copying geek.txt if it exists."""
        # Mock that geek.txt exists
        mock_isfile.return_value = True

        config.verify_app_user_paths()

        # Should NOT copy geek.txt
        mock_copyfile.assert_not_called()


class TestLoadLocale:
    """Test load_locale function."""

    @patch('phatch.core.config.locale')
    @patch('phatch.core.config.gettext')
    @patch('phatch.core.config.glob.glob')
    def test_load_locale_with_default_canonical(self, mock_glob, mock_gettext, mock_locale):
        """load_locale should handle default canonical locale."""
        # Mock locale detection
        mock_locale.getdefaultlocale.return_value = ('en_US', 'UTF-8')
        mock_glob.return_value = []

        # Mock translation object
        mock_translation = Mock()
        mock_gettext.translation.return_value = mock_translation

        config.load_locale('phatch', '/test/locale')

        # Should call setlocale
        mock_locale.setlocale.assert_called_once()

        # Should call gettext.translation
        mock_gettext.translation.assert_called_once()

        # Should install translation
        mock_translation.install.assert_called_once()

    @patch('phatch.core.config.locale')
    @patch('phatch.core.config.gettext')
    @patch('phatch.core.config.glob.glob')
    def test_load_locale_with_custom_canonical(self, mock_glob, mock_gettext, mock_locale):
        """load_locale should use custom canonical when provided."""
        mock_glob.return_value = []
        mock_translation = Mock()
        mock_gettext.translation.return_value = mock_translation

        config.load_locale('phatch', '/test/locale', canonical='fr_FR')

        # Should use fr_FR as canonical
        call_args = mock_gettext.translation.call_args
        assert 'fr_FR' in call_args[1]['languages']

    @patch('phatch.core.config.locale.setlocale')
    @patch('phatch.core.config.gettext')
    @patch('phatch.core.config.glob.glob')
    def test_load_locale_handles_none_canonical(self, mock_glob, mock_gettext, mock_setlocale):
        """load_locale should default to 'en' if canonical is None."""
        mock_glob.return_value = []
        mock_translation = Mock()
        mock_gettext.translation.return_value = mock_translation

        with patch('phatch.core.config._detect_default_locale', return_value=None):
            config.load_locale('phatch', '/test/locale')

        # Should use 'en' as fallback
        call_args = mock_gettext.translation.call_args
        assert 'en' in call_args[1]['languages']


class TestCheckFonts:
    """Test check_fonts function."""

    @patch('phatch.core.config.subprocess.Popen')
    @patch('phatch.core.config.os.path.exists')
    def test_check_fonts_when_cache_missing(self, mock_exists, mock_popen):
        """check_fonts should initialize fonts when cache doesn't exist."""
        # Mock that cache files don't exist
        mock_exists.return_value = False

        config.check_fonts()

        # Should spawn subprocess to initialize fonts
        mock_popen.assert_called_once()

        # Check that --fonts flag is in the command
        call_args = mock_popen.call_args[0][0]
        assert '--fonts' in call_args

    @patch('phatch.core.config.subprocess.Popen')
    @patch('phatch.core.config.os.path.exists')
    def test_check_fonts_when_cache_exists(self, mock_exists, mock_popen):
        """check_fonts should skip initialization when cache exists."""
        # Mock that cache exists
        mock_exists.return_value = True

        config.check_fonts()

        # Should NOT spawn subprocess
        mock_popen.assert_not_called()

    @patch('phatch.core.config.subprocess.Popen')
    @patch('phatch.core.config.os.path.exists')
    def test_check_fonts_force_flag(self, mock_exists, mock_popen):
        """check_fonts should initialize when force=True even if cache exists."""
        # Mock that cache exists
        mock_exists.return_value = True

        config.check_fonts(force=True)

        # Should spawn subprocess despite cache existing
        mock_popen.assert_called_once()


class TestInitConfigPaths:
    """Test init_config_paths function."""

    @patch('phatch.core.config.fix_python_path')
    @patch('phatch.core.config.check_config_paths')
    @patch('phatch.core.config.add_user_paths')
    @patch('phatch.lib.fonts.set_font_cache')
    def test_init_config_paths_calls_required_functions(
        self, mock_set_font_cache, mock_add_user, mock_check_config, mock_fix_path
    ):
        """init_config_paths should call all required initialization functions."""
        # Mock return values
        mock_check_config.return_value = {'PHATCH_DATA_PATH': '/test'}
        mock_fix_path.return_value = '/phatch/path'

        result = config.init_config_paths()

        # Should call check_config_paths
        mock_check_config.assert_called_once()

        # Should call add_user_paths
        mock_add_user.assert_called_once()

        # Should call fix_python_path at least once
        assert mock_fix_path.call_count >= 1

        # Should call set_font_cache
        mock_set_font_cache.assert_called_once()

        # Should return config dict
        assert isinstance(result, dict)

    @patch('phatch.core.config.fix_python_path')
    @patch('phatch.core.config.check_config_paths')
    @patch('phatch.core.config.add_user_paths')
    @patch('phatch.lib.fonts.set_font_cache')
    def test_init_config_paths_with_custom_paths(
        self, mock_set_font_cache, mock_add_user, mock_check_config, mock_fix_path
    ):
        """init_config_paths should accept custom config_paths."""
        custom_paths = {'PHATCH_PYTHON_PATH': '/custom/python'}
        mock_check_config.return_value = custom_paths
        mock_fix_path.return_value = '/custom/python'

        config.init_config_paths(custom_paths)

        # Should pass custom paths to check_config_paths
        mock_check_config.assert_called_once_with(custom_paths)

        # Should use custom PHATCH_PYTHON_PATH
        assert any('/custom/python' in str(call) for call in mock_fix_path.call_args_list)


class TestLoadLocaleOnly:
    """Test load_locale_only function."""

    @patch('phatch.core.config.load_locale')
    @patch('phatch.core.config.check_config_paths')
    def test_load_locale_only_calls_required_functions(
        self, mock_check_config, mock_load_locale
    ):
        """load_locale_only should check paths and load locale."""
        mock_check_config.return_value = {
            'PHATCH_LOCALE_PATH': '/test/locale'
        }

        config.load_locale_only()

        # Should call check_config_paths
        mock_check_config.assert_called_once()

        # Should call load_locale with locale path
        mock_load_locale.assert_called_once_with(
            'phatch', '/test/locale'
        )

    @patch('phatch.core.config.load_locale')
    @patch('phatch.core.config.check_config_paths')
    def test_load_locale_only_with_custom_paths(
        self, mock_check_config, mock_load_locale
    ):
        """load_locale_only should accept custom config_paths."""
        custom_paths = {'PHATCH_LOCALE_PATH': '/custom/locale'}
        mock_check_config.return_value = custom_paths

        config.load_locale_only(custom_paths)

        # Should pass custom paths to check_config_paths
        mock_check_config.assert_called_once_with(custom_paths)

        # Should load locale from custom path
        mock_load_locale.assert_called_once_with(
            'phatch', '/custom/locale'
        )
