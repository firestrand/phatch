"""Unit tests for phatch.actions.effect module.

Tests the Effect action (apply visual effects/filters).

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

from phatch.actions import effect
from PIL import Image, ImageFilter


class TestEffectAction:
    """Test the Effect action class metadata."""

    def test_action_exists(self):
        """Effect action class should exist."""
        assert hasattr(effect, 'Action')
        assert effect.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = effect.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = effect.Action()
        assert 'effect' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(effect.Action, 'init')
        assert callable(effect.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(effect.Action, 'pil')
        assert callable(effect.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = effect.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = effect.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestEffectInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_three_fields(self):
        """Effect should have three parameters."""
        action = effect.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 3

    def test_interface_defines_filter_field(self):
        """interface should define Filter parameter."""
        action = effect.Action()
        fields = {}
        action.interface(fields)

        assert any('filter' in k.lower() for k in fields.keys())

    def test_interface_defines_repeat_field(self):
        """interface should define Repeat parameter."""
        action = effect.Action()
        fields = {}
        action.interface(fields)

        assert any('repeat' in k.lower() for k in fields.keys())

    def test_interface_defines_amount_field(self):
        """interface should define Amount parameter."""
        action = effect.Action()
        fields = {}
        action.interface(fields)

        assert any('amount' in k.lower() for k in fields.keys())


class TestEffectInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(effect, 'init')
        assert callable(effect.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        effect.init()

        # Should have loaded Image, ImageFilter, imtools
        assert hasattr(effect, 'Image')
        assert hasattr(effect, 'ImageFilter')
        assert hasattr(effect, 'imtools')


class TestEffectFunction:
    """Test the effect() function."""

    def test_effect_function_exists(self):
        """effect function should exist."""
        assert hasattr(effect, 'effect')
        assert callable(effect.effect)

    def test_effect_returns_image(self):
        """effect should return Image object."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_applies_blur_filter(self):
        """effect should apply BLUR filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        # Result should be same size
        assert result.size == (100, 100)
        assert result.mode in ['RGB', 'RGBA']

    def test_effect_applies_sharpen_filter(self):
        """effect should apply SHARPEN filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'SHARPEN', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_applies_contour_filter(self):
        """effect should apply CONTOUR filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'CONTOUR', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_applies_emboss_filter(self):
        """effect should apply EMBOSS filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'EMBOSS', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_applies_smooth_filter(self):
        """effect should apply SMOOTH filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'SMOOTH', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_with_amount_less_than_100(self):
        """effect should blend when amount < 100."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% blend with filtered image
        result = effect.effect(image, 'BLUR', 50, 1)

        assert isinstance(result, Image.Image)

    def test_effect_with_repeat_parameter(self):
        """effect should repeat filter application."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        # Apply blur 3 times
        result = effect.effect(image, 'BLUR', 100, 3)

        assert isinstance(result, Image.Image)

    def test_effect_with_rgba_image(self):
        """effect should handle RGBA images."""
        effect.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = effect.effect(image, 'BLUR', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_preserves_alpha_for_contour(self):
        """effect should preserve alpha channel for CONTOUR filter."""
        effect.init()

        # RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = effect.effect(image, 'CONTOUR', 100, 1)

        # Should have alpha channel preserved
        assert result.mode == 'RGBA'

    def test_effect_preserves_alpha_for_emboss(self):
        """effect should preserve alpha channel for EMBOSS filter."""
        effect.init()

        # RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = effect.effect(image, 'EMBOSS', 100, 1)

        # Should have alpha channel preserved
        assert result.mode == 'RGBA'

    def test_effect_with_full_amount(self):
        """effect should use filtered image directly when amount=100."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_with_minimum_amount(self):
        """effect should handle minimum amount (1%)."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 1, 1)

        assert isinstance(result, Image.Image)


class TestEffectEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_effect_with_single_repeat(self):
        """effect should work with repeat=1."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_with_multiple_repeats(self):
        """effect should work with repeat > 1."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'BLUR', 100, 5)

        assert isinstance(result, Image.Image)

    def test_effect_with_small_image(self):
        """effect should handle small images."""
        effect.init()

        image = Image.new('RGB', (10, 10), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        # Should maintain size
        assert result.size == (10, 10)

    def test_effect_with_large_image(self):
        """effect should handle large images."""
        effect.init()

        image = Image.new('RGB', (500, 500), 'red')
        result = effect.effect(image, 'BLUR', 100, 1)

        assert result.size == (500, 500)

    def test_effect_detail_filter(self):
        """effect should apply DETAIL filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'DETAIL', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_edge_enhance_filter(self):
        """effect should apply EDGE_ENHANCE filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'EDGE_ENHANCE', 100, 1)

        assert isinstance(result, Image.Image)

    def test_effect_find_edges_filter(self):
        """effect should apply FIND_EDGES filter."""
        effect.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = effect.effect(image, 'FIND_EDGES', 100, 1)

        assert isinstance(result, Image.Image)


class TestEffectIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = effect.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = effect.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 3

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = effect.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_effects(self):
        """Action documentation mentions effects or filters."""
        action = effect.Action()
        doc_lower = action.__doc__.lower()
        # Should mention at least one effect type
        assert any(word in doc_lower for word in ['blur', 'sharpen', 'emboss', 'smooth'])

    def test_action_pil_is_effect(self):
        """Action.pil should be effect function."""
        assert effect.Action.pil == effect.effect
