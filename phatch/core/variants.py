# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named independent size/format branches on the existing atomic photo saver."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib import import_module
import json
from pathlib import Path
import re
from typing import Any

from PIL import Image

from phatch.core.capabilities import encoder_options, resolve_encoder
from phatch.core.manifests import file_fingerprint
from phatch.lib.atomic import AtomicOutput, CollisionPolicy

MAX_DEFINITION_BYTES = 64 * 1024
FORMATS = {
    'jpeg': 'JPEG',
    'jpg': 'JPEG',
    'png': 'PNG',
    'webp': 'WEBP',
    'avif': 'AVIF',
    'tiff': 'TIFF',
    'tif': 'TIFF',
}


class VariantValidationError(ValueError):
    """Invalid variant definition with its document location."""

    def __init__(self, location: str, message: str) -> None:
        self.location = location
        super().__init__(f'{location}: {message}')


@dataclass(frozen=True)
class Variant:
    name: str
    width: int
    height: int
    format: str = 'webp'
    no_upscale: bool = True
    quality: int = 80
    lossless: bool = False
    effort: int = 4
    speed: int = 6
    metadata_policy: str = 'sharing'
    color_policy: str = 'srgb'
    metadata_tags: str = ''

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not re.fullmatch(
            r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', self.name
        ):
            raise VariantValidationError(
                'name',
                'use a unique name of 1–64 letters, digits, underscores or hyphens',
            )
        for label, value in (('width', self.width), ('height', self.height)):
            if type(value) is not int or not 1 <= value <= 100000:
                raise VariantValidationError(
                    label, 'expected an integer from 1 to 100000'
                )
        if (
            not isinstance(self.format, str)
            or self.format.lower() not in FORMATS
        ):
            raise VariantValidationError(
                'format', 'expected JPEG, PNG, WebP, AVIF or TIFF'
            )
        if (
            type(self.no_upscale) is not bool
            or type(self.lossless) is not bool
        ):
            raise VariantValidationError(
                'options', 'no_upscale and lossless must be booleans'
            )
        for label, value, maximum in (
            ('quality', self.quality, 100),
            ('effort', self.effort, 6),
            ('speed', self.speed, 10),
        ):
            if type(value) is not int or not 0 <= value <= maximum:
                raise VariantValidationError(
                    label, f'expected an integer from 0 to {maximum}'
                )
        if not isinstance(
            self.metadata_policy, str
        ) or self.metadata_policy not in {
            'preserve',
            'strip',
            'selected',
            'sharing',
        }:
            raise VariantValidationError(
                'metadata_policy', 'unsupported policy'
            )
        if not isinstance(self.color_policy, str) or self.color_policy not in {
            'preserve',
            'srgb',
        }:
            raise VariantValidationError('color_policy', 'unsupported policy')
        if not isinstance(self.metadata_tags, str):
            raise VariantValidationError('metadata_tags', 'expected a string')

    @property
    def encoder(self) -> str:
        return FORMATS[self.format.lower()]

    def size_for(self, size: tuple[int, int]) -> tuple[int, int]:
        ratio = min(self.width / size[0], self.height / size[1])
        if self.no_upscale:
            ratio = min(1.0, ratio)
        return max(1, round(size[0] * ratio)), max(1, round(size[1] * ratio))


def web_preset() -> tuple[Variant, ...]:
    """Reviewable publishing defaults, not a claim of optimal compression."""
    return tuple(
        Variant(f'{name}-{format}', size, size, format, quality=quality)
        for name, size in (('small', 640), ('medium', 1280), ('large', 1920))
        for format, quality in (('webp', 80), ('avif', 55))
    )


