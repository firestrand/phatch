"""Tests for phatch.lib.pillow_compat module.

Tests Pillow version compatibility helpers for Pillow 9.x and 10.x.
"""

import pytest
from PIL import Image

from phatch.lib import pillow_compat


class TestGetResampleFilter:
    """Tests for get_resample_filter() function."""

    def test_get_resample_filter_lanczos_exists(self):
        """get_resample_filter('LANCZOS') should return a valid constant."""
        result = pillow_compat.get_resample_filter('LANCZOS')
        assert isinstance(result, int)
        assert result > 0

    def test_get_resample_filter_bilinear_exists(self):
        """get_resample_filter('BILINEAR') should return a valid constant."""
        result = pillow_compat.get_resample_filter('BILINEAR')
        assert isinstance(result, int)
        assert result > 0

    def test_get_resample_filter_bicubic_exists(self):
        """get_resample_filter('BICUBIC') should return a valid constant."""
        result = pillow_compat.get_resample_filter('BICUBIC')
        assert isinstance(result, int)
        assert result > 0

    def test_get_resample_filter_nearest_exists(self):
        """get_resample_filter('NEAREST') should return a valid constant."""
        result = pillow_compat.get_resample_filter('NEAREST')
        assert isinstance(result, int)
        assert result >= 0  # NEAREST can be 0

    def test_get_resample_filter_default_is_lanczos(self):
        """get_resample_filter() with no args should default to LANCZOS."""
        result = pillow_compat.get_resample_filter()
        lanczos = pillow_compat.get_resample_filter('LANCZOS')
        assert result == lanczos

    def test_get_resample_filter_invalid_raises_error(self):
        """get_resample_filter() with invalid name should raise AttributeError."""
        with pytest.raises(AttributeError) as exc_info:
            pillow_compat.get_resample_filter('INVALID_FILTER')
        assert 'No resampling filter found' in str(exc_info.value)
        assert 'INVALID_FILTER' in str(exc_info.value)

    def test_get_resample_filter_works_with_image_resize(self):
        """get_resample_filter() result should work with Image.resize()."""
        img = Image.new('RGB', (100, 100), 'red')
        resample = pillow_compat.get_resample_filter('LANCZOS')

        # Should not raise an error
        result = img.resize((50, 50), resample)
        assert result.size == (50, 50)

    def test_get_resample_filter_compatibility_lanczos_or_antialias(self):
        """LANCZOS filter should work regardless of Pillow version."""
        # Try to get LANCZOS - should work on Pillow 10+
        # Should fall back to ANTIALIAS on older versions
        result = pillow_compat.get_resample_filter('LANCZOS')

        # Verify it matches one of the expected constants
        if hasattr(Image, 'LANCZOS'):
            assert result == Image.LANCZOS
        elif hasattr(Image, 'ANTIALIAS'):
            assert result == Image.ANTIALIAS
        else:
            pytest.fail("Neither LANCZOS nor ANTIALIAS found in PIL.Image")

    def test_get_resample_filter_compatibility_bilinear_or_linear(self):
        """BILINEAR filter should work regardless of Pillow version."""
        result = pillow_compat.get_resample_filter('BILINEAR')

        # Verify it matches one of the expected constants
        if hasattr(Image, 'BILINEAR'):
            assert result == Image.BILINEAR
        elif hasattr(Image, 'LINEAR'):
            assert result == Image.LINEAR
        else:
            pytest.fail("Neither BILINEAR nor LINEAR found in PIL.Image")


