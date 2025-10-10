"""Unit tests for phatch.actions.rank module.

Tests the Rank action (apply rank filter).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch, MagicMock
import pytest

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import rank
from PIL import Image


class TestRankAction:
    """Test the Rank action class metadata."""

    def test_action_exists(self):
        """Rank action class should exist."""
        assert hasattr(rank, 'Action')
        assert rank.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = rank.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = rank.Action()
        assert 'rank' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(rank.Action, 'init')
        assert callable(rank.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(rank.Action, 'pil')
        assert callable(rank.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = rank.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = rank.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestRankInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_three_fields(self):
        """Rank should have three parameters."""
        action = rank.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 3

    def test_interface_defines_radius_field(self):
        """interface should define Radius parameter."""
        action = rank.Action()
        fields = {}
        action.interface(fields)

        assert any('radius' in k.lower() for k in fields.keys())

    def test_interface_defines_rank_field(self):
        """interface should define Rank parameter."""
        action = rank.Action()
        fields = {}
        action.interface(fields)

        assert any('rank' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = rank.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestRankInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(rank, 'init')
        assert callable(rank.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        rank.init()

        # Should have loaded Image, ImageFilter, imtools
        assert hasattr(rank, 'Image')
        assert hasattr(rank, 'ImageFilter')
        assert hasattr(rank, 'imtools')


class TestRnkFunction:
    """Test the rnk() function."""

    def test_rnk_function_exists(self):
        """rnk function should exist."""
        assert hasattr(rank, 'rnk')
        assert callable(rank.rnk)

    def test_rnk_returns_image(self):
        """rnk should return Image object."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_radius_1(self):
        """rnk should apply filter with radius 1."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 1, 50, 100)

        # Result should be same size
        assert result.size == (100, 100)

    def test_rnk_with_radius_3(self):
        """rnk should apply filter with radius 3."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 3, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_rank_0(self):
        """rnk should handle rank=0 (minimum)."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # rank=0 should select minimum pixel
        result = rank.rnk(image, 1, 0, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_rank_50(self):
        """rnk should handle rank=50 (median)."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # rank=50 should select median pixel
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_rank_100(self):
        """rnk should handle rank=100 (maximum)."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # rank=100 should select maximum pixel
        result = rank.rnk(image, 1, 100, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_amount_less_than_100(self):
        """rnk should blend when amount < 100."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% blend with filtered image
        result = rank.rnk(image, 1, 50, 50)

        assert isinstance(result, Image.Image)

    def test_rnk_with_full_amount(self):
        """rnk should use filtered image directly when amount=100."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_minimum_amount(self):
        """rnk should handle minimum amount (1%)."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 1, 50, 1)

        assert isinstance(result, Image.Image)

    def test_rnk_with_rgba_image(self):
        """rnk should handle RGBA images."""
        rank.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_preserves_size(self):
        """rnk should preserve image size."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = rank.rnk(image, 3, 50, 100)

        assert result.size == (100, 100)


class TestRankEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_rnk_with_small_image(self):
        """rnk should handle small images."""
        rank.init()

        image = Image.new('RGB', (10, 10), 'red')
        result = rank.rnk(image, 1, 50, 100)

        # Should maintain size
        assert result.size == (10, 10)

    def test_rnk_with_large_image(self):
        """rnk should handle large images."""
        rank.init()

        image = Image.new('RGB', (500, 500), 'red')
        result = rank.rnk(image, 1, 50, 100)

        assert result.size == (500, 500)

    def test_rnk_with_small_radius(self):
        """rnk should work with minimum radius."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # Note: RankFilter requires radius > 0
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_large_radius(self):
        """rnk should handle large radius."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')
        # RankFilter has size limitations - use radius 5 as a safe large value
        result = rank.rnk(image, 5, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_grayscale_image(self):
        """rnk should handle grayscale images."""
        rank.init()

        image = Image.new('L', (100, 100), 128)
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_p_mode_image(self):
        """rnk should handle palette mode images."""
        rank.init()

        image = Image.new('P', (100, 100))
        result = rank.rnk(image, 1, 50, 100)

        assert isinstance(result, Image.Image)

    def test_rnk_with_various_ranks(self):
        """rnk should handle different rank values."""
        rank.init()

        image = Image.new('RGB', (100, 100), 'red')

        # Test various rank percentages
        for rank_value in [0, 25, 50, 75, 100]:
            result = rank.rnk(image, 1, rank_value, 100)
            assert isinstance(result, Image.Image)


class TestRankIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = rank.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = rank.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 3

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = rank.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_rank(self):
        """Action documentation mentions rank or pixel."""
        action = rank.Action()
        doc_lower = action.__doc__.lower()
        assert 'rank' in doc_lower or 'pixel' in doc_lower

    def test_action_pil_is_rnk(self):
        """Action.pil should be rnk function."""
        assert rank.Action.pil == rank.rnk