def parse_variants(source: str) -> tuple[Variant, ...]:
    """Read bounded JSON data; definitions do not evaluate expressions."""
    if len(source.encode('utf-8')) > MAX_DEFINITION_BYTES:
        raise VariantValidationError('$', 'definition exceeds the size limit')
    try:
        values = json.loads(source)
    except (ValueError, RecursionError) as exc:
        raise VariantValidationError('$', 'expected a JSON list') from exc
    if not isinstance(values, list) or not 1 <= len(values) <= 100:
        raise VariantValidationError('$', 'expected 1–100 variants')
    variants = []
    names = set()
    for index, value in enumerate(values):
        location = f'variants[{index}]'
        if not isinstance(value, dict):
            raise VariantValidationError(location, 'expected an object')
        try:
            variant = Variant(**value)
        except VariantValidationError as exc:
            raise VariantValidationError(
                location + '.' + exc.location, str(exc)
            ) from exc
        except TypeError as exc:
            raise VariantValidationError(
                location, 'missing or unknown definition fields'
            ) from exc
        if variant.name.casefold() in names:
            raise VariantValidationError(
                location + '.name', 'duplicate variant name'
            )
        names.add(variant.name.casefold())
        variants.append(variant)
    return tuple(variants)


def definitions(fields: Mapping[str, str]) -> tuple[Variant, ...]:
    preset = fields.get('Preset', 'web')
    if preset == 'web':
        return web_preset()
    if preset != 'custom':
        raise VariantValidationError('Preset', 'expected web or custom')
    return parse_variants(fields.get('Variants', '[]'))


def planning_fields(
    fields: Mapping[str, str],
) -> list[tuple[dict[str, str], bool]]:
    """Expand variant destinations as save definitions without plugin execution."""
    saves = []
    for variant in definitions(fields):
        saves.append(
            (
                {
                    'In': fields['In'],
                    'File Name': fields['File Name'] + '-' + variant.name,
                    'As': variant.format.lower(),
                    'Collision Policy': fields.get(
                        'Collision Policy', 'inherit'
                    ),
                    'Format Fallback': fields.get('Format Fallback', 'error'),
                },
                False,
            )
        )
    if fields.get('Write Manifest', 'yes').lower() in {'yes', 'true'}:
        saves.append(
            (
                {
                    'In': fields['In'],
                    'File Name': fields['Manifest Name'],
                    'As': 'json',
                    'Collision Policy': fields.get(
                        'Collision Policy', 'inherit'
                    ),
                },
                True,
            )
        )
    return saves


@dataclass
class _VariantLayer:
    image: Image.Image
    position: tuple[int, int] = (0, 0)


