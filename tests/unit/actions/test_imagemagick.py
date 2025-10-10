"""Unit tests for phatch.actions.imagemagick module.

Tests the Imagemagick action (various image effects using ImageMagick).

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

from phatch.actions import imagemagick


class TestImagemagickAction:
    """Test the Imagemagick action class metadata."""

    def test_action_exists(self):
        """Imagemagick action class should exist."""
        assert hasattr(imagemagick, 'Action')
        assert imagemagick.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = imagemagick.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = imagemagick.Action()
        assert 'imagemagick' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init method."""
        action = imagemagick.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = imagemagick.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = imagemagick.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have filter and plugin tags."""
        action = imagemagick.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower
        assert 'plugin' in tags_lower

    def test_action_has_tags_hidden(self):
        """Action should have tags_hidden with ACTIONS."""
        action = imagemagick.Action()
        assert hasattr(action, 'tags_hidden')
        assert action.tags_hidden == imagemagick.ACTIONS


class TestImagemagickCommands:
    """Test COMMANDS dictionary."""

    def test_commands_dict_exists(self):
        """COMMANDS dictionary should exist."""
        assert hasattr(imagemagick, 'COMMANDS')
        assert isinstance(imagemagick.COMMANDS, dict)

    def test_commands_has_blur(self):
        """COMMANDS should include Blur."""
        assert 'Blur' in imagemagick.COMMANDS

    def test_commands_has_polaroid(self):
        """COMMANDS should include Polaroid."""
        assert 'Polaroid' in imagemagick.COMMANDS

    def test_commands_has_shadow(self):
        """COMMANDS should include Shadow."""
        assert 'Shadow' in imagemagick.COMMANDS

    def test_commands_has_sharpen(self):
        """COMMANDS should include Sharpen."""
        assert 'Sharpen' in imagemagick.COMMANDS

    def test_commands_has_wave(self):
        """COMMANDS should include Wave."""
        assert 'Wave' in imagemagick.COMMANDS

    def test_commands_has_charcoal(self):
        """COMMANDS should include Charcoal."""
        assert 'Charcoal' in imagemagick.COMMANDS

    def test_commands_has_paint(self):
        """COMMANDS should include Paint."""
        assert 'Paint' in imagemagick.COMMANDS

    def test_commands_has_unsharp(self):
        """COMMANDS should include Unsharp."""
        assert 'Unsharp' in imagemagick.COMMANDS

    def test_commands_has_13_entries(self):
        """COMMANDS should have 13 different effects."""
        assert len(imagemagick.COMMANDS) == 13

    def test_commands_values_are_strings(self):
        """COMMANDS values should be command strings."""
        for cmd in imagemagick.COMMANDS.values():
            assert isinstance(cmd, str)
            # Commands should contain convert and file references
            assert 'convert' in cmd or '%(convert)s' in cmd


class TestImagemagickActions:
    """Test ACTIONS list."""

    def test_actions_list_exists(self):
        """ACTIONS list should exist."""
        assert hasattr(imagemagick, 'ACTIONS')
        assert isinstance(imagemagick.ACTIONS, list)

    def test_actions_list_sorted(self):
        """ACTIONS list should be sorted."""
        assert imagemagick.ACTIONS == sorted(imagemagick.ACTIONS)

    def test_actions_matches_commands_keys(self):
        """ACTIONS should match COMMANDS keys."""
        assert set(imagemagick.ACTIONS) == set(imagemagick.COMMANDS.keys())


class TestImagemagickInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_action_field(self):
        """interface should define Action parameter."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)

        assert any('action' in k.lower() for k in fields.keys())

    def test_interface_defines_color_fields(self):
        """interface should define Color parameters."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)

        # Should have color-related fields
        has_color = any('color' in k.lower() for k in fields.keys())
        assert has_color

    def test_interface_defines_blur_fields(self):
        """interface should define Blur parameters."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)

        has_blur_radius = any('blur' in k.lower() and 'radius' in k.lower()
                              for k in fields.keys())
        has_blur_sigma = any('blur' in k.lower() and 'sigma' in k.lower()
                             for k in fields.keys())
        assert has_blur_radius
        assert has_blur_sigma

    def test_interface_defines_shadow_fields(self):
        """interface should define Shadow parameters."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)

        has_offset = any('offset' in k.lower() for k in fields.keys())
        assert has_offset

    def test_interface_defines_wave_fields(self):
        """interface should define Wave parameters."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)

        has_wave = any('wave' in k.lower() for k in fields.keys())
        assert has_wave


