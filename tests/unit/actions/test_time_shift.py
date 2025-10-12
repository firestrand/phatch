"""Unit tests for phatch.actions.time_shift module.

Tests the Time Shift action (shift EXIF/file timestamps).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins
from datetime import datetime

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import time_shift


class TestTimeShiftAction:
    """Test the Time Shift action class metadata."""

    def test_action_exists(self):
        """Time Shift action class should exist."""
        assert hasattr(time_shift, 'Action')
        assert time_shift.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = time_shift.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = time_shift.Action()
        assert 'time' in action.label.lower() or 'shift' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod."""
        assert hasattr(time_shift.Action, 'init')
        assert callable(time_shift.Action.init)

    def test_action_has_apply_method(self):
        """Action should have apply method (not pil)."""
        action = time_shift.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = time_shift.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_tags(self):
        """Action should have metadata tag."""
        action = time_shift.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'metadata' in tags_lower


class TestTimeShiftInterface:
    """Test the interface() method defining parameters."""

    def test_interface_has_eight_fields(self):
        """Time Shift should have eight parameters."""
        action = time_shift.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 8

    def test_interface_defines_change_field(self):
        """interface should define Change parameter."""
        action = time_shift.Action()
        fields = {}
        action.interface(fields)

        assert any('change' in k.lower() for k in fields.keys())

    def test_interface_defines_use_exif_field(self):
        """interface should define Use exif datetime parameter."""
        action = time_shift.Action()
        fields = {}
        action.interface(fields)

        assert any('exif' in k.lower() and 'datetime' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_time_fields(self):
        """interface should define time adjustment fields."""
        action = time_shift.Action()
        fields = {}
        action.interface(fields)

        # Should have seconds, minutes, hours, days, months, years
        has_seconds = any('second' in k.lower() for k in fields.keys())
        has_minutes = any('minute' in k.lower() for k in fields.keys())
        has_hours = any('hour' in k.lower() for k in fields.keys())
        has_days = any('day' in k.lower() for k in fields.keys())
        has_months = any('month' in k.lower() for k in fields.keys())
        has_years = any('year' in k.lower() for k in fields.keys())

        assert all([has_seconds, has_minutes, has_hours,
                   has_days, has_months, has_years])


class TestTimeShiftInit:
    """Test the init() function."""

    def test_init_function_exists(self):
        """init function should exist."""
        assert hasattr(time_shift, 'init')
        assert callable(time_shift.init)

    def test_init_loads_relativedelta(self):
        """init should load relativedelta."""
        time_shift.init()

        # Should have loaded relativedelta
        assert hasattr(time_shift, 'relativedelta')


class TestGetDateFunction:
    """Test the get_date() helper function."""

    def test_get_date_function_exists(self):
        """get_date function should exist."""
        assert hasattr(time_shift, 'get_date')
        assert callable(time_shift.get_date)

    def test_get_date_creates_datetime(self):
        """get_date should create datetime from info dict."""
        info = {
            'year': 2023,
            'month': 6,
            'day': 15,
            'hour': 14,
            'minute': 30,
            'second': 45
        }

        result = time_shift.get_date(info)

        assert isinstance(result, datetime)
        assert result.year == 2023
        assert result.month == 6
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45


class TestTimeShiftOptions:
    """Test the OPTIONS constant."""

    def test_options_exist(self):
        """OPTIONS constant should exist."""
        assert hasattr(time_shift, 'OPTIONS')
        assert isinstance(time_shift.OPTIONS, list)

    def test_options_has_three_choices(self):
        """OPTIONS should have three time shift modes."""
        assert len(time_shift.OPTIONS) == 3


class TestTimeShiftApply:
    """Test the apply() method."""

    def test_apply_method_signature(self):
        """apply should have correct signature."""
        action = time_shift.Action()
        # Should accept photo, setting, cache parameters
        assert callable(action.apply)

    def test_construct_date_delta_method_exists(self):
        """_construct_date_delta helper should exist."""
        action = time_shift.Action()
        assert hasattr(action, '_construct_date_delta')
        assert callable(action._construct_date_delta)

    def test_get_relevant_field_labels_exists(self):
        """get_relevant_field_labels method should exist."""
        action = time_shift.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)


class TestTimeShiftEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_get_date_with_minimum_values(self):
        """get_date should handle minimum date values."""
        info = {
            'year': 1970,
            'month': 1,
            'day': 1,
            'hour': 0,
            'minute': 0,
            'second': 0
        }

        result = time_shift.get_date(info)

        assert isinstance(result, datetime)
        assert result.year == 1970

    def test_get_date_with_maximum_reasonable_values(self):
        """get_date should handle large date values."""
        info = {
            'year': 2037,
            'month': 12,
            'day': 31,
            'hour': 23,
            'minute': 59,
            'second': 59
        }

        result = time_shift.get_date(info)

        assert isinstance(result, datetime)
        assert result.year == 2037
        assert result.month == 12


class TestTimeShiftIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = time_shift.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = time_shift.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 8

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = time_shift.Action()
        assert action.author == 'Juho Vepsäläinen'
        assert action.version == '0.2'
        assert 'metadata' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_time(self):
        """Action documentation mentions time or shift."""
        action = time_shift.Action()
        doc_lower = action.__doc__.lower()
        assert 'time' in doc_lower or 'shift' in doc_lower

    def test_action_has_metadata_attribute(self):
        """Action should declare metadata fields it uses."""
        action = time_shift.Action()
        assert hasattr(action, 'metadata')
        assert isinstance(action.metadata, list)
        # Should list EXIF and date/time fields
        assert 'Exif_Image_DateTime' in action.metadata
