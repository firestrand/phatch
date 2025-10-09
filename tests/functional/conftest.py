"""
Functional/acceptance test fixtures and configuration.

This module provides fixtures specifically for functional/acceptance tests.
These tests validate end-to-end workflows and real-world usage scenarios.
"""

import pytest


@pytest.fixture(scope="session")
def sample_actionlists_dir(project_root):
    """
    Get the directory containing sample actionlists.

    Args:
        project_root: Path to project root (from parent conftest.py)

    Returns:
        Path: Path to data/actionlists directory
    """
    return project_root / 'data' / 'actionlists'


@pytest.fixture(scope="session")
def test_images_dir(test_input_dir):
    """
    Get the directory containing test images.

    Args:
        test_input_dir: Path to tests/input directory (from parent conftest.py)

    Returns:
        Path: Path to tests/input directory with sample images
    """
    return test_input_dir


@pytest.fixture
def functional_output_dir(tmp_path):
    """
    Create a temporary output directory for functional test results.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path: Path to temporary output directory for this test
    """
    output_dir = tmp_path / "functional_output"
    output_dir.mkdir()
    return output_dir