class TestImagemagickInit:
    """Test the init() method."""

    def test_init_method_exists(self):
        """init method should exist."""
        action = imagemagick.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)

    @patch('phatch.actions.imagemagick.Action.find_exe')
    def test_init_searches_for_convert(self, mock_find_exe):
        """init should search for convert executable."""
        mock_find_exe.return_value = '/usr/bin/convert'
        action = imagemagick.Action()
        action.init()

        # Should call find_exe for convert
        mock_find_exe.assert_called_once_with('convert', 'Imagemagick')


class TestImagemagickApply:
    """Test the apply() method."""

    def test_apply_method_signature(self):
        """apply should have correct signature."""
        action = imagemagick.Action()
        assert callable(action.apply)

    def test_get_relevant_field_labels_exists(self):
        """get_relevant_field_labels method should exist."""
        action = imagemagick.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_get_relevant_field_labels_returns_list(self):
        """get_relevant_field_labels should return list."""
        action = imagemagick.Action()
        # Mock the get_field_string to return a valid action
        with patch.object(action, 'get_field_string', return_value='Blur'):
            result = action.get_relevant_field_labels()
            assert isinstance(result, list)
            assert 'Action' in result

    def test_get_relevant_field_labels_for_blur(self):
        """get_relevant_field_labels should return Blur fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Blur'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Blur Radius' in result
            assert 'Blur Sigma' in result

    def test_get_relevant_field_labels_for_polaroid(self):
        """get_relevant_field_labels should return Polaroid fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Polaroid'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Border Color' in result
            assert 'Shadow Color' in result
            assert 'Caption' in result

    def test_get_relevant_field_labels_for_shadow(self):
        """get_relevant_field_labels should return Shadow fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Shadow'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Horizontal Offset' in result
            assert 'Vertical Offset' in result
            assert 'Shadow Color' in result

    def test_get_relevant_field_labels_for_wave(self):
        """get_relevant_field_labels should return Wave fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Wave'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Wave Height' in result
            assert 'Wave Length' in result


class TestImagemagickIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = imagemagick.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = imagemagick.Action()
        fields = {}
        action.interface(fields)
        # Should define many fields for all the different effects
        assert len(fields) > 15

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = imagemagick.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]
        assert 'plugin' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_effects(self):
        """Action documentation mentions effects."""
        action = imagemagick.Action()
        doc_lower = action.__doc__.lower()
        # Should mention some of the effects
        assert any(word in doc_lower for word in ['blur', 'polaroid', 'shadow', 'unsharp'])


class TestImagemagickEdgeCases:
    """Test edge cases and special behavior."""

    def test_get_relevant_field_labels_for_motion_blur(self):
        """get_relevant_field_labels should return Motion Blur fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Motion Blur'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Blur Radius' in result
            assert 'Blur Sigma' in result
            assert 'Blur Angle' in result

    def test_get_relevant_field_labels_for_pencil_sketch(self):
        """get_relevant_field_labels should return Pencil Sketch fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Pencil Sketch'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Sketch Radius' in result
            assert 'Sketch Sigma' in result
            assert 'Sketch Angle' in result

    def test_get_relevant_field_labels_for_sharpen(self):
        """get_relevant_field_labels should return Sharpen fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Sharpen'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Sharpen Radius' in result
            assert 'Sharpen Sigma' in result

    def test_get_relevant_field_labels_for_unsharp(self):
        """get_relevant_field_labels should return Unsharp fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Unsharp'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Unsharp Radius' in result
            assert 'Unsharp Sigma' in result

    def test_get_relevant_field_labels_for_charcoal(self):
        """get_relevant_field_labels should return Charcoal fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Charcoal'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Charcoal Radius' in result

    def test_get_relevant_field_labels_for_paint(self):
        """get_relevant_field_labels should return Paint fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Paint'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Paint Radius' in result

    def test_get_relevant_field_labels_for_sigmoidal_contrast(self):
        """get_relevant_field_labels should return Sigmoidal Contrast fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Sigmoidal Contrast'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Contrast Factor' in result
            assert 'Contrast Treshold' in result

    def test_get_relevant_field_labels_for_bullet(self):
        """get_relevant_field_labels should return Bullet fields."""
        action = imagemagick.Action()
        with patch.object(action, 'get_field_string', return_value='Bullet'):
            result = action.get_relevant_field_labels()
            assert 'Action' in result
            assert 'Color' in result
