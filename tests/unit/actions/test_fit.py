"""Unit tests for phatch.actions.fit module.

Tests the Fit action (downsize and crop image with fixed ratio).

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
from phatch.actions import fit


class TestFitAction:
    """Test the Fit action class metadata."""

    def test_action_exists(self):
        """Fit action class should exist."""
        assert hasattr(fit, 'Action')
        assert fit.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = fit.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = fit.Action()
        assert 'fit' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(fit.Action, 'pil')
        assert callable(fit.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(fit.Action, 'init')
        assert callable(fit.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = fit.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_values_method(self):
        """Action should have values method."""
        action = fit.Action()
        assert hasattr(action, 'values')
        assert callable(action.values)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = fit.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower

    def test_action_all_layers(self):
        """Fit action should have all_layers=True."""
        action = fit.Action()
        assert hasattr(action, 'all_layers')
        assert action.all_layers is True


class TestFitInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_width_field(self):
        """interface should define Canvas Width parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Width field
        assert any('width' in k.lower() for k in fields.keys())

    def test_interface_defines_height_field(self):
        """interface should define Canvas Height parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Canvas Height field
        assert any('height' in k.lower() for k in fields.keys())

    def test_interface_defines_resolution_field(self):
        """interface should define Resolution parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Resolution field
        assert any('resolution' in k.lower() for k in fields.keys())

    def test_interface_defines_align_horizontal_field(self):
        """interface should define Align Horizontal parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Align Horizontal field
        assert any('align' in k.lower() and 'horizontal' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_align_vertical_field(self):
        """interface should define Align Vertical parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Align Vertical field
        assert any('align' in k.lower() and 'vertical' in k.lower()
                   for k in fields.keys())

    def test_interface_defines_bleed_field(self):
        """interface should define Bleed parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Bleed field
        assert any('bleed' in k.lower() for k in fields.keys())

    def test_interface_defines_resample_field(self):
        """interface should define Resample Image parameter."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Should have Resample Image field
        assert any('resample' in k.lower() for k in fields.keys())

    def test_interface_width_is_pixel_field(self):
        """Width field should be a PixelField."""
        action = fit.Action()
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

    def test_interface_bleed_is_slider(self):
        """Bleed field should be a SliderField."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        # Get the Bleed field
        bleed_field = None
        for key, value in fields.items():
            if 'bleed' in key.lower():
                bleed_field = value
                break

        assert bleed_field is not None
        assert type(bleed_field).__name__ == 'SliderField'

    def test_interface_has_seven_fields(self):
        """Fit should have seven parameters."""
        action = fit.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 7


class TestFitFunction:
    """Test the fit() PIL function."""

    def test_fit_function_exists(self):
        """fit function should exist."""
        assert hasattr(fit, 'fit')
        assert callable(fit.fit)

    def test_fit_downsize_square(self, rgb_image):
        """Fit to smaller square size."""
        fit.init()

        result = fit.fit(rgb_image, (50, 50), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_upsize_square(self, small_image):
        """Fit to larger square size."""
        fit.init()

        result = fit.fit(small_image, (50, 50), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_different_aspect_ratio(self, rgb_image):
        """Fit to different aspect ratio crops image."""
        fit.init()

        result = fit.fit(rgb_image, (50, 100), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        # Should be exact size requested
        assert result.size == (50, 100)

    def test_fit_center_alignment(self, multicolor_image):
        """Fit with center alignment (0.5, 0.5)."""
        fit.init()

        result = fit.fit(multicolor_image, (50, 50), Image.LANCZOS,
                        0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_left_top_alignment(self, multicolor_image):
        """Fit with left-top alignment (0.0, 0.0)."""
        fit.init()

        result = fit.fit(multicolor_image, (50, 50), Image.LANCZOS,
                        0.0, (0.0, 0.0))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_right_bottom_alignment(self, multicolor_image):
        """Fit with right-bottom alignment (1.0, 1.0)."""
        fit.init()

        result = fit.fit(multicolor_image, (50, 50), Image.LANCZOS,
                        0.0, (1.0, 1.0))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_with_bleed(self, rgb_image):
        """Fit with bleed parameter."""
        fit.init()

        result = fit.fit(rgb_image, (50, 50), Image.LANCZOS, 0.1, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_rgba_image(self, rgba_image):
        """Fit RGBA image."""
        fit.init()

        result = fit.fit(rgba_image, (50, 50), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        # Size should be exact
        assert result.size == (50, 50)

    def test_fit_grayscale(self, grayscale_image):
        """Fit grayscale image."""
        fit.init()

        result = fit.fit(grayscale_image, (50, 50), Image.LANCZOS,
                        0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.mode == 'L'
        assert result.size == (50, 50)


class TestFitEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_fit_landscape_to_portrait(self):
        """Fit landscape image to portrait size."""
        fit.init()

        # Create landscape image
        img = Image.new('RGB', (200, 100), color=(255, 0, 0))
        result = fit.fit(img, (50, 100), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 100)

    def test_fit_portrait_to_landscape(self):
        """Fit portrait image to landscape size."""
        fit.init()

        # Create portrait image
        img = Image.new('RGB', (100, 200), color=(255, 0, 0))
        result = fit.fit(img, (100, 50), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (100, 50)

    def test_fit_small_image(self, small_image):
        """Fit works with small images."""
        fit.init()

        result = fit.fit(small_image, (20, 20), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (20, 20)

    def test_fit_large_image(self, large_image):
        """Fit works with large images."""
        fit.init()

        result = fit.fit(large_image, (100, 100), Image.LANCZOS,
                        0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (100, 100)

    def test_fit_zero_bleed(self, rgb_image):
        """Fit with zero bleed."""
        fit.init()

        result = fit.fit(rgb_image, (50, 50), Image.LANCZOS, 0.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_max_bleed(self, rgb_image):
        """Fit with maximum bleed."""
        fit.init()

        result = fit.fit(rgb_image, (50, 50), Image.LANCZOS, 1.0, (0.5, 0.5))

        assert isinstance(result, Image.Image)
        assert result.size == (50, 50)

    def test_fit_different_methods(self, rgb_image):
        """Fit with various resampling methods."""
        fit.init()

        # Test different resampling methods
        for method in [Image.NEAREST, Image.BILINEAR, Image.BICUBIC,
                      Image.LANCZOS]:
            result = fit.fit(rgb_image, (50, 50), method, 0.0, (0.5, 0.5))
            assert isinstance(result, Image.Image)
            assert result.size == (50, 50)


class TestFitIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_fit(self, multicolor_image):
        """Action.pil should call fit function."""
        fit.init()

        result = fit.Action.pil(multicolor_image, size=(50, 50),
                               method=Image.LANCZOS, bleed=0.0,
                               centering=(0.5, 0.5))

        assert isinstance(result, Image.Image)
        # Verify it actually fit
        assert result.size == (50, 50)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = fit.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = fit.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 7

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = fit.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'transform' in tags_lower or 'size' in tags_lower

    def test_action_docstring_mentions_fit(self):
        """Action documentation mentions fit, downsize, or crop."""
        action = fit.Action()
        doc_lower = action.__doc__.lower()
        assert 'fit' in doc_lower or 'downsize' in doc_lower or 'crop' in doc_lower

    def test_action_pil_points_to_fit(self):
        """Action.pil should point to fit function."""
        # The action's pil staticmethod should be the fit function
        assert fit.Action.pil == fit.fit

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        fit.init()
        # After init, Image should be available in the module
        assert hasattr(fit, 'Image')

    def test_init_loads_imageops(self):
        """init() should load ImageOps module."""
        fit.init()
        # After init, ImageOps should be available
        assert hasattr(fit, 'ImageOps')

    def test_init_loads_colors(self):
        """init() should load color conversion function."""
        fit.init()
        # After init, HTMLColorToRGBA should be available
        assert hasattr(fit, 'HTMLColorToRGBA')
