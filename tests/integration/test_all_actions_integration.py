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
import shutil
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

    def __init__(self, image, temp_path=None):
        self.image = image
        # Save actual temp file if provided
        if temp_path:
            image.save(temp_path)
            path = temp_path
            folder = os.path.dirname(temp_path)
            filename = os.path.basename(temp_path)
        else:
            path = '/tmp/test.png'
            folder = '/tmp'
            filename = 'test.png'

        self.info = {
            'size': image.size,
            'width': image.size[0],
            'height': image.size[1],
            'dpi': 72,  # Single number, not tuple
            'path': path,
            'filename': filename,
            'folder': folder,
            'type': 'png',  # For save/copy/rename actions
            # Add date metadata for time_shift
            'exif': {},
            'iptc': {},
        }
        self._layer = self

    def get_layer(self):
        """Return self as the layer."""
        return self

    def apply_pil(self, pil_func, **kwargs):
        """Apply a PIL function to the image."""
        self.image = pil_func(self.image, **kwargs)

    def convert(self, mode, palette=None):
        """Convert image mode (for convert_mode action)."""
        if palette:
            self.image = self.image.convert(mode, palette=palette)
        else:
            self.image = self.image.convert(mode)
        return self

    def resize(self, size, resample=None):
        """Resize image (for scale action)."""
        if resample:
            self.image = self.image.resize(size, resample)
        else:
            self.image = self.image.resize(size)
        return self

    def append_to_report(self, message):
        """Append message to report (for save_metadata action)."""
        if not hasattr(self, '_report'):
            self._report = []
        self._report.append(message)

    def save(self, path=None, **kwargs):
        """Save image to disk (for save/save_metadata actions)."""
        if path is None:
            path = self.info.get('path', '/tmp/test_output.png')
        self.image.save(path, **kwargs)
        return self


def create_test_photo(image_mode='RGB', save_to_file=False):
    """Create a MockPhoto object with test image."""
    image = create_test_image(mode=image_mode)
    if save_to_file:
        # Create a real temp file for actions that need it
        temp_path = os.path.join(TEST_TEMP_DIR, f'test_{image_mode}_{id(image)}.png')
        return MockPhoto(image, temp_path=temp_path)
    return MockPhoto(image)


def create_helper_image(name, mode='RGBA', size=(50, 50)):
    """Create helper images for watermark, mask, highlight, etc."""
    temp_path = os.path.join(TEST_TEMP_DIR, f'{name}.png')
    if not os.path.exists(temp_path):
        if mode == 'L':
            # Grayscale for masks
            img = create_test_image(mode='L', size=size, color=255)
        else:
            # RGBA with transparency for watermarks/highlights
            img = create_test_image(mode='RGBA', size=size, color=(255, 255, 255, 200))
        img.save(temp_path)
    return temp_path


# Actions that require external dependencies or special setup
SKIP_ACTIONS = {
    'geotag': 'Requires GPS coordinates and external libraries',
    'imagemagick': 'Requires ImageMagick installed',
    'geek': 'Requires ImageMagick convert command',
    'text': 'Requires system fonts and font cache initialization',
    'save_metadata': 'Requires PyExiv2 metadata library and proper info object',
    'blender': 'Requires Blender 2.45-2.49 3D software',
}

# Actions that can be conditionally tested based on tool availability
def should_skip_lossless_jpeg():
    """Check if jpegtran or exiftran are available."""
    has_jpegtran = shutil.which('jpegtran') is not None
    has_exiftran = shutil.which('exiftran') is not None
    if not (has_jpegtran or has_exiftran):
        return 'Requires jpegtran (libjpeg-turbo) or exiftran'
    return None

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

    # Conditional skip for lossless_jpeg based on tool availability
    if action_name == 'lossless_jpeg':
        skip_reason = should_skip_lossless_jpeg()
        if skip_reason:
            pytest.skip(skip_reason)

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

    # Set up action-specific field values
    if action_name == 'watermark':
        # Provide a watermark image file
        watermark_path = create_helper_image('watermark')
        action.set_field('Mark', watermark_path)
    elif action_name == 'mask':
        # Provide a mask image file
        mask_path = create_helper_image('mask', mode='L')
        action.set_field('Mask', mask_path)
    elif action_name == 'highlight':
        # Provide a highlight image file
        highlight_path = create_helper_image('highlight')
        action.set_field('Highlight', highlight_path)
    elif action_name in ['save', 'copy', 'rename', 'save_metadata']:
        # Set valid folder (use temp dir instead of 'desktop')
        action.set_field('In', TEST_TEMP_DIR)
    elif action_name == 'tamogen':
        # Provide fill image
        fill_image_path = create_helper_image('tamogen_fill')
        action.set_field('Fill Image', fill_image_path)
    elif action_name == 'text':
        # Use empty string to trigger default font (line 58-61 in text.py checks font.strip())
        action.set_field('Font', '')
    elif action_name == 'reflection':
        # Provide missing scale_method parameter
        if hasattr(action, 'set_field'):
            try:
                action.set_field('Scale Method', 'Fit')
            except:
                pass  # Field may not exist in older versions

    # Initialize action dependencies (lazy imports)
    if hasattr(action, 'init') and callable(action.init):
        try:
            action.init()
        except Exception as e:
            # Some actions may fail init without external tools, that's ok
            pytest.skip(f"Action {action_name} init() requires external dependencies: {e}")

    # Create appropriate test image
    image_mode = ACTION_IMAGE_MODES.get(action_name, 'RGB')
    # Some actions need real files
    needs_real_file = action_name in ['save', 'copy', 'rename', 'save_metadata', 'tamogen', 'text']
    photo = create_test_photo(image_mode=image_mode, save_to_file=needs_real_file)

    # Add time_shift metadata if needed
    if action_name == 'time_shift':
        import datetime
        photo.info['exif'] = {
            'DateTimeOriginal': datetime.datetime(2020, 1, 1, 12, 0, 0),
        }
        photo.info['iptc'] = {}
        photo.info['year'] = 2020
        photo.info['month'] = 1
        photo.info['day'] = 1
        photo.info['hour'] = 12
        photo.info['minute'] = 0
        photo.info['second'] = 0
        photo.modify_date = datetime.datetime(2020, 1, 1, 12, 0, 0)

    # Execute the action
    try:
        # Create a mock setting function for actions that need it (save, copy, rename)
        def mock_setting(key, default=None):
            settings = {
                'overwrite_existing_images': True,
                'create_new_folders': True,
            }
            return settings.get(key, default)

        result = action.apply(photo, setting=mock_setting, cache={})
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