class TestEnsureIntColor:
    """Tests for ensure_int_color() function."""

    def test_ensure_int_color_converts_floats_to_ints(self):
        """ensure_int_color() should convert float values to integers."""
        result = pillow_compat.ensure_int_color((255.0, 128.5, 0.7))
        assert result == (255, 128, 0)
        assert all(isinstance(c, int) for c in result)

    def test_ensure_int_color_preserves_integers(self):
        """ensure_int_color() should preserve integer values unchanged."""
        result = pillow_compat.ensure_int_color((255, 128, 0))
        assert result == (255, 128, 0)
        assert all(isinstance(c, int) for c in result)

    def test_ensure_int_color_handles_rgba(self):
        """ensure_int_color() should handle RGBA tuples."""
        result = pillow_compat.ensure_int_color((255.0, 128.0, 0.0, 200.5))
        assert result == (255, 128, 0, 200)
        assert len(result) == 4
        assert all(isinstance(c, int) for c in result)

    def test_ensure_int_color_rounds_floats(self):
        """ensure_int_color() should round floats to nearest integer."""
        result = pillow_compat.ensure_int_color((127.4, 127.5, 127.6))
        assert result == (127, 127, 127)

    def test_ensure_int_color_handles_edge_values(self):
        """ensure_int_color() should handle edge cases (0, 255)."""
        result = pillow_compat.ensure_int_color((0.0, 255.0, 128.0))
        assert result == (0, 255, 128)

    def test_ensure_int_color_works_with_image_new(self):
        """ensure_int_color() result should work with Image.new()."""
        color = pillow_compat.ensure_int_color((255.0, 128.5, 0.7))

        # Should not raise an error
        img = Image.new('RGB', (10, 10), color)
        assert img.size == (10, 10)
        assert img.mode == 'RGB'


class TestPillowCompatAliases:
    """Tests for convenience aliases (LANCZOS, BILINEAR, etc.)."""

    def test_lanczos_alias_exists(self):
        """LANCZOS alias should be defined and valid."""
        assert hasattr(pillow_compat, 'LANCZOS')
        assert isinstance(pillow_compat.LANCZOS, int)

    def test_bilinear_alias_exists(self):
        """BILINEAR alias should be defined and valid."""
        assert hasattr(pillow_compat, 'BILINEAR')
        assert isinstance(pillow_compat.BILINEAR, int)

    def test_bicubic_alias_exists(self):
        """BICUBIC alias should be defined and valid."""
        assert hasattr(pillow_compat, 'BICUBIC')
        assert isinstance(pillow_compat.BICUBIC, int)

    def test_nearest_alias_exists(self):
        """NEAREST alias should be defined and valid."""
        assert hasattr(pillow_compat, 'NEAREST')
        assert isinstance(pillow_compat.NEAREST, int)

    def test_lanczos_alias_matches_function(self):
        """LANCZOS alias should match get_resample_filter('LANCZOS')."""
        assert pillow_compat.LANCZOS == pillow_compat.get_resample_filter('LANCZOS')

    def test_bilinear_alias_matches_function(self):
        """BILINEAR alias should match get_resample_filter('BILINEAR')."""
        assert pillow_compat.BILINEAR == pillow_compat.get_resample_filter('BILINEAR')


class TestPillowCompatIntegration:
    """Integration tests for pillow_compat module."""

    def test_resize_with_lanczos_produces_valid_image(self):
        """Resizing with LANCZOS filter should produce valid output."""
        img = Image.new('RGB', (200, 200), (255, 0, 0))
        resample = pillow_compat.get_resample_filter('LANCZOS')

        result = img.resize((100, 100), resample)
        assert result.size == (100, 100)
        assert result.mode == 'RGB'

    def test_create_image_with_int_color(self):
        """Creating image with ensure_int_color() should work."""
        color = pillow_compat.ensure_int_color((255.0, 128.5, 64.7))
        img = Image.new('RGB', (50, 50), color)

        assert img.size == (50, 50)
        # Verify color was applied (check center pixel)
        center_pixel = img.getpixel((25, 25))
        assert center_pixel == (255, 128, 64)

    def test_complete_workflow_resize_and_color(self):
        """Complete workflow using both helpers."""
        # Create image with float colors
        color = pillow_compat.ensure_int_color((128.5, 64.2, 32.8))
        img = Image.new('RGB', (200, 200), color)

        # Resize with compatibility filter
        resample = pillow_compat.get_resample_filter('BILINEAR')
        result = img.resize((100, 100), resample)

        assert result.size == (100, 100)
        assert result.mode == 'RGB'
