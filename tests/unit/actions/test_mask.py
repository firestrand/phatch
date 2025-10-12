"""Unit tests for phatch.actions.mask module.

Tests the Mask action (apply transparency mask).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import patch

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from PIL import Image
from phatch.actions import mask as mask_action


class TestMaskAction:
    """Test the Mask action class metadata."""

    def test_action_exists(self):
        """Mask action class should exist."""
        assert hasattr(mask_action, 'Action')
        assert mask_action.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = mask_action.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = mask_action.Action()
        assert 'mask' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(mask_action.Action, 'pil')
        assert callable(mask_action.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = mask_action.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_cache(self):
        """Action should have cache enabled."""
        action = mask_action.Action()
        assert action.cache is True

    def test_action_tags(self):
        """Action should have filter tag."""
        action = mask_action.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestMaskInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_mask_field(self):
        """interface should define Mask parameter."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)

        assert any('mask' in k.lower() for k in fields.keys())

    def test_interface_defines_resample_mask_field(self):
        """interface should define Resample Mask parameter."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)

        assert any('resample' in k.lower() and 'mask' in k.lower()
                   for k in fields.keys())

    def test_interface_has_two_fields(self):
        """Mask should have two parameters (mask and resample)."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 2

    def test_interface_mask_is_mask_file_field(self):
        """Mask should be a MaskFileField."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)

        # Get the Mask field
        mask_field = None
        for key, value in fields.items():
            if 'mask' in key.lower() and 'resample' not in key.lower():
                mask_field = value
                break

        assert mask_field is not None
        assert type(mask_field).__name__ == 'MaskFileField'

    def test_interface_resample_is_image_resample_field(self):
        """Resample Mask should be an ImageResampleField."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)

        # Get the Resample Mask field
        resample_field = None
        for key, value in fields.items():
            if 'resample' in key.lower():
                resample_field = value
                break

        assert resample_field is not None
        assert type(resample_field).__name__ == 'ImageResampleField'


