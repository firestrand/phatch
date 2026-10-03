# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Runtime encoder diagnostics without encoding files or launching tools."""

import shutil
from typing import Any

from PIL import Image, __version__ as pillow_version, features


class UnsupportedCodecError(ValueError):
    """The requested encoder is unavailable in this Pillow installation."""


def encoder_available(format: str) -> bool:
    """Check registration and native codec support for modern encoders."""
    Image.init()
    format = format.upper()
    if format not in Image.SAVE:
        return False
    feature = {'WEBP': 'webp', 'AVIF': 'avif'}.get(format)
    return feature is None or features.check(feature) is True


def resolve_encoder(format: str, fallback: str = 'error') -> str:
    """Resolve an explicitly requested fallback; never silently change format."""
    if fallback not in {'error', 'png'}:
        raise ValueError('Format fallback must be error or png')
    format = format.upper()
    if encoder_available(format):
        return format
    if fallback == 'png' and encoder_available('PNG'):
        return 'PNG'
    raise UnsupportedCodecError(
        f'{format} encoder is unavailable. Install Pillow with {format} support '
        'or explicitly select PNG fallback.'
    )


def encoder_options(
    format: str,
    *,
    quality: int = 80,
    lossless: bool = False,
    effort: int = 4,
    speed: int = 6,
    max_threads: int = 1,
) -> dict[str, int | bool]:
    """Validate modern encoder controls independently of action field parsing."""
    format = format.upper()
    values = [(quality, 0, 100, 'Quality')]
    if format == 'WEBP':
        values.append((effort, 0, 6, 'WebP effort'))
        if not isinstance(lossless, bool):
            raise ValueError('WebP lossless must be a boolean')
    elif format == 'AVIF':
        values.extend(
            [
                (speed, 0, 10, 'AVIF speed'),
                (max_threads, 1, 64, 'Encoder threads'),
            ]
        )
    else:
        return {}
    for value, minimum, maximum, name in values:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not minimum <= value <= maximum
        ):
            raise ValueError(
                f'{name} must be an integer from {minimum} to {maximum}'
            )
    if format == 'WEBP':
        return {
            'quality': quality,
            'lossless': lossless,
            'method': effort,
            'exact': lossless,
        }
    return {'quality': quality, 'speed': speed, 'max_threads': max_threads}


def capability_report() -> dict[str, Any]:
    """Describe registered codecs and optional tools without recording paths."""
    Image.init()
    return {
        'pillow_version': pillow_version,
        'encoders': {
            name: encoder_available(name) for name in sorted(Image.SAVE)
        },
        'decoders': sorted(Image.OPEN),
        'native_features': {
            name: features.check(name) for name in features.get_supported()
        },
        'external_tools': {
            name: shutil.which(name) is not None
            for name in (
                'convert',
                'magick',
                'tiffcp',
                'tiffinfo',
                'exiftool',
                'jpegtran',
            )
        },
    }
