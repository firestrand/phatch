"""Shared PIL image fixtures for the entire test suite.

These fixtures provide common image patterns used across unit, integration,
and acceptance tests. Centralising them keeps tests DRY and makes updates to
sample imagery straightforward.
"""

from __future__ import annotations

from typing import Tuple

import pytest
from PIL import Image


RGBColor = Tuple[int, int, int]
RGBASwatch = Tuple[int, int, int, int]


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_rgb_image(size: Tuple[int, int] = (100, 100), color: RGBColor | str = 'red') -> Image.Image:
    """Return a solid RGB image."""
    return Image.new('RGB', size, color=color)


def create_rgba_image(
    size: Tuple[int, int] = (100, 100),
    color: RGBASwatch = (255, 0, 0, 255),
    transparent_region: Tuple[slice, slice] | None = None,
    transparent_color: RGBASwatch = (255, 0, 0, 128),
) -> Image.Image:
    """Return an RGBA image with an optional semi-transparent region."""
    img = Image.new('RGBA', size, color=color)
    if transparent_region:
        pixels = img.load()
        x_slice, y_slice = transparent_region
        for x in range(*x_slice.indices(size[0])):
            for y in range(*y_slice.indices(size[1])):
                pixels[x, y] = transparent_color
    return img


def create_grayscale_image(size: Tuple[int, int] = (100, 100), value: int = 128) -> Image.Image:
    """Return a grayscale image filled with ``value``."""
    return Image.new('L', size, color=value)


def create_gradient_image(size: Tuple[int, int] = (100, 100)) -> Image.Image:
    """Return a left-to-right horizontal gradient RGB image."""
    img = Image.new('RGB', size)
    pixels = img.load()
    width, height = size
    for x in range(width):
        color_value = int((x / max(width - 1, 1)) * 255)
        for y in range(height):
            pixels[x, y] = (color_value, color_value, color_value)
    return img


def create_multicolor_image(size: Tuple[int, int] = (100, 100)) -> Image.Image:
    """Return an image split into four coloured quadrants."""
    img = Image.new('RGB', size)
    pixels = img.load()
    mid_x = size[0] // 2
    mid_y = size[1] // 2
    for x in range(size[0]):
        for y in range(size[1]):
            if x < mid_x and y < mid_y:
                pixels[x, y] = (255, 0, 0)  # red
            elif x >= mid_x and y < mid_y:
                pixels[x, y] = (0, 255, 0)  # green
            elif x < mid_x and y >= mid_y:
                pixels[x, y] = (0, 0, 255)  # blue
            else:
                pixels[x, y] = (255, 255, 255)  # white
    return img


# ---------------------------------------------------------------------------
# Fixtures (function scope by default)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_image_100x100() -> Image.Image:
    return create_rgb_image((100, 100), 'red')


@pytest.fixture
def sample_image_200x200() -> Image.Image:
    return create_rgb_image((200, 200), 'blue')


@pytest.fixture
def sample_rgba_image() -> Image.Image:
    return create_rgba_image((100, 100), transparent_region=(slice(0, 50), slice(0, 50)))


@pytest.fixture
def sample_grayscale_image() -> Image.Image:
    return create_grayscale_image((100, 100), value=128)


@pytest.fixture
def rgb_image() -> Image.Image:
    return create_rgb_image((100, 100), 'red')


@pytest.fixture
def rgba_image() -> Image.Image:
    return create_rgba_image((100, 100), transparent_region=(slice(0, 50), slice(0, 50)))


@pytest.fixture
def grayscale_image() -> Image.Image:
    return create_grayscale_image((100, 100), value=128)


@pytest.fixture
def gradient_image() -> Image.Image:
    return create_gradient_image((100, 100))


@pytest.fixture
def multicolor_image() -> Image.Image:
    return create_multicolor_image((100, 100))


@pytest.fixture
def small_image() -> Image.Image:
    return create_rgb_image((10, 10), 'blue')


@pytest.fixture
def large_image() -> Image.Image:
    return create_rgb_image((500, 500), 'green')
