# Phatch - Photo Batch Processor
# Copyright (C) 2007-2025 www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/

"""Pillow version compatibility helpers.

This module provides compatibility functions for Pillow 10+ API changes.

Key changes in Pillow 10+:
- Image.ANTIALIAS renamed to Image.LANCZOS
- Image.LINEAR renamed to Image.BILINEAR
- Image.new() requires integer color values (no floats)
- ImageDraw.textsize() deprecated in favor of textbbox()

This module provides backward-compatible helpers to support both
Pillow 9.x and 10.x versions.
"""

# Follows PEP8

from PIL import Image


def get_resample_filter(name='LANCZOS'):
    """Get resampling filter compatible with all Pillow versions.

    Pillow 10+ renamed several resampling constants:
    - ANTIALIAS → LANCZOS
    - LINEAR → BILINEAR

    This function tries the new name first, then falls back to the old name.

    Args:
        name: Filter name ('LANCZOS', 'BILINEAR', 'BICUBIC', 'NEAREST', 'BOX', 'HAMMING')
             Defaults to 'LANCZOS' (highest quality).

    Returns:
        PIL Image resampling constant (integer)

    Raises:
        AttributeError: If no resampling filter found for the given name

    Examples:
        >>> from PIL import Image
        >>> resample = get_resample_filter('LANCZOS')
        >>> image.resize((100, 100), resample)

        >>> # Works with both old and new Pillow versions
        >>> filter = get_resample_filter('BILINEAR')
    """
    # Pillow 10+ renames: new_name → old_name fallback
    COMPAT_MAP = {
        'LANCZOS': ('LANCZOS', 'ANTIALIAS'),  # Try new, fallback to old
        'BILINEAR': ('BILINEAR', 'LINEAR'),
        # These didn't change but included for completeness
        'BICUBIC': ('BICUBIC',),
        'NEAREST': ('NEAREST',),
        'BOX': ('BOX',),
        'HAMMING': ('HAMMING',),
    }

    names = COMPAT_MAP.get(name, (name,))
    for filter_name in names:
        if hasattr(Image, filter_name):
            return getattr(Image, filter_name)

    # No filter found
    raise AttributeError(
        f"No resampling filter found for '{name}'. "
        f"Available filters: {', '.join(COMPAT_MAP.keys())}"
    )


def ensure_int_color(color):
    """Ensure color tuple contains integers (Pillow 10+ requirement).

    Pillow 10+ requires integer values for Image.new() color parameter.
    Earlier versions accepted floats but this caused issues.

    Args:
        color: Color as (R, G, B) or (R, G, B, A) tuple.
               Values can be int or float.

    Returns:
        Color tuple with integer values

    Examples:
        >>> ensure_int_color((255.0, 128.5, 0.2))
        (255, 128, 0)

        >>> ensure_int_color((255, 255, 255, 128.0))
        (255, 255, 255, 128)

        >>> # Already integers - returns unchanged
        >>> ensure_int_color((255, 128, 0))
        (255, 128, 0)
    """
    return tuple(int(c) for c in color)


# Resampling filter aliases for convenience
LANCZOS = get_resample_filter('LANCZOS')
BILINEAR = get_resample_filter('BILINEAR')
BICUBIC = get_resample_filter('BICUBIC')
NEAREST = get_resample_filter('NEAREST')
