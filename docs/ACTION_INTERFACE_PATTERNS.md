# Phatch Action Interface Patterns

This document explains when to use `pil()` staticmethod vs `apply()` method when implementing Phatch action plugins.

## Overview

Phatch action plugins can implement their image processing logic in two ways:
1. **`pil()` staticmethod** - For pure PIL image transformations (72% of actions)
2. **`apply()` method** - For operations requiring file I/O, metadata, or external tools (28% of actions)

## Pattern: `pil()` Staticmethod

### When to Use

Use `pil()` staticmethod when your action:
- ✅ Performs **pure image transformation** (in-memory PIL operations)
- ✅ Only needs the **image object and parameters**
- ✅ Returns a **modified PIL Image** object
- ✅ Does **NOT** need to access photo metadata (EXIF, filename, etc.)
- ✅ Is **stateless** (no side effects, deterministic)

### Signature

```python
@staticmethod
def function_name(image, param1, param2, ...):
    """Pure image transformation function.

    Args:
        image: PIL Image object
        param1, param2, ...: Action parameters

    Returns:
        PIL Image object (transformed)
    """
    # Perform PIL operations
    result = image.rotate(angle)
    return result

# Register as staticmethod
pil = staticmethod(function_name)
```

### Examples

Actions using `pil()` staticmethod (39 actions):

**Simple Transforms:**
- `rotate.py` - Rotate image by angle
- `mirror.py` - Flip image horizontally/vertically
- `crop.py` - Crop to region
- `canvas.py` - Expand canvas

**Color Adjustments:**
- `brightness.py` - Adjust brightness
- `contrast.py` - Adjust contrast
- `saturation.py` - Adjust saturation
- `colorize.py` - Colorize image

**Filters:**
- `blur.py` - Apply blur filter
- `sharpen.py` - Sharpen image
- `contour.py` - Detect contours
- `effect.py` - Apply PIL ImageFilter effects

**Decorations:**
- `border.py` - Add border
- `round.py` - Round corners
- `shadow.py` - Drop shadow
- `watermark.py` - Add watermark overlay

### Implementation Example

```python
from core import models
from lib.reverse_translation import _t

def init(_inject_deps=None):
    if _inject_deps:
        for name, value in _inject_deps.items():
            globals()[name] = value
        return _inject_deps

    global Image
    from PIL import Image
    return {'Image': Image}

def rotate_image(image, angle):
    """Rotate image by specified angle."""
    return image.rotate(angle, expand=True)

class Action(models.Action):
    label = _t('Rotate')
    author = 'Phatch Team'
    email = 'info@example.com'
    version = '0.1'
    init = staticmethod(init)
    pil = staticmethod(rotate_image)  # ← Register pil() method
    tags = [_t('transform')]

    def interface(self, fields):
        fields[_t('Angle')] = self.SliderField(0, -180, 180)
```

## Pattern: `apply()` Method

### When to Use

Use `apply()` method when your action:
- ✅ Needs to **read/write photo.info** (metadata dictionary)
- ✅ Performs **file I/O operations** (save, copy, rename files)
- ✅ Modifies **EXIF/IPTC metadata** (timestamps, tags, geolocation)
- ✅ Calls **external tools** (ImageMagick, jpegtran, exiftool)
- ✅ Requires **complex workflow** with multiple steps
- ✅ Has **side effects** or is **stateful**

### Signature

```python
def apply(self, photo, setting, cache):
    """Apply action with access to photo context.

    Args:
        self: Action instance (access to fields via self.get_field())
        photo: Photo object with .image (PIL Image) and .info (metadata dict)
        setting: Global settings dictionary
        cache: Cache dictionary for sharing data between actions

    Returns:
        None (modifies photo in-place)
    """
    # Access metadata
    info = photo.info
    filename = info['filename']

    # Modify image
    photo.image = photo.image.resize((800, 600))

    # Update metadata
    info['size'] = photo.image.size
```

### Examples

Actions using `apply()` method (16 actions):

