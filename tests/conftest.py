"""Pytest configuration and shared fixtures for Phatch test suite."""

import os
import sys
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

pytest_plugins = [
    "tests.fixtures.images",
]

_SESSION_ENVIRONMENT: ExitStack | None = None
_SANDBOX_PATHS = {
    'HOME': 'home',
    'USERPROFILE': 'home',
    'APPDATA': 'config',
    'LOCALAPPDATA': 'data',
    'XDG_DATA_HOME': 'data',
    'XDG_CONFIG_HOME': 'config',
    'XDG_CACHE_HOME': 'cache',
    'XDG_RUNTIME_DIR': 'runtime',
    'TMPDIR': 'tmp',
    'TEMP': 'tmp',
    'TMP': 'tmp',
    'PHATCH_PORTABLE_ROOT': 'portable',
}


def _restore_environment(snapshot: dict[str, str]) -> None:
    os.environ.clear()
    os.environ.update(snapshot)


def _close_session_environment() -> None:
    global _SESSION_ENVIRONMENT
    if _SESSION_ENVIRONMENT is not None:
        _SESSION_ENVIRONMENT.close()
        _SESSION_ENVIRONMENT = None


def _start_session_environment(project_root: Path) -> None:
    global _SESSION_ENVIRONMENT
    with ExitStack() as startup:
        root = Path(startup.enter_context(TemporaryDirectory(
            prefix='phatch-tests-',
        )))
        snapshot = os.environ.copy()
        startup.callback(_restore_environment, snapshot)
        environment = {
            name: str(root / relative)
            for name, relative in _SANDBOX_PATHS.items()
        }
        for path in set(environment.values()):
            Path(path).mkdir()
        environment.update({
            'PHATCH_TEST_ROOT': str(root),
            'PYTHONPATH': str(project_root),
            'PYTHONDONTWRITEBYTECODE': '1',
        })
        os.environ.update(environment)
        _SESSION_ENVIRONMENT = startup.pop_all()


@dataclass(frozen=True, slots=True)
class IsolatedRuntime:
    root: Path
    cwd: Path
    home: Path
    env: dict[str, str]


@pytest.fixture
def isolated_runtime(tmp_path, project_root):
    home = tmp_path / 'home'
    cwd = tmp_path / 'outside'
    data = tmp_path / 'data'
    config = tmp_path / 'config'
    cache = tmp_path / 'cache'
    runtime = tmp_path / 'runtime'
    portable = tmp_path / 'portable'
    for path in (home, cwd, data, config, cache, runtime, portable):
        path.mkdir()

    env = os.environ.copy()
    env.update({
        'HOME': str(home),
        'USERPROFILE': str(home),
        'APPDATA': str(config),
        'LOCALAPPDATA': str(data),
        'XDG_DATA_HOME': str(data),
        'XDG_CONFIG_HOME': str(config),
        'XDG_CACHE_HOME': str(cache),
        'XDG_RUNTIME_DIR': str(runtime),
        'TMPDIR': str(runtime),
        'TEMP': str(runtime),
        'TMP': str(runtime),
        'PHATCH_PORTABLE_ROOT': str(portable),
        'PHATCH_TEST_ROOT': str(tmp_path),
        'PYTHONPATH': str(project_root),
        'PYTHONDONTWRITEBYTECODE': '1',
    })
    return IsolatedRuntime(root=tmp_path, cwd=cwd, home=home, env=env)


@pytest.fixture
def initialized_runtime(isolated_runtime, monkeypatch):
    from phatch import phatch
    from phatch.core import api, config, ct

    user_data = isolated_runtime.root / 'data' / 'phatch'
    user_config = isolated_runtime.root / 'config' / 'phatch'
    user_cache = isolated_runtime.root / 'cache' / 'phatch'
    user_paths = {
        'USER_PATH': isolated_runtime.home,
        'USER_CACHE_PATH': user_cache,
        'USER_FONTS_CACHE_PATH': user_cache / 'fonts.cache',
        'USER_LOG_PATH': user_cache / 'log',
        'USER_PREVIEW_PATH': user_cache / 'preview',
        'USER_CONFIG_PATH': user_config,
        'USER_SETTINGS_PATH': user_config / 'settings.py',
        'USER_DATA_PATH': user_data,
        'USER_ACTIONS_PATH': user_data / 'actions',
        'USER_ACTIONLISTS_PATH': user_data / 'actionlists',
        'USER_BIN_PATH': user_data / 'bin',
        'USER_FONTS_PATH': user_data / 'fonts',
        'USER_GEEK_PATH': user_data / 'geek.txt',
        'USER_MASKS_PATH': user_data / 'masks',
        'USER_HIGHLIGHTS_PATH': user_data / 'highlights',
        'USER_WATERMARKS_PATH': user_data / 'watermarks',
    }
    for name, path in user_paths.items():
        monkeypatch.setattr(config, name, str(path))
        if hasattr(ct, name):
            monkeypatch.setattr(ct, name, str(path))

    config.init_config_paths(phatch.create_paths('..'))
    api.init()
    return isolated_runtime


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def project_root():
    """
    Get the project root directory.

    Returns:
        Path: Absolute path to project root (parent of tests directory)
    """
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def tests_dir():
    """
    Get the tests directory.

    Returns:
        Path: Absolute path to tests directory
    """
    return Path(__file__).parent


@pytest.fixture(scope="session")
def phatch_package_dir(project_root):
    """
    Get the phatch package directory.

    Returns:
        Path: Absolute path to phatch package
    """
    return project_root / 'phatch'


@pytest.fixture(scope="session")
def test_input_dir(tests_dir):
    """
    Get the test input directory containing sample images.

    Returns:
        Path: Absolute path to tests/input
    """
    return tests_dir / 'input'


@pytest.fixture(scope="session")
def test_output_dir(tests_dir):
    """
    Get the test output directory.

    Returns:
        Path: Absolute path to tests/output
    """
    return tests_dir / 'output'


# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """
    Pytest configuration hook.

    Isolates process paths before collection and makes Phatch importable.
    """
    project_root = Path(__file__).parent.parent
    _start_session_environment(project_root)
    sys.path.insert(0, str(project_root))


def pytest_sessionfinish(session, exitstatus):
    _close_session_environment()


def pytest_unconfigure(config):
    _close_session_environment()


# ============================================================================
# Custom Markers
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to add markers and skip conditions.

    This hook runs after test collection and can modify test items.
    """
    # Add marker documentation is in pytest.ini
    pass
