"""Unit tests for phatch.actions.grid module.

Tests the Grid action (make n x m matrix of image).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import Mock

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import grid
from PIL import Image


class TestGridAction:
    """Test the Grid action class metadata."""

    def test_action_exists(self):
        """Grid action class should exist."""
        assert hasattr(grid, 'Action')
        assert grid.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = grid.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = grid.Action()
        assert 'grid' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(grid.Action, 'init')
        assert callable(grid.Action.init)

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(grid.Action, 'pil')
        assert callable(grid.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = grid.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = grid.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_tags(self):
        """Action should have size and filter tags."""
        action = grid.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'size' in tags_lower or 'filter' in tags_lower

    def test_action_all_layers(self):
        """Action should process all layers."""
        assert grid.Action.all_layers is True

    def test_action_update_size(self):
        """Action should update size."""
        assert grid.Action.update_size is True


class TestGridConstants:
    """Test module-level constants."""

    def test_choices_constant_exists(self):
        """CHOICES constant should exist."""
        assert hasattr(grid, 'CHOICES')
        assert isinstance(grid.CHOICES, list)

    def test_zero_constant_exists(self):
        """ZERO constant should exist."""
        assert hasattr(grid, 'ZERO')
        assert isinstance(grid.ZERO, list)


class TestGridInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_seven_fields(self):
        """Grid should have seven parameters."""
        action = grid.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 7

    def test_interface_defines_columns_field(self):
        """interface should define Columns parameter."""
        action = grid.Action()
        fields = {}
        action.interface(fields)

        assert any('column' in k.lower() for k in fields.keys())

    def test_interface_defines_rows_field(self):
        """interface should define Rows parameter."""
        action = grid.Action()
        fields = {}
        action.interface(fields)

        assert any('row' in k.lower() for k in fields.keys())

    def test_interface_defines_scale_field(self):
        """interface should define Scale to Keep Size parameter."""
        action = grid.Action()
        fields = {}
        action.interface(fields)

        assert any('scale' in k.lower() for k in fields.keys())

    def test_interface_defines_line_fields(self):
        """interface should define line width and color fields."""
        action = grid.Action()
        fields = {}
        action.interface(fields)

        # Should have line width, color, opacity fields
        keys_lower = [k.lower() for k in fields.keys()]
        assert any('line' in k and 'width' in k for k in keys_lower)
        assert any('line' in k and 'color' in k for k in keys_lower)
        assert any('line' in k and 'opacity' in k for k in keys_lower)


class TestGetRelevantFieldLabels:
    """Test the get_relevant_field_labels() method."""

    def test_get_relevant_field_labels_method_exists(self):
        """get_relevant_field_labels method should exist."""
        action = grid.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_includes_line_color_when_nonzero(self):
        """Should include Line Color when line widths are nonzero."""
        action = grid.Action()
        action.get_field_string = Mock(side_effect=['5 px', '0'])

        labels = action.get_relevant_field_labels()
        assert 'Line Color' in labels
        assert 'Line Opacity' in labels

    def test_get_relevant_field_labels_excludes_line_color_when_zero(self):
        """Should exclude Line Color when line widths are zero."""
        action = grid.Action()
        action.get_field_string = Mock(side_effect=['0', '0'])

        labels = action.get_relevant_field_labels()
        assert 'Line Color' not in labels
        assert 'Line Opacity' not in labels


class TestGridInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(grid, 'init')
        assert callable(grid.init)

    def test_init_loads_pil_modules(self):
        """init should load PIL modules."""
        grid.init()

        # Should have loaded Image, ImageColor
        assert hasattr(grid, 'Image')
        assert hasattr(grid, 'ImageColor')
        assert hasattr(grid, 'imtools')
        assert hasattr(grid, 'HTMLColorToRGBA')


class TestMakeGridFunction:
    """Test the make_grid() function."""

    def test_make_grid_function_exists(self):
        """make_grid function should exist."""
        assert hasattr(grid, 'make_grid')
        assert callable(grid.make_grid)

    def test_make_grid_returns_unchanged_for_1x1_grid(self):
        """make_grid should return unchanged image for 1x1 grid."""
        grid.init()

        image = Image.new('RGB', (100, 100), 'red')

        result = grid.make_grid(image, (1, 1))

        assert result is image  # Same object

    def test_make_grid_creates_2x2_grid(self):
        """make_grid should create 2x2 grid."""
        grid.init()

        image = Image.new('RGB', (100, 100), 'red')

        result = grid.make_grid(image, (2, 2), scale=False)

        # Size should be 2x larger in both dimensions
        assert result.size == (200, 200)
        assert result.mode == 'RGB'

    def test_make_grid_creates_3x2_grid(self):
        """make_grid should create 3x2 grid."""
        grid.init()

        image = Image.new('RGB', (100, 100), 'red')

        result = grid.make_grid(image, (3, 2), scale=False)

        # Size should be 3x2
        assert result.size == (300, 200)

    def test_make_grid_with_line_width(self):
        """make_grid should include line widths."""
        grid.init()

        image = Image.new('RGB', (100, 100), 'red')

        # 2x2 grid with 10px line widths
        result = grid.make_grid(image, (2, 2), col_line_width=10,
                                row_line_width=10, scale=False)

        # Size should be: 2*(100+10) - 10 = 210
        assert result.size == (210, 210)

    def test_make_grid_with_scaling(self):
        """make_grid should scale down when scale=True."""
        grid.init()

        image = Image.new('RGB', (100, 100), 'red')

        # 2x2 grid with scaling
        result = grid.make_grid(image, (2, 2), scale=True)

        # With scaling, total pixels should be similar
        # sqrt(2*2) = 2, so each image is 50x50, total is 100x100
        assert result.size == (100, 100)

    def test_make_grid_preserves_mode(self):
        """make_grid should preserve image mode."""
        grid.init()

        # Test with RGBA
        image = Image.new('RGBA', (100, 100), (255, 0, 0, 255))

        result = grid.make_grid(image, (2, 2), scale=False)

        assert result.mode == 'RGBA'


class TestGridValues:
    """Test the values() method."""

    def test_values_method_exists(self):
        """values method should exist."""
        action = grid.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_values_returns_dict(self):
        """values should return dictionary."""
        action = grid.Action()
        action.get_field = Mock(side_effect=[2, 2, False, '#FFFFFF', 0])
        action.get_field_size = Mock(side_effect=[0, 0])

        info = {'size': (100, 100), 'dpi': 72}
        result = action.values(info)

        assert isinstance(result, dict)

    def test_values_includes_required_keys(self):
        """values should include required keys."""
        action = grid.Action()
        action.get_field = Mock(side_effect=[2, 2, False, '#FFFFFF', 0])
        action.get_field_size = Mock(side_effect=[0, 0])

        info = {'size': (100, 100), 'dpi': 72}
        result = action.values(info)

        assert 'old_size' in result
        assert 'grid' in result
        assert 'scale' in result
        assert 'col_line_width' in result
        assert 'row_line_width' in result
        assert 'line_color' in result
        assert 'line_opacity' in result


class TestGridIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = grid.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = grid.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 7

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = grid.Action()
        assert action.author == 'Pawel T. Jochym'
        assert action.version == '0.2'

    def test_action_docstring_mentions_grid(self):
        """Action documentation mentions grid or matrix."""
        action = grid.Action()
        doc_lower = action.__doc__.lower()
        assert 'grid' in doc_lower or 'matrix' in doc_lower
