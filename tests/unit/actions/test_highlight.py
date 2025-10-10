"""Unit tests for phatch.actions.highlight module.

Tests the Highlight action (apply transparency highlight).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock, patch
import pytest

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import highlight
from PIL import Image


class TestHighlightAction:
    """Test the Highlight action class metadata."""

    def test_action_exists(self):
        """Highlight action class should exist."""
        assert hasattr(highlight, 'Action')
        assert highlight.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = highlight.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = highlight.Action()
        assert 'highlight' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(highlight.Action, 'init')
        assert callable(highlight.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(highlight.Action, 'pil')
        assert callable(highlight.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = highlight.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = highlight.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower

    def test_action_cache_enabled(self):
        """Cache should be enabled for this action."""
        assert highlight.Action.cache is True


class TestHighlightInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_three_fields(self):
        """Highlight should have three parameters."""
        action = highlight.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 3

    def test_interface_defines_highlight_field(self):
        """interface should define Highlight parameter."""
        action = highlight.Action()
        fields = {}
        action.interface(fields)

        assert any('highlight' in k.lower() for k in fields.keys())

    def test_interface_defines_resample_field(self):
        """interface should define Resample Highlight parameter."""
        action = highlight.Action()
        fields = {}
        action.interface(fields)

        assert any('resample' in k.lower() for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = highlight.Action()
        fields = {}
        action.interface(fields)

        assert any('opacity' in k.lower() for k in fields.keys())


class TestHighlightInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(highlight, 'init')
        assert callable(highlight.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        highlight.init()

        # Should have loaded Image, ImageMath
        assert hasattr(highlight, 'Image')
        assert hasattr(highlight, 'ImageMath')
        assert hasattr(highlight, 'imtools')


class TestPutHighlightFunction:
    """Test the put_highlight() function."""

    def test_put_highlight_function_exists(self):
        """put_highlight function should exist."""
        assert hasattr(highlight, 'put_highlight')
        assert callable(highlight.put_highlight)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_returns_image(self, mock_open):
        """put_highlight should return Image object."""
        highlight.init()

        # Create images
        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        assert isinstance(result, Image.Image)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_converts_to_rgba(self, mock_open):
        """put_highlight should convert image to RGBA."""
        highlight.init()

        # RGB image
        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        assert result.mode == 'RGBA'

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_uses_cache(self, mock_open):
        """put_highlight should use cache for repeated calls."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        cache = {}

        # First call
        result1 = highlight.put_highlight(image, 'test.png', 'NEAREST', 100, cache)

        # Cache should have one entry
        assert len(cache) == 1

        # Second call with same parameters
        result2 = highlight.put_highlight(image, 'test.png', 'NEAREST', 100, cache)

        # Should still have one entry (reused)
        assert len(cache) == 1

        # open_image should only be called once
        assert mock_open.call_count == 1

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_resizes_highlight_to_image_size(self, mock_open):
        """put_highlight should resize highlight to match image size."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        # Result should be same size as input
        assert result.size == (100, 100)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_applies_opacity(self, mock_open):
        """put_highlight should apply opacity < 100."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 255))

        mock_open.return_value = highlight_img

        # 50% opacity
        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 50)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_with_rgba_image(self, mock_open):
        """put_highlight should handle RGBA input images."""
        highlight.init()

        # Already RGBA
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 255))
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        assert result.mode == 'RGBA'
        assert result.size == (100, 100)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_cache_key_includes_parameters(self, mock_open):
        """Cache key should include size and opacity."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        cache = {}

        # Different opacity should create different cache entry
        highlight.put_highlight(image, 'test.png', 'NEAREST', 100, cache)
        highlight.put_highlight(image, 'test.png', 'NEAREST', 50, cache)

        # Should have two entries
        assert len(cache) == 2


class TestHighlightEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_with_small_image(self, mock_open):
        """put_highlight should handle small images."""
        highlight.init()

        image = Image.new('RGB', (10, 10), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 128))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        # Should resize highlight to match small image
        assert result.size == (10, 10)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_with_zero_opacity(self, mock_open):
        """put_highlight should handle 0% opacity."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 255))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 0)

        assert isinstance(result, Image.Image)

    @patch('phatch.actions.highlight.open_image')
    def test_put_highlight_with_full_opacity(self, mock_open):
        """put_highlight should handle 100% opacity."""
        highlight.init()

        image = Image.new('RGB', (100, 100), 'red')
        highlight_img = Image.new('RGBA', (50, 50), (255, 255, 255, 255))

        mock_open.return_value = highlight_img

        result = highlight.put_highlight(image, 'test.png', 'NEAREST', 100)

        assert isinstance(result, Image.Image)


class TestHighlightIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = highlight.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = highlight.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 3

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = highlight.Action()
        assert action.author == 'Nadia Alramli'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_highlight(self):
        """Action documentation mentions highlight or transparency."""
        action = highlight.Action()
        doc_lower = action.__doc__.lower()
        assert 'highlight' in doc_lower or 'transparency' in doc_lower