**File Operations:**
- `save.py` - Save image to disk with format conversion
- `copy.py` - Copy image to another location
- `rename.py` - Rename image file

**Metadata Operations:**
- `delete_tags.py` - Remove EXIF/IPTC tags
- `rename_tag.py` - Rename metadata tags
- `write_tag.py` - Write EXIF/IPTC tags
- `save_metadata.py` - Save metadata to file
- `geotag.py` - Add GPS coordinates
- `time_shift.py` - Adjust timestamp metadata

**External Tools:**
- `imagemagick.py` - Call ImageMagick convert command
- `lossless_jpeg.py` - Call jpegtran for lossless operations
- `blender.py` - Call Blender for 3D rendering

**Complex Workflows:**
- `scale.py` - Resize with canvas and DPI metadata updates
- `convert_mode.py` - Change color mode (RGB, CMYK, etc.)
- `transpose.py` - Transpose with EXIF orientation updates
- `geek.py` - Execute custom Python code with full context

### Implementation Example

```python
from core import models
from lib.reverse_translation import _t

class Action(models.Action):
    label = _t('Save')
    author = 'Phatch Team'
    email = 'info@example.com'
    version = '0.1'
    tags = [_t('file')]

    def interface(self, fields):
        fields[_t('File Name')] = self.FileNameField('<filename>')
        fields[_t('Folder')] = self.FolderField('~/Desktop')
        fields[_t('Format')] = self.ChoiceField('JPEG', choices=['JPEG', 'PNG'])

    def apply(self, photo, setting, cache):
        """Save image to disk."""
        # Access metadata
        info = photo.info

        # Get field values (uses metadata for variable expansion)
        filename = self.get_field('File Name', info)
        folder = self.get_field('Folder', info)
        format = self.get_field('Format', info)

        # Construct output path
        output_path = os.path.join(folder, filename)

        # Save image (file I/O operation)
        photo.image.save(output_path, format)

        # Update metadata for next action in chain
        info['output_path'] = output_path
```

## Key Differences

| Aspect | `pil()` Staticmethod | `apply()` Method |
|--------|---------------------|------------------|
| **Access Level** | Image + parameters only | Photo object + metadata + settings |
| **Metadata** | ❌ Cannot access photo.info | ✅ Full access to photo.info |
| **File I/O** | ❌ No file operations | ✅ Can read/write files |
| **Side Effects** | ❌ Pure function (stateless) | ✅ Can have side effects |
| **External Tools** | ❌ Cannot call external programs | ✅ Can call subprocess |
| **Fields Access** | ❌ Parameters passed directly | ✅ Use self.get_field() with variable expansion |
| **Return Value** | ✅ Returns modified PIL Image | ❌ Modifies photo in-place (returns None) |
| **Typical Use** | Image transformations, filters, effects | File operations, metadata, external tools |
| **Prevalence** | 72% (39/54 actions) | 28% (16/54 actions) |

## Variable Expansion

The `apply()` method provides access to **variable expansion** in field values:

```python
# In interface()
fields[_t('Output')] = self.FolderField('~/Desktop/<filename>_edited')

# In apply()
output = self.get_field('Output', info)  # Expands <filename> from metadata
# If info['filename'] = 'photo.jpg', output = '~/Desktop/photo_edited'
```

Available variables in `photo.info`:
- `<filename>` - Base filename without extension
- `<type>` - File extension
- `<folder>` - Parent folder path
- `<width>`, `<height>` - Image dimensions
- `<dpi>` - Image resolution
- `<Exif_*>` - EXIF metadata tags
- Custom variables set by previous actions

## Migration Guide

### When to Convert `pil()` to `apply()`

Convert from `pil()` to `apply()` if you need to:

1. **Access metadata:**
   ```python
   # Before (pil): Cannot access filename
   def process(image):
       return image

   # After (apply): Can access filename
   def apply(self, photo, setting, cache):
       filename = photo.info['filename']
       photo.image = process_with_filename(photo.image, filename)
   ```