class TestPutMaskFunction:
    """Test the put_mask() PIL function."""

    def test_put_mask_function_exists(self):
        """put_mask function should exist."""
        assert hasattr(mask_action, 'put_mask')
        assert callable(mask_action.put_mask)

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_basic_rgb(self, mock_has_transparency, mock_open,
                                rgb_image):
        """Apply mask on RGB image."""
        mask_action.init()

        # Create mock mask
        mask_img = Image.new('L', rgb_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        result = mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'
        assert mock_open.called

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_rgba(self, mock_has_transparency, mock_open,
                           rgba_image):
        """Apply mask on RGBA image."""
        mask_action.init()

        mask_img = Image.new('L', rgba_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.side_effect = [True, True]  # image, then alpha

        result = mask_action.put_mask(rgba_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_with_cache(self, mock_has_transparency, mock_open,
                                 rgb_image):
        """Apply mask with caching."""
        mask_action.init()

        mask_img = Image.new('L', rgb_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        cache = {}

        # First call
        result1 = mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST',
                                      cache=cache)

        # Cache should have one entry
        assert len(cache) == 1

        # Second call with same parameters
        result2 = mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST',
                                      cache=cache)

        # Cache should still have one entry (reused)
        assert len(cache) == 1

        # open should only be called once (on first call)
        assert mock_open.call_count == 1
        assert result1.size == rgb_image.size
        assert result2.size == rgb_image.size

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_different_resample_modes(self, mock_has_transparency,
                                               mock_open, rgb_image):
        """Apply mask with different resample modes."""
        mask_action.init()

        mask_img = Image.new('L', rgb_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        resample_modes = ['NEAREST', 'BILINEAR', 'BICUBIC']

        for mode in resample_modes:
            result = mask_action.put_mask(rgb_image, 'test_mask.png', mode)
            assert isinstance(result, Image.Image)

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_with_existing_alpha(self, mock_has_transparency,
                                          mock_open, rgba_image):
        """Apply mask on image with existing alpha channel.

        Note: Full testing of alpha blending is limited by lazy-loading.
        See REFACTORING.md for dependency injection improvements.
        """
        mask_action.init()

        mask_img = Image.new('L', rgba_image.size, 200)

        mock_open.return_value = mask_img
        mock_has_transparency.side_effect = [True, True]

        result = mask_action.put_mask(rgba_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)
        # Result should maintain RGBA mode
        assert result.mode == 'RGBA'

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_resizes_mask_to_image_size(self, mock_has_transparency,
                                                 mock_open, rgb_image):
        """Mask should be resized to match image size."""
        mask_action.init()

        # Create mask with different size
        mask_img = Image.new('L', (50, 50), 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        result = mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)
        # Result should match input image size, not mask size
        assert result.size == rgb_image.size


class TestMaskEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_small_image(self, mock_has_transparency, mock_open,
                                  small_image):
        """Apply mask on small image."""
        mask_action.init()

        mask_img = Image.new('L', small_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        result = mask_action.put_mask(small_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)
        assert result.size == small_image.size

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_grayscale(self, mock_has_transparency, mock_open,
                                grayscale_image):
        """Apply mask on grayscale image."""
        mask_action.init()

        mask_img = Image.new('L', grayscale_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        result = mask_action.put_mask(grayscale_image, 'test_mask.png',
                                      'NEAREST')

        assert isinstance(result, Image.Image)
        # Grayscale should be converted to RGBA when mask is applied
        assert result.mode == 'RGBA'

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_put_mask_without_cache(self, mock_has_transparency, mock_open,
                                    rgb_image):
        """Apply mask without providing cache (defaults to empty dict)."""
        mask_action.init()

        mask_img = Image.new('L', rgb_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        # Call without cache parameter (should default to {})
        result = mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST')

        assert isinstance(result, Image.Image)


class TestMaskConstants:
    """Test module-level constants."""

    def test_mask_constant_exists(self):
        """MASK constant should exist."""
        assert hasattr(mask_action, 'MASK')
        assert isinstance(mask_action.MASK, str)

    def test_masks_constant_exists(self):
        """MASKS list constant should exist."""
        assert hasattr(mask_action, 'MASKS')
        assert isinstance(mask_action.MASKS, list)

    def test_masks_contains_mask(self):
        """MASKS list should contain MASK."""
        assert mask_action.MASK in mask_action.MASKS


class TestMaskIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = mask_action.Action()
        assert action is not None

    def test_action_pil_points_to_put_mask(self):
        """Action.pil should point to put_mask function."""
        assert mask_action.Action.pil == mask_action.put_mask

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        mask_action.init()
        assert hasattr(mask_action, 'Image')
        assert hasattr(mask_action, 'ImageMath')

    def test_init_loads_imtools(self):
        """init() should load imtools module."""
        mask_action.init()
        assert hasattr(mask_action, 'imtools')

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = mask_action.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = mask_action.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_mask(self):
        """Action documentation mentions mask."""
        action = mask_action.Action()
        doc_lower = action.__doc__.lower()
        assert 'mask' in doc_lower


class TestMaskCaching:
    """Test caching behavior."""

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_cache_key_includes_size(self, mock_has_transparency, mock_open,
                                     rgb_image):
        """Cache key should include image size."""
        mask_action.init()

        mask_img = Image.new('L', (50, 50), 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        cache = {}
        mask_action.put_mask(rgb_image, 'test_mask.png', 'NEAREST',
                            cache=cache)

        # Cache key should include width and height
        cache_keys = list(cache.keys())
        assert len(cache_keys) == 1
        assert 'w%d' % rgb_image.width in cache_keys[0]
        assert 'h%d' % rgb_image.height in cache_keys[0]

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_cache_key_includes_mask_path(self, mock_has_transparency,
                                          mock_open, rgb_image):
        """Cache key should include mask file path."""
        mask_action.init()

        mask_img = Image.new('L', rgb_image.size, 128)
        mock_open.return_value = mask_img
        mock_has_transparency.return_value = False

        cache = {}
        mask_path = 'my_custom_mask.png'
        mask_action.put_mask(rgb_image, mask_path, 'NEAREST', cache=cache)

        cache_keys = list(cache.keys())
        assert len(cache_keys) == 1
        assert mask_path in cache_keys[0]

    @patch('phatch.actions.mask.open_image')
    @patch('phatch.lib.imtools.has_transparency')
    def test_different_sizes_use_different_cache_entries(self,
                                                         mock_has_transparency,
                                                         mock_open):
        """Different image sizes should use different cache entries."""
        mask_action.init()

        mask_img1 = Image.new('L', (100, 100), 128)
        mask_img2 = Image.new('L', (200, 200), 128)
        mock_open.side_effect = [mask_img1, mask_img2]
        mock_has_transparency.return_value = False

        cache = {}

        # Apply mask to two different sized images
        image1 = Image.new('RGB', (100, 100), 'red')
        image2 = Image.new('RGB', (200, 200), 'blue')

        mask_action.put_mask(image1, 'test_mask.png', 'NEAREST', cache=cache)
        mask_action.put_mask(image2, 'test_mask.png', 'NEAREST', cache=cache)

        # Should have two cache entries
        assert len(cache) == 2
