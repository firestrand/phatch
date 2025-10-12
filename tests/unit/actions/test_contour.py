"""Unit tests for phatch.actions.contour module.

Tests the Contour action (draw contour around image edges).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import contour
from PIL import Image


class TestContourAction:
    """Test the Contour action class metadata."""

    def test_action_exists(self):
        """Contour action class should exist."""
        assert hasattr(contour, 'Action')
        assert contour.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = contour.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = contour.Action()
        assert 'contour' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(contour.Action, 'init')
        assert callable(contour.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(contour.Action, 'pil')
        assert callable(contour.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = contour.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter tag."""
        action = contour.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower


class TestContourInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_six_fields(self):
        """Contour should have six parameters."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 6

    def test_interface_defines_size_field(self):
        """interface should define Size parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('size' in k.lower() for k in fields.keys())

    def test_interface_defines_offset_field(self):
        """interface should define Offset parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('offset' in k.lower() for k in fields.keys())

    def test_interface_defines_contour_color_field(self):
        """interface should define Contour Color parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('contour' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_fill_color_field(self):
        """interface should define Fill Color parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('fill' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('opacity' in k.lower() for k in fields.keys())

    def test_interface_defines_include_image_field(self):
        """interface should define Include image parameter."""
        action = contour.Action()
        fields = {}
        action.interface(fields)

        assert any('include' in k.lower() and 'image' in k.lower()
                   for k in fields.keys())


class TestContourInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(contour, 'init')
        assert callable(contour.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        contour.init()

        # Should have loaded Image, ImageOps, imtools
        assert hasattr(contour, 'Image')
        assert hasattr(contour, 'ImageOps')
        assert hasattr(contour, 'imtools')

    def test_init_loads_color_functions(self):
        """init should load HTMLColorToRGBA."""
        contour.init()

        assert hasattr(contour, 'HTMLColorToRGBA')


class TestPutBorderFunction:
    """Test the put_border() function for non-transparent images."""

    def test_put_border_function_exists(self):
        """put_border function should exist."""
        assert hasattr(contour, 'put_border')
        assert callable(contour.put_border)

    def test_put_border_returns_image(self):
        """put_border should return Image object."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert isinstance(result, Image.Image)

    def test_put_border_adds_border_size(self):
        """put_border should increase image size by border."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 2px border on all sides = +4px to width and height
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert result.size == (104, 104)

    def test_put_border_with_offset(self):
        """put_border should handle offset parameter."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 2px border + 3px offset = +10px to width and height
        result = contour.put_border(image, 2, 3, '#000000', '#FFFFFF', 100, True)

        assert result.size == (110, 110)

    def test_put_border_converts_to_rgba(self):
        """put_border should convert result to RGBA."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert result.mode == 'RGBA'

    def test_put_border_with_opacity_less_than_100(self):
        """put_border should apply opacity < 100."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        # 50% opacity - should not raise TypeError (Pillow 10+ bug fix)
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 50, True)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_put_border_without_include_image(self):
        """put_border should create contour-only image when include_image=False."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 100, False)

        # Should be RGBA even without original image
        assert result.mode == 'RGBA'


class TestPutContourFunction:
    """Test the put_contour() function for transparent images."""

    def test_put_contour_function_exists(self):
        """put_contour function should exist."""
        assert hasattr(contour, 'put_contour')
        assert callable(contour.put_contour)

    def test_put_contour_returns_image(self):
        """put_contour should return Image object."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 255))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert isinstance(result, Image.Image)

    def test_put_contour_with_rgb_calls_put_border(self):
        """put_contour should call put_border for non-transparent images."""
        contour.init()

        # RGB image has no transparency
        image = Image.new('RGB', (100, 100), 'red')
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        # Should increase size like put_border does
        assert result.size == (104, 104)

    def test_put_contour_with_rgba_image(self):
        """put_contour should handle RGBA images with transparency."""
        contour.init()

        # RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_put_contour_resizes_mask_with_lanczos(self):
        """put_contour should use LANCZOS/ANTIALIAS for mask resize."""
        contour.init()

        # Create RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))

        # This should not raise AttributeError about ANTIALIAS
        # (Pillow 10+ compatibility fix)
        result = contour.put_contour(image, 5, 5, '#000000', '#FFFFFF', 100, True)

        assert isinstance(result, Image.Image)

    def test_put_contour_applies_opacity_as_integer(self):
        """put_contour should convert opacity to integer (Pillow 10+ fix)."""
        contour.init()

        # RGBA image with transparency
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))

        # 50% opacity - should not raise TypeError
        # (Pillow 10+ bug fix for float to int conversion)
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 50, True)

        assert isinstance(result, Image.Image)
        assert result.mode == 'RGBA'

    def test_put_contour_with_size_parameter(self):
        """put_contour should handle size parameter."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))

        # 5px contour
        result = contour.put_contour(image, 5, 0, '#000000', '#FFFFFF', 100, True)

        # Size should increase by 2*5 = 10px on each dimension
        assert result.size == (110, 110)

    def test_put_contour_with_offset_parameter(self):
        """put_contour should handle offset parameter."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))

        # 2px contour + 3px offset
        result = contour.put_contour(image, 2, 3, '#000000', '#FFFFFF', 100, True)

        # Size should increase by 2*(2+3) = 10px on each dimension
        assert result.size == (110, 110)

    def test_put_contour_without_include_image(self):
        """put_contour should create contour-only when include_image=False."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, False)

        # Should still be RGBA
        assert result.mode == 'RGBA'


class TestContourEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_put_contour_with_zero_size(self):
        """put_contour should handle size=0 (no contour)."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = contour.put_contour(image, 0, 0, '#000000', '#FFFFFF', 100, True)

        # With 0 size, image size should stay the same
        assert result.size == (100, 100)

    def test_put_contour_with_zero_opacity(self):
        """put_contour should handle 0% opacity."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 0, True)

        assert isinstance(result, Image.Image)

    def test_put_contour_with_full_opacity(self):
        """put_contour should handle 100% opacity."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        assert isinstance(result, Image.Image)

    def test_put_contour_with_small_image(self):
        """put_contour should handle small images."""
        contour.init()

        image = Image.new('RGBA', (10, 10), (255, 0, 0, 128))
        result = contour.put_contour(image, 2, 0, '#000000', '#FFFFFF', 100, True)

        # Should add contour even to small image
        assert result.size == (14, 14)

    def test_put_contour_with_large_size(self):
        """put_contour should handle large contour size."""
        contour.init()

        image = Image.new('RGBA', (100, 100), (255, 0, 0, 128))
        # Large 20px contour
        result = contour.put_contour(image, 20, 0, '#000000', '#FFFFFF', 100, True)

        assert result.size == (140, 140)

    def test_put_border_with_zero_opacity(self):
        """put_border should handle 0% opacity."""
        contour.init()

        image = Image.new('RGB', (100, 100), 'red')
        result = contour.put_border(image, 2, 0, '#000000', '#FFFFFF', 0, True)

        assert isinstance(result, Image.Image)


class TestContourIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = contour.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = contour.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 6

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = contour.Action()
        assert action.author == 'Nadia Alramli'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_contour(self):
        """Action documentation mentions contour or edges."""
        action = contour.Action()
        doc_lower = action.__doc__.lower()
        assert 'contour' in doc_lower or 'edge' in doc_lower

    def test_action_pil_is_put_contour(self):
        """Action.pil should be put_contour function."""
        assert contour.Action.pil == contour.put_contour
