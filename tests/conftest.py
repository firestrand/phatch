"""Pytest configuration and shared fixtures for Phatch test suite."""

import sys
from pathlib import Path

import pytest

pytest_plugins = [
    "tests.fixtures.images",
]


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

    Adds project root to sys.path so tests can import phatch package.
    """
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))


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
