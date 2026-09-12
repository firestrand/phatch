"""Unit tests for phatch.actions.watermark module.

Tests the Watermark action (apply watermark with tiling, scaling, opacity).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

from PIL import Image

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import watermark


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


class TestWatermarkInit:
    def test_init_preserves_imported_dependencies(self):
        image_module = watermark.Image
        layer_factory = watermark.generate_layer

        result = watermark.init()

        assert result is None
        assert watermark.Image is image_module
        assert watermark.generate_layer is layer_factory


class TestWatermarkPil:
    """Test the watermark.pil implementation."""

    def test_watermark_calls_generate_layer(self, monkeypatch, rgba_image):
        """watermark should request a layer and composite it."""

        calls = {}

        def fake_generate_layer(size, mark, method, h_off, v_off, h_just, v_just, orientation, opacity):
            calls['args'] = (size, mark, method, h_off, v_off, h_just, v_just, orientation, opacity)
            return Image.new('RGBA', size, (0, 0, 0, 128))

        monkeypatch.setattr(watermark, 'generate_layer', fake_generate_layer)

        mark = Image.new('RGBA', (10, 10), (255, 255, 255, 128))
        result = watermark.watermark(
            rgba_image,
            mark,
            horizontal_offset=5,
            vertical_offset=10,
            horizontal_justification='center',
            vertical_justification='center',
            orientation='ROTATE_90',
            method='tile',
            opacity=80,
        )

        assert isinstance(result, Image.Image)
        assert result.size == rgba_image.size
        assert calls['args'][0] == rgba_image.size
        assert calls['args'][-1] == 80
        assert calls['args'][5] == 'center'
        assert calls['args'][6] == 'center'
        assert calls['args'][7] == getattr(Image, 'ROTATE_90')
        assert calls['args'][8] == 80

    def test_palette_image_is_converted(self, monkeypatch, rgba_image):
        """Palette images should be converted via convert_safe_mode."""

        palette = rgba_image.convert('P')
        converted = rgba_image.copy()
        called = {}

        def fake_convert_safe_mode(image):
            called['image'] = image
            return converted

        def fake_generate_layer(*args, **kwargs):
            return Image.new('RGBA', converted.size, (0, 0, 0, 128))

        monkeypatch.setattr(watermark, 'convert_safe_mode', fake_convert_safe_mode)
        monkeypatch.setattr(watermark, 'generate_layer', fake_generate_layer)

        result = watermark.watermark(palette, Image.new('RGBA', (10, 10), (255, 255, 255, 128)))

        assert called['image'] is palette
        assert isinstance(result, Image.Image)
        assert result.size == converted.size


class TestWatermarkActionPil:
    """Test Action.pil wiring."""

    def test_action_pil_points_to_module_function(self):
        """The Action.pil staticmethod should reference watermark.watermark."""

        assert watermark.Action.pil is watermark.watermark
