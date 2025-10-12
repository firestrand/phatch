"""Unit tests for phatch.actions.geek module.

Tests the Geek action (execute external commands).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import geek


class TestGeekAction:
    """Test the Geek action class metadata."""

    def test_action_exists(self):
        """Geek action class should exist."""
        assert hasattr(geek, 'Action')
        assert geek.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = geek.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = geek.Action()
        assert 'geek' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init method."""
        action = geek.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = geek.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = geek.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have plugin tag."""
        action = geek.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'plugin' in tags_lower


class TestGeekInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_five_fields(self):
        """Geek should have five parameters."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 5

    def test_interface_defines_command_field(self):
        """interface should define Command parameter."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert any('command' in k.lower() for k in fields.keys())

    def test_interface_defines_verify_program_field(self):
        """interface should define Verify Program parameter."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert any('verify' in k.lower() and 'program' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_verify_input_field(self):
        """interface should define Verify Input parameter."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert any('verify' in k.lower() and 'input' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_verify_output_field(self):
        """interface should define Verify Output parameter."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert any('verify' in k.lower() and 'output' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_allow_as_last_action_field(self):
        """interface should define Allow as last action parameter."""
        action = geek.Action()
        fields = {}
        action.interface(fields)

        assert any('allow' in k.lower() and 'last' in k.lower()
                   for k in fields.keys())


class TestGeekInit:
    """Test the init() method."""

    def test_init_method_exists(self):
        """init method should exist."""
        action = geek.Action()
        assert hasattr(action, 'init')
        assert callable(action.init)


class TestGeekApply:
    """Test the apply() method."""

    def test_apply_method_signature(self):
        """apply should have correct signature."""
        action = geek.Action()
        assert callable(action.apply)

    def test_get_relevant_field_labels_exists(self):
        """get_relevant_field_labels method should exist."""
        action = geek.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_is_overwrite_existing_images_forced_exists(self):
        """is_overwrite_existing_images_forced method should exist."""
        action = geek.Action()
        assert hasattr(action, 'is_overwrite_existing_images_forced')
        assert callable(action.is_overwrite_existing_images_forced)

    def test_is_overwrite_existing_images_forced_returns_false(self):
        """is_overwrite_existing_images_forced should return False."""
        action = geek.Action()
        assert action.is_overwrite_existing_images_forced() is False


class TestGeekConstants:
    """Test module-level constants."""

    def test_commands_constant_exists(self):
        """COMMANDS constant should exist."""
        assert hasattr(geek, 'COMMANDS')

    def test_commands_is_list(self):
        """COMMANDS should be a list."""
        assert isinstance(geek.COMMANDS, list)

    def test_commands_has_entries(self):
        """COMMANDS should have at least one entry."""
        assert len(geek.COMMANDS) > 0

    def test_commands_contains_strings(self):
        """COMMANDS should contain strings."""
        for command in geek.COMMANDS:
            assert isinstance(command, str)


class TestGeekIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = geek.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = geek.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 5

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = geek.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        assert 'plugin' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_command(self):
        """Action documentation mentions command or execute."""
        action = geek.Action()
        doc_lower = action.__doc__.lower()
        assert 'command' in doc_lower or 'execute' in doc_lower

    def test_action_class_docstring(self):
        """Action class should have docstring."""
        # The __doc__ is reassigned to translated text
        assert geek.Action.__doc__ is not None
        assert 'execute' in geek.Action.__doc__.lower() or \
               'command' in geek.Action.__doc__.lower()
