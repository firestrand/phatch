"""Unit tests for phatch.actions.reflection module.

Tests the Reflection action (drops a reflection).

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
from phatch.actions import reflection


class TestReflectionAction:
    """Test the Reflection action class metadata."""

    def test_action_exists(self):
        """Reflection action class should exist."""
        assert hasattr(reflection, 'Action')
        assert reflection.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = reflection.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = reflection.Action()
        assert 'reflection' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(reflection.Action, 'pil')
        assert callable(reflection.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(reflection.Action, 'init')
        assert callable(reflection.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = reflection.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = reflection.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_has_get_relevant_field_labels(self):
        """Action should have get_relevant_field_labels method."""
        action = reflection.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = reflection.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower

    def test_action_has_cache(self):
        """Action should have cache enabled."""
        action = reflection.Action()
        assert hasattr(action, 'cache')
        assert action.cache is True


class TestReflectionConstants:
    """Test module-level constants."""

    def test_reflect_id_constant_exists(self):
        """REFLECT_ID constant should exist."""
        assert hasattr(reflection, 'REFLECT_ID')
        assert isinstance(reflection.REFLECT_ID, str)

    def test_reflect_id_has_placeholders(self):
        """REFLECT_ID should have format placeholders."""
        assert '%s' in reflection.REFLECT_ID


class TestReflectionInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_depth_field(self):
        """interface should define Depth parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('depth' in k.lower() for k in fields.keys())

    def test_interface_defines_gap_field(self):
        """interface should define Gap parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('gap' in k.lower() for k in fields.keys())

    def test_interface_defines_opacity_field(self):
        """interface should define Opacity parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('opacity' in k.lower() for k in fields.keys())

    def test_interface_defines_blur_field(self):
        """interface should define Blur Reflection parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('blur' in k.lower() for k in fields.keys())

    def test_interface_defines_scale_reflection_field(self):
        """interface should define Scale Reflection parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('scale' in k.lower() and 'reflection' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_scale_method_field(self):
        """interface should define Scale Method parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('scale' in k.lower() and 'method' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_background_color_field(self):
        """interface should define Background Color parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('background' in k.lower() and 'color' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_background_opacity_field(self):
        """interface should define Background Opacity parameter."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert any('background' in k.lower() and 'opacity' in k.lower()
                   for k in fields.keys())

    def test_interface_has_eight_fields(self):
        """Reflection should have eight parameters."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 8


class TestReflectionHelperFunctions:
    """Test helper functions."""

    def test_gradient_vector_function_exists(self):
        """gradient_vector function should exist."""
        assert hasattr(reflection, 'gradient_vector')
        assert callable(reflection.gradient_vector)

    def test_gradient_vector_creates_gradient(self):
        """gradient_vector creates gradient vector."""
        reflection.init()
        cache = {}

        vector = reflection.gradient_vector(100, 255, cache)

        assert isinstance(vector, Image.Image)
        assert vector.mode == 'L'
        assert vector.size == (1, 100)

    def test_gradient_vector_caches_result(self):
        """gradient_vector caches results."""
        reflection.init()
        cache = {}

        vector1 = reflection.gradient_vector(100, 255, cache)
        vector2 = reflection.gradient_vector(100, 255, cache)

        # Should return same cached object
        assert vector1 is vector2
        assert len(cache) > 0

    def test_gradient_mask_function_exists(self):
        """gradient_mask function should exist."""
        assert hasattr(reflection, 'gradient_mask')
        assert callable(reflection.gradient_mask)

    def test_gradient_mask_creates_mask(self):
        """gradient_mask creates 2D gradient mask."""
        reflection.init()
        cache = {}

        mask = reflection.gradient_mask((100, 50), 255, cache)

        assert isinstance(mask, Image.Image)
        assert mask.mode == 'L'
        assert mask.size == (100, 50)

    def test_gradient_mask_caches_result(self):
        """gradient_mask caches results."""
        reflection.init()
        cache = {}

        mask1 = reflection.gradient_mask((100, 50), 255, cache)
        mask2 = reflection.gradient_mask((100, 50), 255, cache)

        # Should return same cached object
        assert mask1 is mask2
        assert len(cache) > 0


class TestReflectionFunction:
    """Test the reflect() PIL function."""

    def test_reflect_function_exists(self):
        """reflect function should exist."""
        assert hasattr(reflection, 'reflect')
        assert callable(reflection.reflect)

    def test_reflect_basic(self, rgb_image):
        """Reflect with basic settings."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=90,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Height should increase (original + reflection)
        assert result.size[0] == 100  # Width unchanged
        assert result.size[1] > 100   # Height increased

    def test_reflect_with_depth(self, rgb_image):
        """Reflect with specific depth."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=30, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Height = original (100) + depth (30) = 130
        assert result.size == (100, 130)

    def test_reflect_with_gap(self, rgb_image):
        """Reflect with gap between image and reflection."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=30, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS', gap=10)

        assert isinstance(result, Image.Image)
        # Height = original (100) + gap (10) + depth (30) = 140
        assert result.size == (100, 140)

    def test_reflect_scaled(self, rgb_image):
        """Reflect with scale_reflection enabled."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS',
                                   scale_reflection=True)

        assert isinstance(result, Image.Image)
        # Height = original (100) + depth (50) = 150
        assert result.size == (100, 150)

    def test_reflect_not_scaled(self, rgb_image):
        """Reflect without scaling (cropped)."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS',
                                   scale_reflection=False)

        assert isinstance(result, Image.Image)
        # Height = original (100) + depth (50) = 150
        assert result.size == (100, 150)

    def test_reflect_blurred(self, rgb_image):
        """Reflect with blur applied."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS',
                                   blur_reflection=True)

        assert isinstance(result, Image.Image)
        assert result.size == (100, 150)

    def test_reflect_rgba_image(self, rgba_image):
        """Reflect RGBA image with transparency."""
        reflection.init()

        result = reflection.reflect(rgba_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=90,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Should be RGBA due to background_opacity < 100
        assert result.mode == 'RGBA'

    def test_reflect_grayscale(self, grayscale_image):
        """Reflect grayscale image."""
        reflection.init()

        result = reflection.reflect(grayscale_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Grayscale converted to RGB
        assert result.mode == 'RGB'

    def test_reflect_depth_limited_to_height(self, rgb_image):
        """Reflection depth is limited to image height."""
        reflection.init()

        # Request depth larger than image height
        result = reflection.reflect(rgb_image, depth=200, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Depth should be clamped to image height (100)
        assert result.size == (100, 200)


class TestReflectionEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_reflect_minimal_depth(self, rgb_image):
        """Reflect with minimal depth."""
        reflection.init()

        # Zero depth would cause ValueError in gradient_mask
        # Use minimal depth of 1 instead
        result = reflection.reflect(rgb_image, depth=1, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Minimal depth means tiny reflection added
        assert result.size == (100, 101)

    def test_reflect_full_opacity(self, rgb_image):
        """Reflect with full opacity (100)."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=100,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)

    def test_reflect_zero_opacity(self, rgb_image):
        """Reflect with zero opacity."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=0,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)

    def test_reflect_different_background_colors(self, rgb_image):
        """Reflect with various background colors."""
        reflection.init()

        for color in ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00']:
            result = reflection.reflect(rgb_image, depth=30, opacity=60,
                                       background_color=color,
                                       background_opacity=100,
                                       scale_method='LANCZOS')
            assert isinstance(result, Image.Image)

    def test_reflect_partial_background_opacity(self, rgb_image):
        """Reflect with partial background opacity."""
        reflection.init()

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=50,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Partial opacity should create RGBA mode
        assert result.mode == 'RGBA'

    def test_reflect_small_image(self, small_image):
        """Reflect works with small images."""
        reflection.init()

        result = reflection.reflect(small_image, depth=5, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        assert result.size == (10, 15)

    def test_reflect_multicolor(self, multicolor_image):
        """Reflect multicolor image."""
        reflection.init()

        result = reflection.reflect(multicolor_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        assert result.size == (100, 150)

    def test_reflect_with_cache_parameter(self, rgb_image):
        """Reflect with explicit cache parameter."""
        reflection.init()
        cache = {}

        result = reflection.reflect(rgb_image, depth=50, opacity=60,
                                   background_color='#FFFFFF',
                                   background_opacity=100,
                                   scale_method='LANCZOS',
                                   cache=cache)

        assert isinstance(result, Image.Image)
        # Cache should be populated
        assert len(cache) > 0

    def test_reflect_reuses_cache(self, rgb_image):
        """Reflect reuses cached gradients."""
        reflection.init()
        cache = {}

        # First call
        result1 = reflection.reflect(rgb_image, depth=50, opacity=60,
                                    background_color='#FFFFFF',
                                    background_opacity=100,
                                    scale_method='LANCZOS',
                                    cache=cache)

        cache_size_1 = len(cache)

        # Second call with same parameters
        result2 = reflection.reflect(rgb_image, depth=50, opacity=60,
                                    background_color='#FFFFFF',
                                    background_opacity=100,
                                    scale_method='LANCZOS',
                                    cache=cache)

        cache_size_2 = len(cache)

        # Cache size should not increase
        assert cache_size_1 == cache_size_2
        assert result1.width == rgb_image.width
        assert result2.width == rgb_image.width
        assert result1.height >= rgb_image.height
        assert result2.height >= rgb_image.height


class TestReflectionIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_reflect(self, multicolor_image):
        """Action.pil should call reflect function."""
        reflection.init()

        result = reflection.Action.pil(multicolor_image, depth=50, opacity=60,
                                      background_color='#FFFFFF',
                                      background_opacity=100,
                                      scale_method='LANCZOS')

        assert isinstance(result, Image.Image)
        # Verify it actually reflected
        assert result.size == (100, 150)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = reflection.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = reflection.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 8

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = reflection.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'filter' in tags_lower

    def test_action_docstring_mentions_reflection(self):
        """Action documentation mentions reflection."""
        action = reflection.Action()
        doc_lower = action.__doc__.lower()
        assert 'reflection' in doc_lower

    def test_action_pil_points_to_reflect(self):
        """Action.pil should point to reflect function."""
        assert reflection.Action.pil == reflection.reflect

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        reflection.init()
        assert hasattr(reflection, 'Image')
        assert hasattr(reflection, 'ImageColor')
        assert hasattr(reflection, 'ImageFilter')

    def test_init_loads_colors(self):
        """init() should load color conversion function."""
        reflection.init()
        assert hasattr(reflection, 'HTMLColorToRGBA')

    def test_get_relevant_field_labels_no_scale(self):
        """get_relevant_field_labels when Scale Reflection is false."""
        action = reflection.Action()
        action.get_field_string = lambda x: 'no' if x == 'Scale Reflection' else None

        relevant = action.get_relevant_field_labels()

        # Should NOT include Scale Method
        assert 'Scale Method' not in relevant
        assert 'Depth' in relevant
        assert 'Opacity' in relevant

    def test_get_relevant_field_labels_with_scale(self):
        """get_relevant_field_labels when Scale Reflection is true."""
        action = reflection.Action()
        action.get_field_string = lambda x: 'yes' if x == 'Scale Reflection' else None

        relevant = action.get_relevant_field_labels()

        # Should include Scale Method
        assert 'Scale Method' in relevant
        assert 'Depth' in relevant
        assert 'Opacity' in relevant
