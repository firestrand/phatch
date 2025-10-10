"""Unit tests for phatch.actions.round module.

Tests the Round action (rounded or crossed corners).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from PIL import Image
from phatch.actions import round as round_action


class TestRoundAction:
    """Test the Round action class metadata."""

    def test_action_exists(self):
        """Round action class should exist."""
        assert hasattr(round_action, 'Action')
        assert round_action.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = round_action.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(round_action.Action, 'pil')
        assert callable(round_action.Action.pil)

    def test_action_has_cache(self):
        """Action should have cache enabled."""
        action = round_action.Action()
        assert action.cache is True


class TestRoundConstants:
    """Test module-level constants."""

    def test_corners_constant_exists(self):
        """CORNERS constant should exist."""
        assert hasattr(round_action, 'CORNERS')
        assert isinstance(round_action.CORNERS, list)

    def test_corners_has_three_values(self):
        """CORNERS should have three values."""
        assert len(round_action.CORNERS) == 3


class TestRoundHelperFunctions:
    """Test helper functions."""

    def test_create_corner_function_exists(self):
        """create_corner function should exist."""
        assert hasattr(round_action, 'create_corner')
        assert callable(round_action.create_corner)

    def test_create_corner_creates_mask(self):
        """create_corner creates corner mask."""
        round_action.init()

        corner = round_action.create_corner(radius=50, opacity=255)

        assert isinstance(corner, Image.Image)
        assert corner.mode == 'L'
        assert corner.size == (50, 50)

    def test_create_rounded_rectangle_function_exists(self):
        """create_rounded_rectangle function should exist."""
        assert hasattr(round_action, 'create_rounded_rectangle')
        assert callable(round_action.create_rounded_rectangle)

    def test_create_rounded_rectangle_creates_mask(self):
        """create_rounded_rectangle creates rounded rectangle mask."""
        round_action.init()
        cache = {}

        mask = round_action.create_rounded_rectangle(size=(100, 100),
                                                     cache=cache,
                                                     radius=20)

        assert isinstance(mask, Image.Image)
        assert mask.mode == 'L'
        assert mask.size == (100, 100)


class TestRoundFunction:
    """Test the round_image() PIL function."""

    def test_round_image_function_exists(self):
        """round_image function should exist."""
        assert hasattr(round_action, 'round_image')
        assert callable(round_action.round_image)

    def test_round_image_basic(self, rgb_image):
        """Round image with basic settings."""
        round_action.init()

        result = round_action.round_image(rgb_image, radius=20)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_round_image_rgba(self, rgba_image):
        """Round RGBA image."""
        round_action.init()

        result = round_action.round_image(rgba_image, radius=20)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_round_image_with_radius(self, rgb_image):
        """Round image with custom radius."""
        round_action.init()

        result = round_action.round_image(rgb_image, radius=30)

        assert isinstance(result, Image.Image)

    def test_round_image_all_corners(self, rgb_image):
        """Round all corners with same type."""
        round_action.init()

        result = round_action.round_image(rgb_image, round_all=True,
                                         rounding_type=round_action.ROUNDED,
                                         radius=20)

        assert isinstance(result, Image.Image)

    def test_round_image_square_corners(self, rgb_image):
        """Round with square corners."""
        round_action.init()

        result = round_action.round_image(rgb_image, round_all=True,
                                         rounding_type=round_action.SQUARE,
                                         radius=20)

        assert isinstance(result, Image.Image)

    def test_round_image_cross_corners(self, rgb_image):
        """Round with cross corners."""
        round_action.init()

        result = round_action.round_image(rgb_image, round_all=True,
                                         rounding_type=round_action.CROSS,
                                         radius=20)

        assert isinstance(result, Image.Image)

    def test_round_image_caching(self, rgb_image):
        """Round image uses caching."""
        round_action.init()
        cache = {}

        # First call
        result1 = round_action.round_image(rgb_image, cache=cache, radius=20)
        cache_size_1 = len(cache)

        # Second call with same parameters
        result2 = round_action.round_image(rgb_image, cache=cache, radius=20)
        cache_size_2 = len(cache)

        # Cache should be reused
        assert cache_size_1 > 0
        assert cache_size_1 == cache_size_2


class TestRoundIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_round_image(self, multicolor_image):
        """Action.pil should call round_image function."""
        round_action.init()

        result = round_action.Action.pil(multicolor_image, radius=30)

        assert isinstance(result, Image.Image)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = round_action.Action()
        assert action is not None

    def test_action_pil_points_to_round_image(self):
        """Action.pil should point to round_image function."""
        assert round_action.Action.pil == round_action.round_image

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        round_action.init()
        assert hasattr(round_action, 'Image')
        assert hasattr(round_action, 'ImageDraw')