2. **Save files or perform I/O:**
   ```python
   # Before (pil): Returns image only
   def process(image):
       return image.filter(ImageFilter.BLUR)

   # After (apply): Can save intermediate results
   def apply(self, photo, setting, cache):
       photo.image = photo.image.filter(ImageFilter.BLUR)
       photo.image.save('/tmp/debug.png')  # Debug output
   ```

3. **Update metadata for next action:**
   ```python
   # Before (pil): Cannot update metadata
   def resize(image, width, height):
       return image.resize((width, height))

   # After (apply): Update size metadata
   def apply(self, photo, setting, cache):
       width = self.get_field('Width', photo.info)
       height = self.get_field('Height', photo.info)
       photo.image = photo.image.resize((width, height))
       photo.info['size'] = (width, height)  # Update for next action
   ```

### When to Convert `apply()` to `pil()`

Convert from `apply()` to `pil()` if:

1. **No metadata access needed:**
   ```python
   # Before (apply): Unnecessarily complex
   def apply(self, photo, setting, cache):
       angle = self.get_field('Angle', photo.info)
       photo.image = photo.image.rotate(angle)

   # After (pil): Simpler
   @staticmethod
   def rotate(image, angle):
       return image.rotate(angle)

   pil = staticmethod(rotate)
   ```

2. **Pure transformation:**
   ```python
   # Before (apply): Side effects not needed
   def apply(self, photo, setting, cache):
       photo.image = photo.image.convert('L')

   # After (pil): More testable
   @staticmethod
   def grayscale(image):
       return image.convert('L')

   pil = staticmethod(grayscale)
   ```

## Testing Implications

### Testing `pil()` Methods

Simpler to test - pure functions:

```python
def test_rotate_90_degrees():
    """Test rotation function directly."""
    from phatch.actions import rotate

    # Create test image
    image = Image.new('RGB', (100, 50), 'red')

    # Call pil() directly
    result = rotate.rotate_image(image, 90)

    # Assert dimensions swapped
    assert result.size == (50, 100)
```

### Testing `apply()` Methods

Requires photo object setup:

```python
def test_save_action(tmp_path):
    """Test save action with metadata."""
    from phatch.actions.save import Action
    from phatch.core.api import Photo

    # Create test photo with metadata
    image = Image.new('RGB', (100, 100), 'red')
    photo = Photo(image)
    photo.info['filename'] = 'test.jpg'

    # Create action and apply
    action = Action()
    action.set_field('Folder', str(tmp_path))
    action.apply(photo, {}, {})

    # Assert file was saved
    assert (tmp_path / 'test.jpg').exists()
```

## Best Practices

1. **Prefer `pil()` when possible** - Simpler, more testable, easier to understand
2. **Use `apply()` when necessary** - When you need metadata or file I/O
3. **Keep `pil()` functions pure** - No side effects, deterministic
4. **Document metadata dependencies** - Specify what metadata fields are read/written
5. **Use type hints** - Helps IDE support and catches errors early
6. **Test both patterns** - Unit tests for `pil()`, integration tests for `apply()`

## Historical Context

The dual interface pattern exists because:

1. **Performance** - `pil()` staticmethods are faster (no object overhead)
2. **Testability** - Pure functions are easier to unit test
3. **Simplicity** - Most actions (72%) don't need metadata access
4. **Flexibility** - `apply()` provides full context when needed
5. **Pipeline** - Phatch chains actions together, some need to pass metadata

## Summary

**Use `pil()` staticmethod for:**
- ✅ Pure image transformations (rotate, crop, filter)
- ✅ Stateless operations
- ✅ When you only need image + parameters

**Use `apply()` method for:**
- ✅ File operations (save, copy, rename)
- ✅ Metadata operations (EXIF, tags, timestamps)
- ✅ External tool integration
- ✅ Complex workflows requiring context

**Golden Rule:** If you're just transforming the image in memory, use `pil()`. If you need to interact with files, metadata, or external tools, use `apply()`.

---

**Last Updated:** 2025-10-10
**Author:** Phatch Development Team
**Related:** See `phatch/core/models.py` for base Action class implementation
