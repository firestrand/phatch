"""
Unit test fixtures and configuration.

This module provides fixtures specifically for unit tests.
Unit tests should be fast, isolated, and not depend on external resources.
"""

import pytest
from PIL import Image


@pytest.fixture
def sample_image_100x100():
    """
    Create a simple 100x100 RGB test image.

    Returns:
        PIL.Image: A 100x100 red image
    """
    return Image.new('RGB', (100, 100), color='red')


@pytest.fixture
def sample_image_200x200():
    """
    Create a simple 200x200 RGB test image.

    Returns:
        PIL.Image: A 200x200 blue image
    """
    return Image.new('RGB', (200, 200), color='blue')


@pytest.fixture
def sample_rgba_image():
    """
    Create a simple RGBA test image with transparency.

    Returns:
        PIL.Image: A 100x100 RGBA image
    """
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
    return img


@pytest.fixture
def sample_grayscale_image():
    """
    Create a simple grayscale test image.

    Returns:
        PIL.Image: A 100x100 grayscale image
    """
    return Image.new('L', (100, 100), color=128)
