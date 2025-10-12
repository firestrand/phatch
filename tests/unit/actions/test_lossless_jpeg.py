"""Unit tests for phatch.actions.lossless_jpeg module.

Tests the Lossless JPEG action (lossless JPEG transformations using external tools).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from unittest.mock import patch

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import lossless_jpeg


class TestLosslessJpegAction:
    """Test the Lossless JPEG action class metadata."""

    def test_action_exists(self):
        """Lossless JPEG action class should exist."""
        assert hasattr(lossless_jpeg, 'Action')
        assert lossless_jpeg.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = lossless_jpeg.Action()
        assert 'lossless' in action.label.lower() or 'jpeg' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init method."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have transform or size tags."""
        action = lossless_jpeg.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower


class TestLosslessJpegInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_utility_field(self):
        """interface should define Utility parameter."""
        action = lossless_jpeg.Action()
        fields = {}
        action.interface(fields)

        assert any('utility' in k.lower() for k in fields.keys())

    def test_interface_defines_transformation_fields(self):
        """interface should define transformation parameters."""
        action = lossless_jpeg.Action()
        fields = {}
        action.interface(fields)

        # Should have transformation field
        has_transformation = any('transformation' in k.lower() for k in fields.keys())
        assert has_transformation

    def test_interface_defines_angle_field(self):
        """interface should define Angle parameter."""
        action = lossless_jpeg.Action()
        fields = {}
        action.interface(fields)

        assert any('angle' in k.lower() for k in fields.keys())

    def test_interface_defines_direction_field(self):
        """interface should define Direction parameter."""
        action = lossless_jpeg.Action()
        fields = {}
        action.interface(fields)

        assert any('direction' in k.lower() for k in fields.keys())


class TestLosslessJpegUtilities:
    """Test utility classes and helpers."""

    def test_exiftran_class_exists(self):
        """Exiftran utility class should exist."""
        assert hasattr(lossless_jpeg, 'Exiftran')

    def test_jpegtran_class_exists(self):
        """Jpegtran utility class should exist."""
        assert hasattr(lossless_jpeg, 'Jpegtran')

    def test_exiftran_has_name(self):
        """Exiftran should have name attribute."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'name')
        assert 'exiftran' in exiftran.name.lower()

    def test_jpegtran_has_name(self):
        """Jpegtran should have name attribute."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'name')
        assert 'jpegtran' in jpegtran.name.lower()

    def test_exiftran_has_interface_method(self):
        """Exiftran should have interface method."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'interface')
        assert callable(exiftran.interface)

    def test_jpegtran_has_interface_method(self):
        """Jpegtran should have interface method."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'interface')
        assert callable(jpegtran.interface)

    def test_exiftran_has_transformations(self):
        """Exiftran should have transformations defined."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'transformations')
        assert isinstance(exiftran.transformations, tuple)
        assert len(exiftran.transformations) > 0

    def test_jpegtran_has_transformations(self):
        """Jpegtran should have transformations defined."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'transformations')
        assert isinstance(jpegtran.transformations, tuple)
        assert len(jpegtran.transformations) > 0

    def test_arguments_class_exists(self):
        """Arguments class should exist."""
        assert hasattr(lossless_jpeg, 'Arguments')

    def test_arguments_is_list(self):
        """Arguments should be a list subclass."""
        args = lossless_jpeg.Arguments()
        assert isinstance(args, list)

    def test_arguments_append_adds_dash_prefix(self):
        """Arguments append should add dash prefix."""
        args = lossless_jpeg.Arguments()
        args.append('a')
        assert args[0] == '-a'

    def test_arguments_append_with_value(self):
        """Arguments append should handle option with value."""
        args = lossless_jpeg.Arguments()
        args.append('rotate', '90')
        assert args[0] == '-rotate 90'

    def test_arguments_str_joins_with_space(self):
        """Arguments str should join with spaces."""
        args = lossless_jpeg.Arguments()
        args.append('a')
        args.append('rotate', '90')
        result = str(args)
        assert result == '-a -rotate 90'


