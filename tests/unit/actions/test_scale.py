"""Unit tests for phatch.actions.scale module.

Tests the Scale action (resize image).

Following TDD principles:
- Test behavior, not implementation
- Mock external dependencies when needed
- Each test has single responsibility
"""

import builtins

# Initialize translation system for tests
if not hasattr(builtins, '_'):
    builtins._ = lambda x: x

from phatch.actions import scale


class TestScaleAction:
    """Test the Scale action class metadata."""

    def test_action_exists(self):
        """Scale action class should exist."""
        assert hasattr(scale, 'Action')
        assert scale.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = scale.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = scale.Action()
        assert 'scale' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(scale.Action, 'init')
        assert callable(scale.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = scale.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_apply_method(self):
        """Action should have apply method (not pil)."""
        action = scale.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = scale.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower


class TestScaleInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_width_field(self):
        """interface should define Canvas Width parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Width field
        assert any('width' in k.lower() for k in fields.keys())

    def test_interface_defines_height_field(self):
        """interface should define Canvas Height parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Height field
        assert any('height' in k.lower() for k in fields.keys())

    def test_interface_defines_resolution_field(self):
        """interface should define Resolution parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Resolution field
        assert any('resolution' in k.lower() for k in fields.keys())

    def test_interface_defines_proportions_field(self):
        """interface should define Constrain Proportions parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Constrain Proportions field
        assert any('proportion' in k.lower() for k in fields.keys())

    def test_interface_defines_resample_field(self):
        """interface should define Resample Image parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Resample field
        assert any('resample' in k.lower() for k in fields.keys())

    def test_interface_defines_scale_down_field(self):
        """interface should define Scale Down Only parameter."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Should have Scale Down Only field
        assert any('down' in k.lower() for k in fields.keys())

    def test_interface_width_is_pixel_field(self):
        """Width field should be a PixelField."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Get the Width field
        width_field = None
        for key, value in fields.items():
            if 'width' in key.lower():
                width_field = value
                break

        assert width_field is not None
        assert type(width_field).__name__ == 'PixelField'

    def test_interface_proportions_is_boolean(self):
        """Constrain Proportions should be a BooleanField."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        # Get the Proportions field
        prop_field = None
        for key, value in fields.items():
            if 'proportion' in key.lower():
                prop_field = value
                break

        assert prop_field is not None
        assert type(prop_field).__name__ == 'BooleanField'

    def test_interface_has_six_fields(self):
        """Scale should have six parameters."""
        action = scale.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 6


class TestPreserveProportionsFunction:
    """Test the preserve_proportions helper function."""

    def test_preserve_proportions_function_exists(self):
        """preserve_proportions function should exist."""
        assert hasattr(scale, 'preserve_proportions')
        assert callable(scale.preserve_proportions)

    def test_preserve_proportions_width_limited(self):
        """When width scale is smaller, height is adjusted."""
        # Original: 100x200, Target: 50x100
        # Width scale: 0.5, Height scale: 0.5
        # Should keep both at 0.5 scale
        x1, y1 = scale.preserve_proportions(100, 200, 50, 100)
        assert x1 == 50
        assert y1 == 100

    def test_preserve_proportions_height_limited(self):
        """When height scale is smaller, width is adjusted."""
        # Original: 200x100, Target: 100x50
        # Width scale: 0.5, Height scale: 0.5
        # Should keep both at 0.5 scale
        x1, y1 = scale.preserve_proportions(200, 100, 100, 50)
        assert x1 == 100
        assert y1 == 50

    def test_preserve_proportions_width_constrains(self):
        """Width is the limiting factor, adjust height."""
        # Original: 100x100, Target: 50x200
        # Width scale: 0.5, Height scale: 2.0
        # Use smaller scale (0.5), so height becomes 50
        x1, y1 = scale.preserve_proportions(100, 100, 50, 200)
        assert x1 == 50
        assert y1 == 50

    def test_preserve_proportions_height_constrains(self):
        """Height is the limiting factor, adjust width."""
        # Original: 100x100, Target: 200x50
        # Width scale: 2.0, Height scale: 0.5
        # Use smaller scale (0.5), so width becomes 50
        x1, y1 = scale.preserve_proportions(100, 100, 200, 50)
        assert x1 == 50
        assert y1 == 50

    def test_preserve_proportions_square_to_square(self):
        """Square image to square maintains aspect ratio."""
        x1, y1 = scale.preserve_proportions(100, 100, 200, 200)
        assert x1 == 200
        assert y1 == 200

    def test_preserve_proportions_landscape_to_portrait(self):
        """Landscape to portrait constraint."""
        # 200x100 to fit in 100x200
        # Width scale: 0.5, Height scale: 2.0
        # Use 0.5 scale: 100x50
        x1, y1 = scale.preserve_proportions(200, 100, 100, 200)
        assert x1 == 100
        assert y1 == 50

    def test_preserve_proportions_portrait_to_landscape(self):
        """Portrait to landscape constraint."""
        # 100x200 to fit in 200x100
        # Width scale: 2.0, Height scale: 0.5
        # Use 0.5 scale: 50x100
        x1, y1 = scale.preserve_proportions(100, 200, 200, 100)
        assert x1 == 50
        assert y1 == 100

    def test_preserve_proportions_returns_integers(self):
        """Result should be integers."""
        x1, y1 = scale.preserve_proportions(100, 100, 75, 75)
        assert isinstance(x1, int)
        assert isinstance(y1, int)

    def test_preserve_proportions_rounding(self):
        """Rounding should work correctly."""
        # Test that rounding happens properly
        x1, y1 = scale.preserve_proportions(100, 100, 33, 33)
        assert isinstance(x1, int)
        assert isinstance(y1, int)
        assert x1 == 33
        assert y1 == 33


class TestScaleIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = scale.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = scale.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 6

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = scale.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'

    def test_action_docstring_mentions_scale(self):
        """Action documentation mentions scale or resize."""
        action = scale.Action()
        doc_lower = action.__doc__.lower()
        assert ('scale' in doc_lower or 'resize' in doc_lower or
                'smaller' in doc_lower or 'bigger' in doc_lower)

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        scale.init()
        # After init, Image should be available in the module
        assert hasattr(scale, 'Image')
