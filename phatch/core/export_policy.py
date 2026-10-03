# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Native metadata and color policies, independent of the GUI and pyexiv2."""

from dataclasses import dataclass, field
from io import BytesIO
from collections.abc import Iterable
from typing import Any
import re

from PIL import ExifTags, Image, ImageCms, PngImagePlugin

METADATA_FORMATS = frozenset({'JPEG', 'PNG', 'TIFF', 'WEBP', 'AVIF'})
PROFILE_FORMATS = METADATA_FORMATS
PRIVATE_TAGS = frozenset(
    {
        270,
        271,
        272,
        305,
        315,
        316,
        33432,
        34853,
        37500,
        37510,
        42032,
        42033,
        42034,
        42035,
        42036,
        42037,
    }
)
TAG_NAMES = {name: number for number, name in ExifTags.TAGS.items()}


class ExportPolicyError(ValueError):
    """An invalid or unsupported export policy."""


def validate_profile_mode(image: Image.Image, profile: bytes | None) -> None:
    """Reject embedding a profile whose color space no longer matches pixels."""
    if not profile:
        return
    color_space = ImageCms.ImageCmsProfile(
        BytesIO(profile)
    ).profile.xcolor_space.strip()
    modes = {
        'RGB': {'RGB', 'RGBA', 'P'},
        'GRAY': {'1', 'L', 'LA'},
        'CMYK': {'CMYK'},
        'Lab': {'LAB'},
    }
    if image.mode not in modes.get(color_space, set()):
        raise ExportPolicyError(
            'Preserved ICC profile does not match the output pixel mode; '
            'select convert-to-sRGB color policy'
        )


@dataclass(frozen=True)
class SourceMetadata:
    exif: bytes = b''
    icc_profile: bytes | None = None
    xmp: bytes | None = None
    text: dict[str, str] = field(default_factory=dict)
    has_iptc: bool = False


def capture_metadata(image: Image.Image) -> SourceMetadata:
    """Capture the source before transformations can discard image info."""
    exif = image.getexif()
    profile = image.info.get('icc_profile')
    tiff_tags = getattr(image, 'tag_v2', {})
    if image.format == 'TIFF':
        # Pillow can retain an earlier page's info when the next tag is absent.
        profile = tiff_tags.get(34675)
    xmp = image.info.get('xmp') or image.info.get('XML:com.adobe.xmp')
    if isinstance(xmp, str):
        xmp = xmp.encode('utf-8')
    return SourceMetadata(
        exif=exif.tobytes() if exif else b'',
        icc_profile=profile if isinstance(profile, bytes) else None,
        xmp=xmp if isinstance(xmp, bytes) else None,
        text={
            key: value
            for key, value in image.info.items()
            if isinstance(key, str)
            and isinstance(value, str)
            and key not in {'Format', 'format', 'XML:com.adobe.xmp'}
            and image.format == 'PNG'
        },
        has_iptc=bool(
            image.info.get('photoshop')
            or image.info.get('iptc')
            or tiff_tags.get(33723)
            or tiff_tags.get(34377)
        ),
    )


def selected_tag_ids(tags: str | Iterable[str | int]) -> set[int]:
    """Parse EXIF tag names or numeric IDs; reject unknown selections."""
    values = tags.split(',') if isinstance(tags, str) else tags
    result = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text.isdecimal():
            number = int(text)
            if not 0 <= number <= 65535:
                raise ExportPolicyError('EXIF tag number is outside its range')
        elif text in TAG_NAMES:
            number = TAG_NAMES[text]
        else:
            raise ExportPolicyError('Unknown EXIF tag name')
        result.add(number)
    return result


def _exif(
    source: SourceMetadata, policy: str, tags: set[int], size: tuple[int, int]
) -> bytes:
    if policy == 'strip' or not source.exif:
        return b''
    metadata = Image.Exif()
    metadata.load(source.exif)
    # These TIFF payloads have independent export/privacy controls.
    for tag in (700, 33723, 34377, 34675):
        if tag in metadata:
            del metadata[tag]
    if policy == 'selected':
        selected = Image.Exif()
        for tag in tags:
            if tag in metadata and tag not in {34665, 34853}:
                selected[tag] = metadata[tag]
        nested = metadata.get_ifd(34665) if 34665 in metadata else {}
        nested = {
            tag: value
            for tag, value in nested.items()
            if tag in tags and tag != 40965
        }
        if nested:
            selected[34665] = nested
        if 34853 in tags and 34853 in metadata:
            selected[34853] = metadata.get_ifd(34853)
        metadata = selected
    elif policy == 'sharing':
        for tag in PRIVATE_TAGS:
            if tag in metadata:
                del metadata[tag]
        if 34665 in metadata:
            nested = metadata.get_ifd(34665)
            for tag in PRIVATE_TAGS:
                nested.pop(tag, None)
    if not metadata:
        return b''
    # Pixels have already been oriented by Photo; do not encode a second turn.
    metadata[274] = 1
    metadata[256], metadata[257] = size
    if 34665 in metadata:
        value = metadata[34665]
        nested = value if isinstance(value, dict) else metadata.get_ifd(34665)
        nested[40962], nested[40963] = size
    return metadata.tobytes()