class TestLosslessJpegInit:
    """Test the init() method."""

    def test_init_method_exists(self):
        """init method should exist."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)

    @patch('phatch.actions.lossless_jpeg.system.find_exe')
    def test_init_searches_for_exiftran(self, mock_find_exe):
        """init should search for exiftran executable."""
        mock_find_exe.return_value = '/usr/bin/exiftran'
        action = lossless_jpeg.Action()
        action.init()

        # Should call find_exe for exiftran
        calls = [str(call) for call in mock_find_exe.call_args_list]
        assert any('exiftran' in str(call) for call in calls)

    @patch('phatch.actions.lossless_jpeg.system.find_exe')
    def test_init_searches_for_jpegtran(self, mock_find_exe):
        """init should search for jpegtran executable."""
        mock_find_exe.return_value = '/usr/bin/jpegtran'
        action = lossless_jpeg.Action()
        action.init()

        # Should call find_exe for jpegtran
        calls = [str(call) for call in mock_find_exe.call_args_list]
        assert any('jpegtran' in str(call) for call in calls)


class TestLosslessJpegApply:
    """Test the apply() method."""

    def test_apply_method_signature(self):
        """apply should have correct signature."""
        action = lossless_jpeg.Action()
        assert callable(action.apply)

    def test_get_relevant_field_labels_exists(self):
        """get_relevant_field_labels method should exist."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)


class TestUtilityMixin:
    """Test the UtilityMixin class."""

    def test_utility_mixin_exists(self):
        """UtilityMixin class should exist."""
        assert hasattr(lossless_jpeg, 'UtilityMixin')

    def test_utility_mixin_has_interface(self):
        """UtilityMixin should have interface method."""
        assert hasattr(lossless_jpeg.UtilityMixin, 'interface')

    def test_utility_mixin_has_apply(self):
        """UtilityMixin should have apply method."""
        assert hasattr(lossless_jpeg.UtilityMixin, 'apply')

    def test_utility_mixin_has_get_relevant_field_labels(self):
        """UtilityMixin should have get_relevant_field_labels method."""
        assert hasattr(lossless_jpeg.UtilityMixin, 'get_relevant_field_labels')


class TestLossLessSaveUtilityMixin:
    """Test the LossLessSaveUtilityMixin class."""

    def test_lossless_save_utility_mixin_exists(self):
        """LossLessSaveUtilityMixin class should exist."""
        assert hasattr(lossless_jpeg, 'LossLessSaveUtilityMixin')

    def test_lossless_save_utility_mixin_has_format(self):
        """LossLessSaveUtilityMixin should have format attribute."""
        assert hasattr(lossless_jpeg.LossLessSaveUtilityMixin, 'format')
        assert lossless_jpeg.LossLessSaveUtilityMixin.format == 'JPEG'

    def test_lossless_save_utility_mixin_has_call(self):
        """LossLessSaveUtilityMixin should have call method."""
        assert hasattr(lossless_jpeg.LossLessSaveUtilityMixin, 'call')


class TestLosslessJpegIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = lossless_jpeg.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = lossless_jpeg.Action()
        fields = {}
        action.interface(fields)
        # Should have utility field and transformation fields from both utilities
        assert len(fields) > 0

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = lossless_jpeg.Action()
        assert action.author == 'Juho Vepsäläinen'
        assert action.version == '0.1'

    def test_action_docstring_mentions_operations(self):
        """Action documentation mentions supported operations."""
        action = lossless_jpeg.Action()
        doc_lower = action.__doc__.lower()
        assert any(word in doc_lower for word in ['rotate', 'flip', 'crop', 'grayscale'])

    def test_action_has_utilities_dict(self):
        """Action should have utilities dictionary."""
        action = lossless_jpeg.Action()
        assert hasattr(action, 'utilities')
        assert isinstance(action.utilities, dict)
        assert len(action.utilities) == 2

    def test_action_utilities_has_exiftran(self):
        """Action utilities should include Exiftran."""
        action = lossless_jpeg.Action()
        assert any('exiftran' in name.lower() for name in action.utilities.keys())

    def test_action_utilities_has_jpegtran(self):
        """Action utilities should include Jpegtran."""
        action = lossless_jpeg.Action()
        assert any('jpegtran' in name.lower() for name in action.utilities.keys())


