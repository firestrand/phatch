"""Unit tests for phatch.actions.sketch module.

Tests the Sketch action (transform to grayscale pencil drawing).

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
from phatch.actions import sketch


class TestSketchAction:
    """Test the Sketch action class metadata."""

    def test_action_exists(self):
        """Sketch action class should exist."""
        assert hasattr(sketch, 'Action')
        assert sketch.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = sketch.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = sketch.Action()
        assert 'sketch' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(sketch.Action, 'pil')
        assert callable(sketch.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(sketch.Action, 'init')
        assert callable(sketch.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = sketch.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_cache_disabled(self):
        """Sketch action should have cache disabled."""
        action = sketch.Action()
        assert hasattr(action, 'cache')
        assert not action.cache


class TestSketchInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_details_field(self):
        """interface should define Details Degree parameter."""
        action = sketch.Action()
        fields = {}
        action.interface(fields)

        # Should have Details Degree field
        assert any('details' in k.lower() for k in fields.keys())

    def test_interface_details_is_integer(self):
        """Details Degree field should be an IntegerField."""
        action = sketch.Action()
        fields = {}
        action.interface(fields)

        # Get the Details field
        details_field = None
        for key, value in fields.items():
            if 'details' in key.lower():
                details_field = value
                break

        assert details_field is not None
        assert type(details_field).__name__ == 'IntegerField'

    def test_interface_has_one_field(self):
        """Sketch should have only one parameter."""
        action = sketch.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestSketchPilFunction:
    """Test the sketch() PIL function."""

    def test_sketch_function_exists(self):
        """sketch function should exist."""
        assert hasattr(sketch, 'sketch')
        assert callable(sketch.sketch)

    def test_sketch_rgb_image(self, multicolor_image):
        """Sketch RGB image creates grayscale pencil drawing."""
        sketch.init()

        result = sketch.sketch(multicolor_image, details_degree=1)

        assert isinstance(result, Image.Image)
        # Sketch always returns grayscale
        assert result.mode == 'L'

    def test_sketch_low_details(self, rgb_image):
        """Sketch with low details (1) creates simple drawing."""
        sketch.init()

        result = sketch.sketch(rgb_image, details_degree=1)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == rgb_image.size

    def test_sketch_high_details(self, multicolor_image):
        """Sketch with high details (20) creates softer drawing."""
        sketch.init()

        result = sketch.sketch(multicolor_image, details_degree=20)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == multicolor_image.size

    def test_sketch_grayscale_image(self, grayscale_image):
        """Sketch already grayscale image."""
        sketch.init()

        result = sketch.sketch(grayscale_image, details_degree=5)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == grayscale_image.size

    def test_sketch_rgba_image(self, rgba_image):
        """Sketch RGBA image (converts to grayscale, loses alpha)."""
        sketch.init()

        result = sketch.sketch(rgba_image, details_degree=5)

        assert isinstance(result, Image.Image)
        # Sketch always returns 'L' mode (grayscale, no alpha)
        assert result.mode == 'L'
        assert result.size == rgba_image.size

    def test_sketch_gradient(self, gradient_image):
        """Sketch gradient creates edge-detected look."""
        sketch.init()

        result = sketch.sketch(gradient_image, details_degree=10)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == gradient_image.size


class TestSketchEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_sketch_details_minimum(self, multicolor_image):
        """Sketch with details=1 (minimum from choices)."""
        sketch.init()

        result = sketch.sketch(multicolor_image, details_degree=1)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'

    def test_sketch_details_maximum(self, multicolor_image):
        """Sketch with details=20 (maximum from choices)."""
        sketch.init()

        result = sketch.sketch(multicolor_image, details_degree=20)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'

    def test_sketch_small_image(self, small_image):
        """Sketch works with small images."""
        sketch.init()

        result = sketch.sketch(small_image, details_degree=5)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == small_image.size

    def test_sketch_large_image(self, large_image):
        """Sketch works with large images."""
        sketch.init()

        result = sketch.sketch(large_image, details_degree=5)

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == large_image.size

    def test_sketch_twice(self, multicolor_image):
        """Sketching twice (already grayscale after first)."""
        sketch.init()

        first = sketch.sketch(multicolor_image, details_degree=5)
        second = sketch.sketch(first, details_degree=10)

        assert isinstance(second, Image.Image)
        assert second.mode == 'L'
        # Second sketch processes the first sketch result

    def test_sketch_different_details(self, multicolor_image):
        """Sketch with various detail levels."""
        sketch.init()

        # Test all available choices
        for details in [1, 5, 10, 20]:
            result = sketch.sketch(multicolor_image, details_degree=details)
            assert isinstance(result, Image.Image)
            assert result.mode == 'L'
            assert result.size == multicolor_image.size


class TestSketchIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_sketch(self, multicolor_image):
        """Action.pil should call sketch function."""
        sketch.init()

        result = sketch.Action.pil(multicolor_image, details_degree=5)

        assert isinstance(result, Image.Image)
        # Verify it actually sketched
        assert result.mode == 'L'
        assert result.size == multicolor_image.size

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = sketch.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = sketch.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1  # Only Details Degree field

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = sketch.Action()
        assert action.author == 'Nadia Alramli'
        assert action.version == '0.1'
        assert 'filter' in [str(tag).lower() for tag in action.tags]

    def test_action_docstring_mentions_sketch(self):
        """Action documentation mentions sketch or pencil or drawing."""
        action = sketch.Action()
        doc_lower = action.__doc__.lower()
        assert ('sketch' in doc_lower or 'pencil' in doc_lower or
                'drawing' in doc_lower or 'grayscale' in doc_lower)

    def test_action_pil_points_to_sketch(self):
        """Action.pil should point to sketch function."""
        # The action's pil staticmethod should be the sketch function
        assert sketch.Action.pil == sketch.sketch
