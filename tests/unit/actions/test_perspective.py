"""Unit tests for phatch.actions.perspective module.

Tests the Perspective action (shear 2d or 3d transformations).

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
from phatch.actions import perspective as perspective_action


class TestPerspectiveAction:
    """Test the Perspective action class metadata."""

    def test_action_exists(self):
        """Perspective action class should exist."""
        assert hasattr(perspective_action, 'Action')
        assert perspective_action.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = perspective_action.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = perspective_action.Action()
        assert 'perspective' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(perspective_action.Action, 'pil')
        assert callable(perspective_action.Action.pil)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = perspective_action.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have transform and filter tags."""
        action = perspective_action.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower
        assert 'filter' in tags_lower


class TestPerspectiveConstants:
    """Test module-level constants."""

    def test_presets_constant_exists(self):
        """PRESETS constant should exist."""
        assert hasattr(perspective_action, 'PRESETS')
        assert isinstance(perspective_action.PRESETS, dict)

    def test_presets_has_options(self):
        """PRESETS should have multiple perspective options."""
        assert len(perspective_action.PRESETS) > 5

    def test_fields_constant_exists(self):
        """FIELDS constant should exist."""
        assert hasattr(perspective_action, 'FIELDS')
        assert isinstance(perspective_action.FIELDS, list)

    def test_fields_has_expected_entries(self):
        """FIELDS should contain expected field names."""
        assert 'Scale' in perspective_action.FIELDS
        assert 'Left Shear Angle' in perspective_action.FIELDS
        assert 'Top Shear Angle' in perspective_action.FIELDS

    def test_options_constant_exists(self):
        """OPTIONS constant should exist."""
        assert hasattr(perspective_action, 'OPTIONS')
        assert isinstance(perspective_action.OPTIONS, list)

    def test_preset_configurations_exist(self):
        """Preset configurations should be defined."""
        assert hasattr(perspective_action, 'TOP')
        assert hasattr(perspective_action, 'BOTTOM_STRETCHED')
        assert hasattr(perspective_action, 'LEFT')
        assert hasattr(perspective_action, 'RIGHT_STRETCHED')
        assert hasattr(perspective_action, 'TOP_LEFT')


class TestPerspectiveInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_projection_field(self):
        """interface should define Projection parameter."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('projection' in k.lower() for k in fields.keys())

    def test_interface_defines_scale_field(self):
        """interface should define Scale parameter."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('scale' in k.lower() for k in fields.keys())

    def test_interface_defines_shear_angle_fields(self):
        """interface should define shear angle parameters."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('left' in k.lower() and 'shear' in k.lower() and 'angle' in k.lower()
                   for k in fields.keys())
        assert any('top' in k.lower() and 'shear' in k.lower() and 'angle' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_background_fields(self):
        """interface should define background color and opacity."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('background' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())
        assert any('background' in k.lower() and 'opacity' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_transpose_field(self):
        """interface should define Transpose parameter."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('transpose' in k.lower() for k in fields.keys())

    def test_interface_defines_autocrop_field(self):
        """interface should define Auto Crop parameter."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        assert any('auto' in k.lower() and 'crop' in k.lower()
                   for k in fields.keys())

    def test_interface_has_multiple_fields(self):
        """Perspective should have many parameters."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)

        # Should have at least 10 fields
        assert len(fields) >= 10


class TestPerspectiveFunction:
    """Test the perspective() PIL function."""

    def test_perspective_function_exists(self):
        """perspective function should exist."""
        assert hasattr(perspective_action, 'perspective')
        assert callable(perspective_action.perspective)

    def test_perspective_basic(self, rgb_image):
        """Apply basic perspective transformation."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_scale(self, rgb_image):
        """Apply perspective with scaling."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=0.5, height=0.5, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_skew(self, rgb_image):
        """Apply perspective with skew."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=5, skew_y=5,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_background_color(self, rgb_image):
        """Apply perspective with background color."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#FF0000', opacity=100,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)
        # Result mode depends on fill_background_color implementation
        assert result.mode in ['RGB', 'RGBA']

    def test_perspective_with_opacity(self, rgb_image):
        """Apply perspective with background opacity."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=50,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_crop(self, rgb_image):
        """Apply perspective with auto crop."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=True, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_different_resample_modes(self, rgb_image):
        """Apply perspective with different resample modes."""
        perspective_action.init()

        resample_modes = [Image.NEAREST, Image.BILINEAR, Image.BICUBIC]

        for mode in resample_modes:
            result = perspective_action.perspective(
                rgb_image,
                width=1.0, height=1.0, skew_x=0, skew_y=0,
                offset_x=0, offset_y=0, left=0, top=0,
                back_color='#000000', opacity=0,
                resample=mode, crop=False, transpose='NONE'
            )

            assert isinstance(result, Image.Image)


class TestPerspectiveTranspose:
    """Test transpose functionality."""

    def test_perspective_with_flip_left_right(self, rgb_image):
        """Apply perspective with FLIP_LEFT_RIGHT transpose."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='FLIP_LEFT_RIGHT'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_flip_top_bottom(self, rgb_image):
        """Apply perspective with FLIP_TOP_BOTTOM transpose."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='FLIP_TOP_BOTTOM'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_rotate_90(self, rgb_image):
        """Apply perspective with ROTATE_90 transpose."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='ROTATE_90'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_rotate_180(self, rgb_image):
        """Apply perspective with ROTATE_180 transpose."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='ROTATE_180'
        )

        assert isinstance(result, Image.Image)


class TestGetRelevantFieldLabels:
    """Test the get_relevant_field_labels() method."""

    def test_get_relevant_field_labels_method_exists(self):
        """get_relevant_field_labels method should exist."""
        action = perspective_action.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_returns_list(self):
        """get_relevant_field_labels should return list."""
        action = perspective_action.Action()
        labels = action.get_relevant_field_labels()
        assert isinstance(labels, list)

    def test_get_relevant_field_labels_includes_common_fields(self):
        """get_relevant_field_labels should include common fields."""
        action = perspective_action.Action()
        labels = action.get_relevant_field_labels()

        assert 'Projection' in labels
        assert 'Background Color' in labels
        assert 'Background Opacity' in labels


class TestValuesMethod:
    """Test the values() method."""

    def test_values_method_exists(self):
        """values method should exist."""
        action = perspective_action.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_values_returns_dict(self):
        """values method should return dictionary."""
        action = perspective_action.Action()

        info = {'size': (100, 100), 'dpi': 72}
        result = action.values(info)

        assert isinstance(result, dict)

    def test_values_includes_expected_keys(self):
        """values should include expected transformation parameters."""
        action = perspective_action.Action()

        info = {'size': (100, 100), 'dpi': 72}
        result = action.values(info)

        assert 'width' in result
        assert 'height' in result
        assert 'skew_x' in result
        assert 'skew_y' in result
        assert 'left' in result
        assert 'top' in result
        assert 'back_color' in result
        assert 'opacity' in result
        assert 'resample' in result
        assert 'crop' in result
        assert 'transpose' in result


class TestPerspectiveEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_perspective_rgba_image(self, rgba_image):
        """Apply perspective on RGBA image."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgba_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_grayscale_image(self, grayscale_image):
        """Apply perspective on grayscale image."""
        perspective_action.init()

        result = perspective_action.perspective(
            grayscale_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_small_image(self, small_image):
        """Apply perspective on small image."""
        perspective_action.init()

        result = perspective_action.perspective(
            small_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_zero_width(self, rgb_image):
        """Apply perspective with zero width (identity transform)."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=0, height=1.0, skew_x=0, skew_y=0,
            offset_x=0, offset_y=0, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)

    def test_perspective_with_offsets(self, rgb_image):
        """Apply perspective with offset values."""
        perspective_action.init()

        result = perspective_action.perspective(
            rgb_image,
            width=1.0, height=1.0, skew_x=0, skew_y=0,
            offset_x=10, offset_y=10, left=0, top=0,
            back_color='#000000', opacity=0,
            resample=Image.NEAREST, crop=False, transpose='NONE'
        )

        assert isinstance(result, Image.Image)


class TestPerspectiveIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = perspective_action.Action()
        assert action is not None

    def test_action_pil_points_to_perspective(self):
        """Action.pil should point to perspective function."""
        assert perspective_action.Action.pil == perspective_action.perspective

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        perspective_action.init()
        assert hasattr(perspective_action, 'Image')

    def test_init_loads_math(self):
        """init() should load math module."""
        perspective_action.init()
        assert hasattr(perspective_action, 'math')
        assert hasattr(perspective_action, 'r')  # radians function

    def test_init_loads_imtools(self):
        """init() should load imtools module."""
        perspective_action.init()
        assert hasattr(perspective_action, 'imtools')

    def test_init_loads_color_functions(self):
        """init() should load color conversion functions."""
        perspective_action.init()
        assert hasattr(perspective_action, 'HTMLColorToRGBA')

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = perspective_action.Action()
        fields = {}
        action.interface(fields)
        # Should have many fields
        assert len(fields) >= 10

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = perspective_action.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'transform' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_shear(self):
        """Action documentation mentions shear."""
        action = perspective_action.Action()
        doc_lower = action.__doc__.lower()
        assert 'shear' in doc_lower
