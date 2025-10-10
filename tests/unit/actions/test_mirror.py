"""Unit tests for phatch.actions.mirror module.

Tests the Mirror action (symmetrical tile texture).

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
from phatch.actions import mirror


class TestMirrorAction:
    """Test the Mirror action class metadata."""

    def test_action_exists(self):
        """Mirror action class should exist."""
        assert hasattr(mirror, 'Action')
        assert mirror.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = mirror.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = mirror.Action()
        assert 'mirror' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(mirror.Action, 'pil')
        assert callable(mirror.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(mirror.Action, 'init')
        assert callable(mirror.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = mirror.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = mirror.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'filter' in tags_lower


class TestMirrorInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_direction_field(self):
        """interface should define Direction parameter."""
        action = mirror.Action()
        fields = {}
        action.interface(fields)

        # Should have Direction field
        assert any('direction' in k.lower() for k in fields.keys())

    def test_interface_direction_is_choice_field(self):
        """Direction field should be a ChoiceField."""
        action = mirror.Action()
        fields = {}
        action.interface(fields)

        # Get the Direction field
        direction_field = None
        for key, value in fields.items():
            if 'direction' in key.lower():
                direction_field = value
                break

        assert direction_field is not None
        assert type(direction_field).__name__ == 'ChoiceField'

    def test_interface_has_one_field(self):
        """Mirror should have one parameter."""
        action = mirror.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestMirrorConstants:
    """Test module-level constants."""

    def test_directions_constant_exists(self):
        """DIRECTIONS constant should exist."""
        assert hasattr(mirror, 'DIRECTIONS')
        assert isinstance(mirror.DIRECTIONS, list)

    def test_directions_has_three_values(self):
        """DIRECTIONS should have three values."""
        assert len(mirror.DIRECTIONS) == 3

    def test_both_constant_exists(self):
        """BOTH constant should exist."""
        assert hasattr(mirror, 'BOTH')

    def test_horizontal_constant_exists(self):
        """HORIZONTAL constant should exist."""
        assert hasattr(mirror, 'HORIZONTAL')

    def test_vertical_constant_exists(self):
        """VERTICAL constant should exist."""
        assert hasattr(mirror, 'VERTICAL')


class TestMirrorHelperFunctions:
    """Test helper functions."""

    def test_get_scales_function_exists(self):
        """get_scales function should exist."""
        assert hasattr(mirror, 'get_scales')
        assert callable(mirror.get_scales)

    def test_get_scales_both(self):
        """get_scales with Both direction returns 2x2."""
        x_scale, y_scale = mirror.get_scales(mirror.BOTH)
        assert x_scale == 2
        assert y_scale == 2

    def test_get_scales_horizontal(self):
        """get_scales with Horizontal direction returns 2x1."""
        x_scale, y_scale = mirror.get_scales(mirror.HORIZONTAL)
        assert x_scale == 2
        assert y_scale == 1

    def test_get_scales_vertical(self):
        """get_scales with Vertical direction returns 1x2."""
        x_scale, y_scale = mirror.get_scales(mirror.VERTICAL)
        assert x_scale == 1
        assert y_scale == 2

    def test_get_dimensions_function_exists(self):
        """get_dimensions function should exist."""
        assert hasattr(mirror, 'get_dimensions')
        assert callable(mirror.get_dimensions)

    def test_get_dimensions_both(self, rgb_image):
        """get_dimensions with Both direction doubles both dimensions."""
        width, height = mirror.get_dimensions(rgb_image, mirror.BOTH)
        assert width == 200
        assert height == 200

    def test_get_dimensions_horizontal(self, rgb_image):
        """get_dimensions with Horizontal direction doubles width only."""
        width, height = mirror.get_dimensions(rgb_image, mirror.HORIZONTAL)
        assert width == 200
        assert height == 100

    def test_get_dimensions_vertical(self, rgb_image):
        """get_dimensions with Vertical direction doubles height only."""
        width, height = mirror.get_dimensions(rgb_image, mirror.VERTICAL)
        assert width == 100
        assert height == 200


class TestMirrorTileFunction:
    """Test the tile() PIL function."""

    def test_tile_function_exists(self):
        """tile function should exist."""
        assert hasattr(mirror, 'tile')
        assert callable(mirror.tile)

    def test_tile_horizontal(self, rgb_image):
        """Tile horizontal creates left-right mirror."""
        mirror.init()

        result = mirror.tile(rgb_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        # Width should double, height same
        assert result.size == (200, 100)

    def test_tile_vertical(self, rgb_image):
        """Tile vertical creates top-bottom mirror."""
        mirror.init()

        result = mirror.tile(rgb_image, mirror.VERTICAL)

        assert isinstance(result, Image.Image)
        # Height should double, width same
        assert result.size == (100, 200)

    def test_tile_both(self, rgb_image):
        """Tile both creates 4-way mirror."""
        mirror.init()

        result = mirror.tile(rgb_image, mirror.BOTH)

        assert isinstance(result, Image.Image)
        # Both dimensions should double
        assert result.size == (200, 200)

    def test_tile_multicolor_horizontal(self, multicolor_image):
        """Tile multicolor image horizontally."""
        mirror.init()

        result = mirror.tile(multicolor_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 100)
        # Original top-left pixel should be preserved
        assert result.getpixel((0, 0)) == multicolor_image.getpixel((0, 0))

    def test_tile_multicolor_vertical(self, multicolor_image):
        """Tile multicolor image vertically."""
        mirror.init()

        result = mirror.tile(multicolor_image, mirror.VERTICAL)

        assert isinstance(result, Image.Image)
        assert result.size == (100, 200)

    def test_tile_multicolor_both(self, multicolor_image):
        """Tile multicolor image both directions."""
        mirror.init()

        result = mirror.tile(multicolor_image, mirror.BOTH)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)

    def test_tile_rgba_preserves_mode(self, rgba_image):
        """Tile RGBA image preserves mode."""
        mirror.init()

        result = mirror.tile(rgba_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        # Should preserve RGBA mode
        assert result.mode == 'RGBA'
        assert result.size == (200, 100)

    def test_tile_grayscale(self, grayscale_image):
        """Tile grayscale image."""
        mirror.init()

        result = mirror.tile(grayscale_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == (200, 100)

    def test_tile_gradient(self, gradient_image):
        """Tile gradient creates symmetrical pattern."""
        mirror.init()

        result = mirror.tile(gradient_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        assert result.size == (200, 100)


class TestMirrorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_tile_small_image_horizontal(self, small_image):
        """Tile works with small images."""
        mirror.init()

        result = mirror.tile(small_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        assert result.size == (20, 10)

    def test_tile_small_image_vertical(self, small_image):
        """Tile small image vertically."""
        mirror.init()

        result = mirror.tile(small_image, mirror.VERTICAL)

        assert isinstance(result, Image.Image)
        assert result.size == (10, 20)

    def test_tile_small_image_both(self, small_image):
        """Tile small image both directions."""
        mirror.init()

        result = mirror.tile(small_image, mirror.BOTH)

        assert isinstance(result, Image.Image)
        assert result.size == (20, 20)

    def test_tile_large_image(self, large_image):
        """Tile works with large images."""
        mirror.init()

        result = mirror.tile(large_image, mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        assert result.size == (1000, 500)

    def test_tile_twice_horizontal(self, rgb_image):
        """Tiling twice horizontally."""
        mirror.init()

        first = mirror.tile(rgb_image, mirror.HORIZONTAL)
        second = mirror.tile(first, mirror.HORIZONTAL)

        assert isinstance(second, Image.Image)
        # Should be 4x original width
        assert second.size == (400, 100)

    def test_tile_twice_vertical(self, rgb_image):
        """Tiling twice vertically."""
        mirror.init()

        first = mirror.tile(rgb_image, mirror.VERTICAL)
        second = mirror.tile(first, mirror.VERTICAL)

        assert isinstance(second, Image.Image)
        # Should be 4x original height
        assert second.size == (100, 400)

    def test_tile_mixed_directions(self, rgb_image):
        """Tile with different directions."""
        mirror.init()

        # First horizontal, then vertical
        first = mirror.tile(rgb_image, mirror.HORIZONTAL)
        second = mirror.tile(first, mirror.VERTICAL)

        assert isinstance(second, Image.Image)
        # Should be 2x width, 2x height
        assert second.size == (200, 200)


class TestMirrorIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_tile(self, multicolor_image):
        """Action.pil should call tile function."""
        mirror.init()

        result = mirror.Action.pil(multicolor_image, direction=mirror.HORIZONTAL)

        assert isinstance(result, Image.Image)
        # Verify it actually tiled
        assert result.size == (200, 100)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = mirror.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = mirror.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = mirror.Action()
        assert action.author == 'Juho Vepsäläinen'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'filter' in tags_lower

    def test_action_docstring_mentions_mirror(self):
        """Action documentation mentions mirror, tile, or symmetrical."""
        action = mirror.Action()
        doc_lower = action.__doc__.lower()
        assert 'mirror' in doc_lower or 'tile' in doc_lower or 'symmetrical' in doc_lower

    def test_action_pil_points_to_tile(self):
        """Action.pil should point to tile function."""
        # The action's pil staticmethod should be the tile function
        assert mirror.Action.pil == mirror.tile

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        mirror.init()
        # After init, Image should be available in the module
        assert hasattr(mirror, 'Image')
