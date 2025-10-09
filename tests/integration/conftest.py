"""
Integration test fixtures and configuration.

This module provides fixtures specifically for integration tests.
Integration tests may use real file I/O and test interactions between modules.
"""

import pytest
from PIL import Image


@pytest.fixture
def temp_test_image(tmp_path):
    """
    Create a temporary test image file.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path: Path to a temporary PNG image file
    """
    img_path = tmp_path / "test_image.png"
    img = Image.new('RGB', (100, 100), color='green')
    img.save(img_path)
    return img_path


@pytest.fixture
def temp_output_dir(tmp_path):
    """
    Create a temporary output directory for test results.

    Args:
        tmp_path: pytest's tmp_path fixture

    Returns:
        Path: Path to temporary output directory
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def sample_actionlist():
    """
    Create a simple actionlist for testing.

    Returns:
        list: List of action dictionaries
    """
    return [
        {
            'action': 'scale',
            'width': '50%',
            'height': '50%',
        },
        {
            'action': 'save',
            'path': '',  # Will be set by tests
        }
    ]