def export_variants(
    photo: Any,
    variants: Sequence[Variant],
    folder: Path | str,
    base_name: str,
    *,
    manifest_name: str | None = None,
    collision_policy: CollisionPolicy = 'replace',
    fallback: str = 'error',
    encoder_threads: int = 1,
    cancel: Callable[[], bool] | None = None,
) -> Any:
    """Export branches from the same incoming photo, restoring its layers.

    Photo is the legacy dynamic boundary. Ordinary outputs and their metadata
    use Photo.save; the JSON association manifest is a separate atomic artifact.
    """
    if not variants:
        raise VariantValidationError('$', 'at least one variant is required')
    for label, value in (
        ('File Name', base_name),
        ('Manifest Name', manifest_name),
    ):
        if value is not None and (
            not value
            or Path(value).name != value
            or '\\' in value
            or value in {'.', '..'}
        ):
            raise VariantValidationError(
                label, 'expected a filename without directory components'
            )
    folder = Path(folder).expanduser().resolve()
    source = Path(photo.info['path']).resolve()
    original_layers = photo.layers
    original_layer_name = photo.current_layer_name
    resolved = [
        (variant, resolve_encoder(variant.encoder, fallback))
        for variant in variants
    ]
    targets = [
        folder
        / f'{base_name}-{variant.name}.{variant.format.lower() if encoder == variant.encoder else "png"}'
        for variant, encoder in resolved
    ]
    manifest = folder / (manifest_name + '.json') if manifest_name else None
    if manifest and hasattr(photo, 'sequence_extract_index'):
        from phatch.core.sequences import extraction_path

        manifest = extraction_path(manifest, photo.sequence_extract_index)
    paths = targets + ([manifest] if manifest else [])
    if len({path.resolve() for path in paths}) != len(paths) or source in {
        path.resolve() for path in paths
    }:
        raise VariantValidationError(
            'outputs',
            'destinations must be unique and must not overlap the source',
        )
    folder.mkdir(parents=True, exist_ok=True)
    base = photo.get_flattened_image()
    records = []
    try:
        for (variant, encoder), target in zip(resolved, targets):
            if cancel and cancel():
                raise InterruptedError('Variant export cancelled')
            size = variant.size_for(base.size)
            branch = (
                base.resize(size, Image.Resampling.LANCZOS)
                if size != base.size
                else base.copy()
            )
            try:
                photo.layers = {original_layer_name: _VariantLayer(branch)}
                options: dict[str, Any] = {
                    'metadata_policy': variant.metadata_policy,
                    'metadata_tags': variant.metadata_tags,
                    'color_policy': variant.color_policy,
                }
                if encoder == 'JPEG':
                    options['quality'] = max(1, variant.quality)
                elif encoder in {'WEBP', 'AVIF'}:
                    options.update(
                        encoder_options(
                            encoder,
                            quality=variant.quality,
                            lossless=variant.lossless,
                            effort=variant.effort,
                            speed=variant.speed,
                            max_threads=encoder_threads,
                        )
                    )
                committed = photo.save(
                    str(target),
                    format=encoder,
                    collision_policy=collision_policy,
                    **options,
                )
                recorded_path = Path(committed) if committed else target
                if not committed and hasattr(photo, 'sequence_extract_index'):
                    from phatch.core.sequences import extraction_path

                    recorded_path = extraction_path(
                        recorded_path, photo.sequence_extract_index
                    )
                records.append(
                    {
                        'name': variant.name,
                        'path': recorded_path.name,
                        'status': 'committed' if committed else 'skipped',
                        'width': size[0],
                        'height': size[1],
                        'format': encoder,
                        'definition': asdict(variant),
                    }
                )
                if encoder != variant.encoder:
                    photo.log(
                        'Explicit PNG fallback used for variant '
                        + variant.name
                        + '\n'
                    )
            finally:
                photo.layers = original_layers
                branch.close()
        if cancel and cancel():
            raise InterruptedError('Variant export cancelled')
        if manifest:
            from phatch.core.destinations import planned_destination

            manifest, manifest_policy = planned_destination(
                photo, manifest, collision_policy
            )
            transaction = AtomicOutput(manifest, manifest_policy)
            with transaction as temporary:
                temporary.write_text(
                    json.dumps(
                        {
                            'schema_version': 1,
                            'source': {
                                'name': source.name,
                                'fingerprint': file_fingerprint(source),
                            },
                            'variants': records,
                        },
                        indent=2,
                        sort_keys=True,
                    )
                    + '\n',
                    encoding='utf-8',
                )
            if transaction.committed:
                photo.report_artifacts.append(str(transaction.committed))
            else:
                photo.log('Existing variant manifest skipped\n')
        return photo
    finally:
        photo.layers = original_layers
        photo.current_layer_name = original_layer_name
        base.close()


def variant_action(
    variants: Sequence[Variant],
    output: Path | str,
    *,
    name: str = '<filename>',
    manifest: bool = True,
) -> Any:
    """Construct the standard, serializable Variants action for engine callers."""
    action = import_module('phatch.actions.variants').Action()
    action.set_field_as_string('Preset', 'custom')
    action.set_field_as_string(
        'Variants', json.dumps([asdict(variant) for variant in variants])
    )
    action.set_field_as_string('In', str(output))
    action.set_field_as_string('File Name', name)
    action.set_field_as_string('Write Manifest', 'yes' if manifest else 'no')
    action.set_field_as_string('Manifest Name', name + '-variants')
    return action
