"""Unit tests for phatch.actions.watermark module.

Tests the Watermark action (apply watermark with tiling, scaling, opacity).

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
from phatch.actions import watermark
from unittest.mock import patch, Mock


class TestWatermarkAction:
    """Test the Watermark action class metadata."""

    def test_action_exists(self):
        """Watermark action class should exist."""
        assert hasattr(watermark, 'Action')
        assert watermark.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = watermark.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(watermark.Action, 'pil')
        assert callable(watermark.Action.pil)

    def test_action_inherits_from_stamp_mixin(self):
        """Action should inherit from StampMixin."""
        # Check that StampMixin is in the MRO
        base_names = [base.__name__ for base in watermark.Action.__mro__]
        assert 'StampMixin' in base_names


class TestWatermarkInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_mark_field(self):
        """interface should define Mark parameter."""
        action = watermark.Action()
        fields = {}
        action.interface(fields)

        assert any('mark' in k.lower() for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = watermark.Action()
        fields = {}
        action.interface(fields)

        assert any('opacity' in k.lower() for k in fields.keys())

    def test_interface_defines_method_field(self):
        """interface should define Method parameter."""
        action = watermark.Action()
        fields = {}
        action.interface(fields)

        assert any('method' in k.lower() for k in fields.keys())

    def test_interface_defines_offset_fields(self):
        """interface should define offset-related parameters."""
        action = watermark.Action()
        fields = {}
        action.interface(fields)

        assert any('horizontal' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())
        assert any('vertical' in k.lower() and 'offset' in k.lower()
                   for k in fields.keys())


class TestWatermarkConstants:
    """Test module-level and class constants."""

    def test_stamp_mixin_has_methods(self):
        """StampMixin should define METHODS constant."""
        action = watermark.Action()
        assert hasattr(action, 'METHODS')
        assert isinstance(action.METHODS, list)

    def test_methods_has_three_values(self):
        """METHODS should have three values."""
        action = watermark.Action()
        assert len(action.METHODS) == 3