def prepare_export(
    image: Image.Image,
    source: SourceMetadata,
    format: str,
    metadata_policy: str = 'preserve',
    color_policy: str = 'preserve',
    metadata_tags: str | Iterable[str | int] = '',
) -> tuple[Image.Image, dict[str, Any], list[str]]:
    """Return a private image copy, encoder options and preservation warnings."""
    if metadata_policy not in {'preserve', 'strip', 'selected', 'sharing'}:
        raise ExportPolicyError('Unknown metadata policy')
    if color_policy not in {'preserve', 'srgb'}:
        raise ExportPolicyError('Unknown color policy')
    tags = (
        selected_tag_ids(metadata_tags)
        if metadata_policy == 'selected'
        else set()
    )
    output = image.copy()
    # Do not let Pillow inherit metadata behind a policy's explicit options.
    transparency = output.info.get('transparency')
    if output.mode not in {'P', 'L', 'RGB'} or (
        output.mode == 'RGB' and not isinstance(transparency, tuple)
    ):
        transparency = None
    output.info.clear()
    if transparency is not None:
        output.info['transparency'] = transparency
    options: dict[str, Any] = {}
    warnings: list[str] = []
    profile = source.icc_profile
    try:
        if color_policy == 'srgb':
            target = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB'))
            alpha_image = (
                output.convert('RGBA') if transparency is not None else output
            )
            alpha = (
                alpha_image.getchannel('A')
                if alpha_image.mode in {'RGBA', 'LA', 'PA'}
                else None
            )
            if alpha_image is not output:
                alpha_image.close()
            base = (
                output.convert('RGB')
                if output.mode in {'RGBA', 'P', 'LA'}
                else output
            )
            converted = None
            try:
                if profile:
                    original = ImageCms.ImageCmsProfile(BytesIO(profile))
                    converted = ImageCms.profileToProfile(
                        base, original, target, outputMode='RGB'
                    )
                    if converted is None:
                        raise ExportPolicyError(
                            'ICC conversion produced no image'
                        )
                else:
                    converted = base.convert('RGB')
                    warnings.append('No source ICC profile; assuming sRGB')
                if alpha is not None:
                    converted.putalpha(alpha)
            except BaseException:
                if converted is not None:
                    converted.close()
                raise
            finally:
                if alpha is not None:
                    alpha.close()
                if base is not output:
                    base.close()
            output.close()
            output = converted
            profile = target.tobytes()
        if profile:
            if format in PROFILE_FORMATS:
                options['icc_profile'] = profile
            else:
                warnings.append(
                    'Output format cannot preserve the ICC profile'
                )
        if source.exif and metadata_policy != 'strip':
            if format in METADATA_FORMATS:
                options['exif'] = _exif(
                    source, metadata_policy, tags, output.size
                )
            else:
                warnings.append('Output format cannot preserve EXIF metadata')
        elif format in METADATA_FORMATS:
            options['exif'] = b''
        if metadata_policy == 'preserve':
            if source.xmp:
                # Keep orientation consistent in ordinary XMP attributes/elements.
                xmp = re.sub(
                    rb'(tiff:Orientation=["\'])\d+(["\'])',
                    rb'\g<1>1\2',
                    source.xmp,
                )
                xmp = re.sub(
                    rb'(<tiff:Orientation>)\d+(</tiff:Orientation>)',
                    rb'\g<1>1\2',
                    xmp,
                )
                if format in {'JPEG', 'WEBP', 'AVIF'}:
                    options['xmp'] = xmp
                elif format == 'PNG':
                    text = PngImagePlugin.PngInfo()
                    for key, value in source.text.items():
                        text.add_text(key, value)
                    text.add_itxt('XML:com.adobe.xmp', xmp.decode('utf-8'))
                    options['pnginfo'] = text
                elif format == 'TIFF':
                    exif = Image.Exif()
                    exif.load(options.get('exif', b''))
                    exif[700] = xmp
                    options['exif'] = exif
                else:
                    warnings.append(
                        'Output format cannot preserve XMP metadata'
                    )
            elif source.text:
                if format == 'PNG':
                    text = PngImagePlugin.PngInfo()
                    for key, value in source.text.items():
                        text.add_text(key, value)
                    options['pnginfo'] = text
                else:
                    warnings.append(
                        'Output format cannot preserve PNG text metadata'
                    )
            if source.has_iptc:
                warnings.append('Native export cannot preserve IPTC metadata')
        return output, options, warnings
    except BaseException:
        output.close()
        raise
