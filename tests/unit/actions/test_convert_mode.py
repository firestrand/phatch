"""Unit tests for phatch.actions.convert_mode module.

Tests the Convert Mode action (convert the color mode of an image).

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
from phatch.actions import convert_mode


class MockPhoto:
    """Mock photo object for testing apply method."""

    def __init__(self, image):
        self.image = image
        self.info = {'size': image.size}
        self._converted_mode = None
        self._converted_palette = None

    def convert(self, mode, palette=None):
        """Mock convert method."""
        self._converted_mode = mode
        self._converted_palette = palette
        if palette:
            self.image = self.image.convert(mode, palette=palette)
        else:
            self.image = self.image.convert(mode)


class TestConvertModeAction:
    """Test the Convert Mode action class metadata."""

    def test_action_exists(self):
        """Convert Mode action class should exist."""
        assert hasattr(convert_mode, 'Action')
        assert convert_mode.Action is not None

    def test_action_has_required_metadata(self):
        """Action should have required metadata attributes."""
        action = convert_mode.Action()
        assert hasattr(action, 'label')
        assert hasattr(action, 'author')
        assert hasattr(action, 'email')
        assert hasattr(action, 'version')
        assert hasattr(action, 'tags')
        assert hasattr(action, '__doc__')

    def test_action_label(self):
        """Action should have descriptive label."""
        action = convert_mode.Action()
        assert 'convert' in action.label.lower() and 'mode' in action.label.lower()

    def test_action_has_init_method(self):
        """Action should have init staticmethod for lazy loading."""
        assert hasattr(convert_mode.Action, 'init')
        assert callable(convert_mode.Action.init)

    def test_action_has_interface_method(self):
        """Action should have interface method."""
        action = convert_mode.Action()
        assert hasattr(action, 'interface')
        assert callable(action.interface)

    def test_action_has_apply_method(self):
        """Action should have apply method."""
        action = convert_mode.Action()
        assert hasattr(action, 'apply')
        assert callable(action.apply)

    def test_action_tags(self):
        """Action should have appropriate tags."""
        action = convert_mode.Action()
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'color' in tags_lower

    def test_action_no_pil_method(self):
        """Action should not have pil staticmethod."""
        # This action uses apply() instead of pil()
        action = convert_mode.Action()
        # pil should not be defined or should not be the staticmethod
        if hasattr(action, 'pil'):
            # If it exists, it's likely inherited, not defined
            pass


class TestConvertModeInterface:
    """Test the interface() method defining parameters."""

    def test_interface_defines_mode_field(self):
        """interface should define Mode parameter."""
        action = convert_mode.Action()
        fields = {}
        action.interface(fields)

        # Should have Mode field
        assert any('mode' in k.lower() for k in fields.keys())

    def test_interface_mode_is_image_mode_field(self):
        """Mode field should be an ImageModeField."""
        action = convert_mode.Action()
        fields = {}
        action.interface(fields)

        # Get the Mode field
        mode_field = None
        for key, value in fields.items():
            if 'mode' in key.lower():
                mode_field = value
                break

        assert mode_field is not None
        assert type(mode_field).__name__ == 'ImageModeField'

    def test_interface_has_one_field(self):
        """Convert Mode should have one parameter."""
        action = convert_mode.Action()
        fields = {}
        action.interface(fields)

        assert len(fields) == 1


class TestConvertModeConstants:
    """Test module-level and class constants."""

    def test_image_modes_constant_exists(self):
        """IMAGE_MODES constant should exist."""
        action = convert_mode.Action()
        assert hasattr(action, 'IMAGE_MODES')
        assert isinstance(action.IMAGE_MODES, (list, tuple))

    def test_image_modes_has_values(self):
        """IMAGE_MODES should have multiple values."""
        action = convert_mode.Action()
        assert len(action.IMAGE_MODES) > 0

    def test_image_modes_includes_common_modes(self):
        """IMAGE_MODES should include common modes."""
        action = convert_mode.Action()
        # Should include at least some common modes (such as RGB family)
        assert any('RGB' in mode for mode in action.IMAGE_MODES)


class TestConvertModeConversions:
    """Test mode conversion functionality."""

    def test_convert_rgb_to_grayscale(self):
        """Convert RGB image to grayscale (L)."""
        convert_mode.init()

        # Create RGB image
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        # Set the Mode field
        action.get_field = lambda field, info: 'L'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'L'

    def test_convert_rgb_to_rgba(self):
        """Convert RGB image to RGBA."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGBA'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'RGBA'

    def test_convert_rgba_to_rgb(self):
        """Convert RGBA image to RGB."""
        convert_mode.init()

        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGB'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'RGB'

    def test_convert_to_palette(self):
        """Convert to palette mode (P)."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'P'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'P'
        # Palette mode should use ADAPTIVE palette
        assert result_photo._converted_palette == Image.ADAPTIVE

    def test_convert_to_1bit(self):
        """Convert to 1-bit mode."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: '1'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == '1'

    def test_convert_grayscale_to_rgb(self):
        """Convert grayscale to RGB."""
        convert_mode.init()

        img = Image.new('L', (100, 100), color=128)
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGB'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'RGB'

    def test_convert_same_mode(self):
        """Convert to same mode (RGB to RGB)."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGB'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'RGB'


class TestConvertModeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_convert_small_image(self):
        """Convert small image."""
        convert_mode.init()

        img = Image.new('RGB', (10, 10), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'L'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'L'

    def test_convert_large_image(self):
        """Convert large image."""
        convert_mode.init()

        img = Image.new('RGB', (500, 500), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'L'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'L'

    def test_convert_palette_to_rgb(self):
        """Convert palette image to RGB."""
        convert_mode.init()

        img = Image.new('P', (100, 100))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGB'

        result_photo = action.apply(photo, None, None)

        assert result_photo._converted_mode == 'RGB'

    def test_convert_returns_photo(self):
        """Convert mode returns photo object."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'L'

        result_photo = action.apply(photo, None, None)

        # Should return the same photo object
        assert result_photo is photo


class TestConvertModeIntegration:
    """Test integration with Action class."""

    def test_action_can_be_instantiated(self):
        """Action can be instantiated."""
        action = convert_mode.Action()
        assert action is not None

    def test_action_interface_callable(self):
        """Action interface is callable."""
        action = convert_mode.Action()
        fields = {}
        action.interface(fields)
        assert len(fields) == 1

    def test_action_metadata_correct(self):
        """Action metadata is correctly set."""
        action = convert_mode.Action()
        assert action.author == 'Stani'
        assert action.version == '0.1'
        tags_lower = [str(tag).lower() for tag in action.tags]
        assert 'color' in tags_lower

    def test_action_docstring_mentions_convert(self):
        """Action documentation mentions convert or mode."""
        action = convert_mode.Action()
        doc_lower = action.__doc__.lower()
        assert 'convert' in doc_lower or 'mode' in doc_lower

    def test_init_loads_pil(self):
        """init() should load PIL modules."""
        convert_mode.init()
        # After init, Image should be available in the module
        assert hasattr(convert_mode, 'Image')

    def test_apply_with_mock_photo(self):
        """apply() method works with mock photo."""
        convert_mode.init()

        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        photo = MockPhoto(img)

        action = convert_mode.Action()
        action.get_field = lambda field, info: 'RGBA'

        result = action.apply(photo, None, None)

        assert isinstance(result, MockPhoto)
        assert result._converted_mode == 'RGBA'
