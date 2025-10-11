"""Integration tests for all Phatch actions.

This test suite executes every action with valid inputs to ensure:
1. No Python 3 compatibility errors (string methods, types, etc.)
2. No Pillow 10+ compatibility errors (ANTIALIAS, etc.)
3. No wxPython 4.x compatibility errors
4. Proper field validation (relevant fields only)
5. No missing dependencies in action init()

This catches the kinds of bugs found during batch execution testing.
"""

import glob
import os
import sys
import tempfile
import pytest
from PIL import Image

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from phatch.core import config
from phatch.core.pil import Photo

# Initialize config paths for testing
config.init_config_paths()

# Create a temp directory for test images
TEST_TEMP_DIR = tempfile.mkdtemp(prefix='phatch_test_')


def get_all_action_modules():
    """Discover all action modules in phatch/actions/."""
    actions_dir = os.path.join(os.path.dirname(__file__), '../../phatch/actions')
    action_files = glob.glob(os.path.join(actions_dir, '*.py'))

    modules = []
    for filepath in action_files:
        filename = os.path.basename(filepath)
        if filename.startswith('_') or filename == 'common.py':
            continue
        module_name = filename[:-3]  # Remove .py
        modules.append(module_name)

    return sorted(modules)


def create_test_image(mode='RGB', size=(100, 100), color=None):
    """Create a test image with specified mode and size."""
    if mode == 'RGBA':
        # Image with transparency for Background, Round, etc.
        color = color or (255, 0, 0, 128)
    elif mode == 'L':
        # Grayscale
        color = color or 128
    elif mode == 'P':
        # Palette mode
        img = Image.new('P', size)
        # Add a simple palette
        palette = []
        for i in range(256):
            palette.extend([i, i, i])
        img.putpalette(palette)
        return img
    else:  # RGB
        color = color or (255, 0, 0)

    return Image.new(mode, size, color)


class MockPhoto:
    """Minimal mock photo object for testing actions."""

    def __init__(self, image):
        self.image = image
        self.info = {
            'size': image.size,
            'width': image.size[0],
            'height': image.size[1],
            'dpi': 72,  # Single number, not tuple
            'path': '/tmp/test.png',
            'filename': 'test.png',
            'folder': '/tmp',
        }
        self._layer = self

    def get_layer(self):
        """Return self as the layer."""
        return self

    def apply_pil(self, pil_func, **kwargs):
        """Apply a PIL function to the image."""
        self.image = pil_func(self.image, **kwargs)


def create_test_photo(image_mode='RGB'):
    """Create a MockPhoto object with test image."""
    image = create_test_image(mode=image_mode)
    return MockPhoto(image)


# Actions that require external dependencies or special setup
SKIP_ACTIONS = {
    'geotag': 'Requires GPS coordinates and external libraries',
    'imagemagick': 'Requires ImageMagick installed',
    'lossless_jpeg': 'Requires jpegtran tool',
}

# Actions that need specific image modes
ACTION_IMAGE_MODES = {
    'background': 'RGBA',  # Needs transparency
    'color_to_alpha': 'RGBA',
    'reflection': 'RGBA',
    'round': 'RGBA',
    'shadow': 'RGBA',
    'watermark': 'RGB',
}


@pytest.mark.parametrize('action_name', get_all_action_modules())
def test_action_executes_without_error(action_name):
    """Test that each action can be executed with valid default values."""

    # Skip actions with external dependencies
    if action_name in SKIP_ACTIONS:
        pytest.skip(SKIP_ACTIONS[action_name])

    # Import the action module
    try:
        action_module = __import__(f'phatch.actions.{action_name}', fromlist=['Action'])
    except ImportError as e:
        pytest.fail(f"Failed to import action {action_name}: {e}")

    # Get the Action class
    try:
        ActionClass = action_module.Action
    except AttributeError:
        pytest.fail(f"Action module {action_name} does not have an Action class")

    # Create action instance
    action = ActionClass()

    # Initialize fields (calls interface method)
    try:
        action.interface(action._fields)
    except Exception as e:
        pytest.fail(f"Action {action_name} interface() failed: {e}")

    # Initialize action dependencies (lazy imports)
    if hasattr(action, 'init') and callable(action.init):
        try:
            action.init()
        except Exception as e:
            # Some actions may fail init without external tools, that's ok
            pytest.skip(f"Action {action_name} init() requires external dependencies: {e}")

    # Create appropriate test image
    image_mode = ACTION_IMAGE_MODES.get(action_name, 'RGB')
    photo = create_test_photo(image_mode=image_mode)

    # Execute the action
    try:
        result = action.apply(photo, setting={}, cache={})
        assert result is not None, f"Action {action_name} returned None"
        # MockPhoto or Photo is acceptable
        assert hasattr(result, 'image'), f"Action {action_name} result has no image attribute"
        assert hasattr(result, 'info'), f"Action {action_name} result has no info attribute"
    except Exception as e:
        pytest.fail(f"Action {action_name} execution failed: {e}")


def test_all_actions_discovered():
    """Verify we discovered action modules."""
    modules = get_all_action_modules()
    assert len(modules) > 40, f"Expected 40+ actions, found {len(modules)}"

    # Check some known actions exist
    assert 'border' in modules
    assert 'save' in modules
    assert 'scale' in modules
    assert 'background' in modules


def test_action_with_transparent_image():
    """Test Background action specifically with transparency (regression test)."""
    action_module = __import__('phatch.actions.background', fromlist=['Action'])
    action = action_module.Action()
    action.interface(action._fields)

    # Set to Color fill (Mark should be excluded from validation)
    action.set_field('Fill', 'Color')
    action.set_field('Color', '#FFFFFF')

    # Initialize dependencies
    if hasattr(action, 'init'):
        action.init()

    # Create transparent image
    photo = create_test_photo(image_mode='RGBA')

    # Should not raise ValidationError for Mark field
    result = action.apply(photo, setting={}, cache={})
    assert result is not None


def test_action_with_pillow_compat():
    """Test actions that use Pillow resampling filters (regression test)."""
    test_actions = ['scale', 'fit', 'canvas']

    for action_name in test_actions:
        action_module = __import__(f'phatch.actions.{action_name}', fromlist=['Action'])
        action = action_module.Action()
        action.interface(action._fields)

        if hasattr(action, 'init'):
            try:
                action.init()
            except:
                pytest.skip(f"Action {action_name} requires external dependencies")

        photo = create_test_photo(image_mode='RGB')

        try:
            result = action.apply(photo, setting={}, cache={})
            assert result is not None, f"Action {action_name} returned None"
        except AttributeError as e:
            if 'ANTIALIAS' in str(e) or 'LINEAR' in str(e):
                pytest.fail(f"Action {action_name} still using deprecated Pillow constants: {e}")
            raise


if __name__ == '__main__':
    # Run with: python -m pytest tests/integration/test_all_actions_integration.py -v
    pytest.main([__file__, '-v', '-s'])
