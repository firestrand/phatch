"""Unit tests for phatch.actions.background module.

Tests the Background action (fill transparent background with color or image).

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
from phatch.actions import background


class TestBackgroundAction:
    """Test the Background action class metadata."""

    def test_action_exists(self):
        """Background action class should exist."""
        assert hasattr(background, 'Action')
        assert background.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = background.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = background.Action()
        assert 'background' in action.label.lower()

    def test_action_has_pil_method(self):
        """Action should have pil staticmethod."""
        assert hasattr(background.Action, 'pil')
        assert callable(background.Action.pil)

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(background.Action, 'init')
        assert callable(background.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = background.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_get_relevant_field_labels(self):
        """Action should have get_relevant_field_labels method."""
        action = background.Action()
        assert hasattr(action, 'get_relevant_field_labels')
        assert callable(action.get_relevant_field_labels)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = background.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'color' in tags_lower or 'filter' in tags_lower


class TestBackgroundConstants:
    """Test module-level constants."""

    def test_fill_choices_constant_exists(self):
        """FILL_CHOICES constant should exist."""
        assert hasattr(background, 'FILL_CHOICES')
        assert isinstance(background.FILL_CHOICES, tuple)

    def test_fill_choices_has_two_values(self):
        """FILL_CHOICES should have two values."""
        assert len(background.FILL_CHOICES) == 2

    def test_fill_choices_has_color(self):
        """FILL_CHOICES should include Color option."""
        choices_lower = [str(c).lower() for c in background.FILL_CHOICES]
        assert 'color' in choices_lower

    def test_fill_choices_has_image(self):
        """FILL_CHOICES should include Image option."""
        choices_lower = [str(c).lower() for c in background.FILL_CHOICES]
        assert 'image' in choices_lower


class TestBackgroundInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_fill_field(self):
        """interface should define Fill parameter."""
        action = background.Action()
        fields = {}
        action.interface(fields)

        # Should have Fill field
        assert 'Fill' in fields.keys()

    def test_interface_defines_color_field(self):
        """interface should define Color parameter."""
        action = background.Action()
        fields = {}
        action.interface(fields)

        # Should have Color field
        assert 'Color' in fields.keys()

    def test_interface_fill_is_choice_field(self):
        """Fill field should be a ChoiceField."""
        action = background.Action()
        fields = {}
        action.interface(fields)

        fill_field = fields.get('Fill')
        assert fill_field is not None
        assert type(fill_field).__name__ == 'ChoiceField'

    def test_interface_color_is_color_field(self):
        """Color field should be a ColorField."""
        action = background.Action()
        fields = {}
        action.interface(fields)

        color_field = fields.get('Color')
        assert color_field is not None
        assert type(color_field).__name__ == 'ColorField'

    def test_interface_inherits_from_stamp_mixin(self):
        """Interface should include fields from StampMixin."""
        action = background.Action()
        fields = {}
        action.interface(fields)

        # StampMixin adds additional fields
        # Minimum should have Fill and Color
        assert len(fields) >= 2


class TestBackgroundFunction:
    """Test the background() PIL function."""

    def test_background_function_exists(self):
        """background function should exist."""
        assert hasattr(background, 'background')
        assert callable(background.background)

    def test_background_no_transparency_returns_original(self, rgb_image):
        """Background on non-transparent image returns original."""
        background.init()

        result = background.background(rgb_image, 'Color', None, '#FFFFFF')

        # Should return original since no transparency
        assert result is rgb_image

    def test_background_color_fill_white(self, rgba_image):
        """Background with white color fill."""
        background.init()

        result = background.background(rgba_image, 'Color', None, '#FFFFFF',
                                      opacity=100)

        assert isinstance(result, Image.Image)
        # Transparency should be filled

    def test_background_color_fill_red(self, rgba_image):
        """Background with red color fill."""
        background.init()

        result = background.background(rgba_image, 'Color', None, '#FF0000',
                                      opacity=100)

        assert isinstance(result, Image.Image)
        # Check background is red
        # Corners should have red background
        corner_pixel = result.getpixel((0, 0))
        assert corner_pixel[0] == 255  # Red channel

    def test_background_color_fill_partial_opacity(self, rgba_image):
        """Background with partial opacity."""
        background.init()

        result = background.background(rgba_image, 'Color', None, '#FFFFFF',
                                      opacity=50)

        assert isinstance(result, Image.Image)

    def test_background_palette_mode_converted(self):
        """Background converts palette mode to RGBA."""
        background.init()

        # Create palette image with transparency
        img = Image.new('P', (100, 100))
        img.info['transparency'] = 0

        result = background.background(img, 'Color', None, '#FFFFFF',
                                      opacity=100)

        assert isinstance(result, Image.Image)

    def test_background_grayscale_no_transparency(self, grayscale_image):
        """Background on grayscale without transparency returns original."""
        background.init()

        result = background.background(grayscale_image, 'Color', None,
                                      '#FFFFFF', opacity=100)

        # Should return original since no transparency
        assert result is grayscale_image


class TestBackgroundEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_background_zero_opacity(self, rgba_image):
        """Background with zero opacity."""
        background.init()

        result = background.background(rgba_image, 'Color', None, '#FFFFFF',
                                      opacity=0)

        assert isinstance(result, Image.Image)

    def test_background_max_opacity(self, rgba_image):
        """Background with maximum opacity."""
        background.init()

        result = background.background(rgba_image, 'Color', None, '#FFFFFF',
                                      opacity=100)

        assert isinstance(result, Image.Image)

    def test_background_different_colors(self, rgba_image):
        """Background with various colors."""
        background.init()

        # Test different colors
        for color in ['#000000', '#FF0000', '#00FF00', '#0000FF', '#FFFF00']:
            result = background.background(rgba_image, 'Color', None, color,
                                          opacity=100)
            assert isinstance(result, Image.Image)

    def test_background_image_fill_orientation_string(self, rgba_image):
        """Image fill should resolve string orientation names."""
        calls = {}

        def fake_generate_layer(size, mark, method, h_off, v_off,
                                h_just, v_just, orientation, opacity):
            calls['args'] = (size, mark, method, h_off, v_off,
                             h_just, v_just, orientation, opacity)
            return Image.new('RGBA', size, (255, 255, 255, 128))

        background.init({'Image': Image, 'generate_layer': fake_generate_layer,
                          'HTMLColorToRGBA': background.HTMLColorToRGBA})

        mark = Image.new('RGBA', (20, 20), (0, 0, 0, 128))
        result = background.background(
            rgba_image,
            background.FILL_CHOICES[1],
            mark=mark,
            method='tile',
            orientation='ROTATE_180',
            opacity=70,
        )

        assert isinstance(result, Image.Image)
        assert calls['args'][0] == rgba_image.size
        assert calls['args'][2] == 'tile'
        assert calls['args'][7] == getattr(Image, 'ROTATE_180')
        assert calls['args'][8] == 70

        background.init()

    def test_background_small_image(self):
        """Background works with small transparent images."""
        background.init()

        # Create small RGBA image
        img = Image.new('RGBA', (10, 10), color=(255, 0, 0, 128))
        result = background.background(img, 'Color', None, '#FFFFFF',
                                      opacity=100)

        assert isinstance(result, Image.Image)

    def test_background_large_image(self):
        """Background works with large transparent images."""
        background.init()

        # Create large RGBA image
        img = Image.new('RGBA', (500, 500), color=(255, 0, 0, 128))
        result = background.background(img, 'Color', None, '#FFFFFF',
                                      opacity=100)

        assert isinstance(result, Image.Image)


class TestBackgroundIntegration:
    """Test integration with Action class."""

    def test_action_pil_calls_background(self, rgba_image):
        """Action.pil should call background function."""
        background.init()

        result = background.Action.pil(rgba_image, fill='Color', mark=None,
                                      color='#FFFFFF', opacity=100)

        assert isinstance(result, Image.Image)

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = background.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = background.Action()
        fields = {}
        action.interface(fields)
        # Should have at least Fill and Color
        assert len(fields) >= 2

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = background.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'color' in tags_lower or 'filter' in tags_lower

    def test_action_docstring_mentions_background(self):
        """Action documentation mentions background or transparent."""
        action = background.Action()
        doc_lower = action.__doc__.lower()
        assert 'background' in doc_lower or 'transparent' in doc_lower

    def test_action_pil_points_to_background(self):
        """Action.pil should point to background function."""
        # The action's pil staticmethod should be the background function
        assert background.Action.pil == background.background

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        background.init()
        # After init, Image should be available in the module
        assert hasattr(background, 'Image')

    def test_init_loads_colors(self):
        """init() should load color conversion function."""
        background.init()
        # After init, HTMLColorToRGBA should be available
        assert hasattr(background, 'HTMLColorToRGBA')