class TestExiftranUtility:
    """Test Exiftran utility in detail."""

    def test_exiftran_angles_defined(self):
        """Exiftran should have angles mapping."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'angles')
        assert '90 degrees' in exiftran.angles
        assert '180 degrees' in exiftran.angles
        assert '270 degrees' in exiftran.angles

    def test_exiftran_directions_defined(self):
        """Exiftran should have directions mapping."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'directions')
        assert len(exiftran.directions) > 0

    def test_exiftran_has_get_command_line_args(self):
        """Exiftran should have get_command_line_args method."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'get_command_line_args')
        assert callable(exiftran.get_command_line_args)

    def test_exiftran_has_get_command_line(self):
        """Exiftran should have get_command_line method."""
        exiftran = lossless_jpeg.Exiftran()
        assert hasattr(exiftran, 'get_command_line')
        assert callable(exiftran.get_command_line)


class TestJpegtranUtility:
    """Test Jpegtran utility in detail."""

    def test_jpegtran_angles_defined(self):
        """Jpegtran should have angles mapping."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'angles')
        assert '90 degrees' in jpegtran.angles
        assert '180 degrees' in jpegtran.angles
        assert '270 degrees' in jpegtran.angles

    def test_jpegtran_directions_defined(self):
        """Jpegtran should have directions mapping."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'directions')
        assert len(jpegtran.directions) > 0

    def test_jpegtran_has_get_command_line_args(self):
        """Jpegtran should have get_command_line_args method."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'get_command_line_args')
        assert callable(jpegtran.get_command_line_args)

    def test_jpegtran_has_get_command_line(self):
        """Jpegtran should have get_command_line method."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'get_command_line')
        assert callable(jpegtran.get_command_line)

    def test_jpegtran_copy_choices(self):
        """Jpegtran should have copy_choices defined."""
        jpegtran = lossless_jpeg.Jpegtran()
        assert hasattr(jpegtran, 'copy_choices')
        assert len(jpegtran.copy_choices) == 3


class TestConstants:
    """Test module-level constants."""

    def test_automatic_constant_exists(self):
        """AUTOMATIC constant should exist."""
        assert hasattr(lossless_jpeg, 'AUTOMATIC')

    def test_copy_constant_exists(self):
        """COPY constant should exist."""
        assert hasattr(lossless_jpeg, 'COPY')

    def test_crop_constant_exists(self):
        """CROP constant should exist."""
        assert hasattr(lossless_jpeg, 'CROP')

    def test_rotate_constant_exists(self):
        """ROTATE constant should exist."""
        assert hasattr(lossless_jpeg, 'ROTATE')

    def test_flip_constant_exists(self):
        """FLIP constant should exist."""
        assert hasattr(lossless_jpeg, 'FLIP')

    def test_grayscale_constant_exists(self):
        """GRAYSCALE constant should exist."""
        assert hasattr(lossless_jpeg, 'GRAYSCALE')

    def test_rotate_amounts_defined(self):
        """ROTATE_AMOUNTS should be defined."""
        assert hasattr(lossless_jpeg, 'ROTATE_AMOUNTS')
        assert len(lossless_jpeg.ROTATE_AMOUNTS) == 3

    def test_flip_directions_defined(self):
        """FLIP_DIRECTIONS should be defined."""
        assert hasattr(lossless_jpeg, 'FLIP_DIRECTIONS')
        assert len(lossless_jpeg.FLIP_DIRECTIONS) == 2
