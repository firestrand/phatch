"""Shared fixtures for action plugin tests.

Provides reusable PIL Image fixtures for testing actions.
Following SOLID, DRY, KISS principles.
"""

import pytest
from PIL import Image


@pytest.fixture
def rgb_image():
    """Create a simple RGB test image (100x100 red)."""
    return Image.new('RGB', (100, 100), color='red')


@pytest.fixture
def rgba_image():
    """Create an RGBA test image with transparency (100x100)."""
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
    # Add some transparency
    pixels = img.load()
    for x in range(50):
        for y in range(50):
            pixels[x, y] = (255, 0, 0, 128)  # Semi-transparent red
    return img


@pytest.fixture
def grayscale_image():
    """Create a grayscale test image (100x100)."""
    return Image.new('L', (100, 100), color=128)


@pytest.fixture
def gradient_image():
    """Create an RGB image with horizontal gradient (100x100)."""
    img = Image.new('RGB', (100, 100))
    pixels = img.load()
    for x in range(100):
        color_value = int((x / 100.0) * 255)
        for y in range(100):
            pixels[x, y] = (color_value, color_value, color_value)
    return img


@pytest.fixture
def multicolor_image():
    """Create an image with multiple color regions for testing."""
    img = Image.new('RGB', (100, 100))
    pixels = img.load()
    # Top-left: red
    for x in range(50):
        for y in range(50):
            pixels[x, y] = (255, 0, 0)
    # Top-right: green
    for x in range(50, 100):
        for y in range(50):
            pixels[x, y] = (0, 255, 0)
    # Bottom-left: blue
    for x in range(50):
        for y in range(50, 100):
            pixels[x, y] = (0, 0, 255)
    # Bottom-right: white
    for x in range(50, 100):
        for y in range(50, 100):
            pixels[x, y] = (255, 255, 255)
    return img


@pytest.fixture
def small_image():
    """Create a small RGB image (10x10) for quick tests."""
    return Image.new('RGB', (10, 10), color='blue')


@pytest.fixture
def large_image():
    """Create a large RGB image (500x500) for performance tests."""
    return Image.new('RGB', (500, 500), color='green')
