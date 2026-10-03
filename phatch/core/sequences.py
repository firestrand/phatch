# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit bounded frame/page processing and atomic sequence encoding."""

from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
import math
from typing import Any

from PIL import Image

from phatch.core.export_policy import prepare_export, validate_profile_mode
from phatch.lib.atomic import AtomicOutput, CollisionPolicy

POLICIES = frozenset({'reject', 'first', 'extract', 'preserve'})
ANIMATION_FORMATS = frozenset({'GIF', 'PNG', 'WEBP', 'AVIF'})
PAGE_FORMATS = frozenset({'TIFF'})


def workflow_settings(
    actions: Sequence[Any], settings: Mapping[str, Any]
) -> dict[str, Any]:
    """Explicit batch settings override recipe-level Save policy controls."""
    result = dict(settings)
    for key, label in (
        ('animation_policy', 'Animation Policy'),
        ('page_policy', 'Page Policy'),
    ):
        if result.get(key) is not None:
            continue
        selected = set()
        for action in actions:
            if not action.is_enabled():
                continue
            value = action.dump()['fields'].get(label, 'inherit')
            if value != 'inherit':
                selected.add(value)
        if len(selected) > 1:
            raise SequenceError(f'Conflicting recipe {label} controls')
        result[key] = next(iter(selected), 'reject')
    return result


class SequenceError(ValueError):
    """An unsupported sequence policy, action or resource requirement."""


@dataclass(frozen=True)
class SequenceInfo:
    format: str
    count: int
    kind: str
    durations: tuple[int | float, ...]
    loop: int | None
    default_image: bool = False
    sizes: tuple[tuple[int, int], ...] = ()


def inspect_sequence(
    path: Path,
    settings: Mapping[str, Any],
    cancel: Callable[[], bool] | None = None,
) -> SequenceInfo:
    with Image.open(path) as image:
        count = getattr(image, 'n_frames', 1)
        format = image.format or ''
        kind = 'pages' if format in PAGE_FORMATS else 'animation'
        maximum = settings.get('max_sequence_frames', 1000)
        budget = settings.get('sequence_memory_bytes', 256 * 1024 * 1024)
        if (
            type(maximum) is not int
            or maximum < 1
            or type(budget) is not int
            or budget < 1
        ):
            raise SequenceError(
                'Sequence frame and memory limits must be positive integers'
            )
        if count > maximum:
            raise SequenceError(
                'Sequence exceeds the configured frame/page limit'
            )
        loop = image.info.get('loop')
        if loop is not None and (type(loop) is not int or loop < 0):
            raise SequenceError('Invalid animation loop count')
        default_image = bool(image.info.get('default_image', False))
        durations = []
        sizes = []
        estimated = 0
        for index in range(count):
            if cancel and cancel():
                raise InterruptedError('Sequence decoding cancelled')
            image.seek(index)
            estimated += image.width * image.height * 4
            if count > 1 and estimated > budget:
                raise SequenceError(
                    'Decoded sequence exceeds the configured memory budget'
                )
            if count > 1:
                image.load()
            orientation = image.getexif().get(274, 1)
            sizes.append(
                image.size[::-1]
                if format != 'TIFF' and orientation in {5, 6, 7, 8}
                else image.size
            )
            duration = image.info.get('duration', 0)
            if (
                type(duration) not in {int, float}
                or not math.isfinite(duration)
                or not 0 <= duration <= 100000000
            ):
                raise SequenceError('Invalid frame duration')
            durations.append(duration)
        return SequenceInfo(
            format,
            count,
            kind,
            tuple(durations),
            loop,
            default_image,
            tuple(sizes),
        )


def policy_for(info: SequenceInfo, settings: Mapping[str, Any]) -> str:
    policy = settings.get(
        'page_policy' if info.kind == 'pages' else 'animation_policy', 'reject'
    )
    if not isinstance(policy, str) or policy not in POLICIES:
        raise SequenceError(
            'Expected reject, first, extract or preserve sequence policy'
        )
    return policy


def validate_workflow(
    info: SequenceInfo, actions: Sequence[Any], settings: Mapping[str, Any]
) -> str:
    policy = policy_for(info, settings)
    if info.count <= 1:
        return policy
    if policy == 'reject':
        raise SequenceError(
            f'Input has {info.count} {info.kind}; select an explicit policy'
        )
    if policy == 'first':
        return policy
    from phatch.core.workflow_preview import PURE_ACTIONS

    for action in actions:
        module = type(action).__module__
        name = module.rsplit('.', 1)[-1]
        built_in = module.startswith(('phatch.actions.', 'actions.'))
        allowed = built_in and (
            name in PURE_ACTIONS
            or name == 'save'
            or (name == 'variants' and policy == 'extract')
        )
        if not allowed and getattr(action, 'sequence_safe', False) is not True:
            raise SequenceError(
                f'Action {action.label} does not support {policy} sequences'
            )
    return policy


def extraction_path(path: Path | str, index: int) -> Path:
    path = Path(path)
    return path.with_name(f'{path.stem}-frame-{index:04d}{path.suffix}')


def attach_sequence(
    photo: Any,
    members: list[Any],
    info: SequenceInfo,
    policy: str,
    cancel: Callable[[], bool] | None,
) -> None:
    photo.sequence_members = members
    photo.sequence_info = info
    photo.sequence_policy = policy
    photo.sequence_cancel = cancel
    for index, member in enumerate(members):
        dict.update(member.info, frameindex=index, framecount=info.count)
        if policy == 'extract':
            member.sequence_extract_index = index
    if info.count > 1 and policy == 'first':
        photo.log(
            f'Explicit first {info.kind} policy discarded {info.count - 1} frames/pages\n'
        )


def apply_action(
    photo: Any,
    action: Any,
    setting: Callable[[str], Any],
    cache: dict[str, Any],
) -> Any:
    members = getattr(photo, 'sequence_members', [photo])
    if len(members) == 1:
        return action.apply(photo, setting, cache)
    preserve_save = getattr(
        photo, 'sequence_policy', None
    ) == 'preserve' and type(action).__module__ in {
        'actions.save',
        'phatch.actions.save',
    }
    for index, member in enumerate(members[:1] if preserve_save else members):
        cancel = getattr(photo, 'sequence_cancel', None)
        if cancel and cancel():
            raise InterruptedError('Sequence processing cancelled')
        previous_images = [layer.image for layer in member.layers.values()]
        try:
            updated = (
                action.apply(
                    member, setting, cache.setdefault(f'frame:{index}', {})
                )
                if len(members) > 1
                else action.apply(member, setting, cache)
            )
            if updated is not member:
                raise SequenceError(
                    'Sequence actions must retain the incoming Photo object'
                )
        finally:
            retained = {id(layer.image) for layer in member.layers.values()}
            for image in previous_images:
                if id(image) not in retained:
                    image.close()
            if member is not photo:
                photo.report_files.extend(member.report_files)
                member.report_files.clear()
                photo.report_artifacts.extend(member.report_artifacts)
                member.report_artifacts.clear()
                warning = member.get_log()
                if warning:
                    photo.log(warning)
                    member.clear_log()
    return photo


def close_sequence(photo: Any) -> None:
    for member in getattr(photo, 'sequence_members', [photo]):
        for layer in member.layers.values():
            layer.image.close()
        member.close()


def save_sequence(
    photo: Any,
    filename: str,
    format: str | None,
    save_metadata: bool,
    collision_policy: CollisionPolicy,
    options: Mapping[str, Any],
) -> str | None:
    """Encode composited animation frames or document pages before one commit."""
    from phatch.lib import imtools

    format = format or imtools.get_format_filename(filename)
    info = photo.sequence_info
    supported = PAGE_FORMATS if info.kind == 'pages' else ANIMATION_FORMATS
    if format not in supported:
        raise SequenceError(f'{format} cannot preserve {info.kind}')
    options = dict(options)
    policy = options.pop('metadata_policy', None) or (
        'preserve' if save_metadata else 'strip'
    )
    color = options.pop('color_policy', 'preserve')
    tags = options.pop('metadata_tags', '')
    compression = options.pop('compression.tif', 'none')
    if format == 'TIFF' and compression not in {
        'none',
        'raw',
        '<compression>',
    }:
        options['compression'] = {
            'lzw': 'tiff_lzw',
            'zip': 'tiff_adobe_deflate',
            'g3': 'group3',
            'g4': 'group4',
        }.get(compression, compression)
    with ExitStack() as resources:
        frames = []
        metadata_options = {}
        for member in photo.sequence_members:
            cancel = getattr(photo, 'sequence_cancel', None)
            if cancel and cancel():
                raise InterruptedError('Sequence encoding cancelled')
            pixels = member.get_flattened_image()
            resources.callback(pixels.close)
            prepared, metadata, warnings = prepare_export(
                pixels, member.source_metadata, format, policy, color, tags
            )
            resources.callback(prepared.close)
            frame = imtools.convert_save_mode_by_format(prepared, format)
            resources.callback(frame.close)
            if color == 'preserve':
                validate_profile_mode(frame, metadata.get('icc_profile'))
            frames.append(frame)
            if info.kind == 'pages':
                exif = Image.Exif()
                value = metadata.get('exif', b'')
                if isinstance(value, Image.Exif):
                    exif = value
                else:
                    exif.load(value)
                if any(tag in exif for tag in (34665, 34853)):
                    if options.get('compression'):
                        raise SequenceError(
                            'Native compressed TIFF cannot preserve EXIF/GPS sub-IFDs; '
                            'choose uncompressed TIFF or a metadata policy that removes them'
                        )
                    if len(frames) > 1:
                        raise SequenceError(
                            'Native TIFF cannot relocate EXIF/GPS sub-IFDs on appended pages; '
                            'select page extraction or a metadata policy that removes them'
                        )
                # Per-page options override defaults inherited by append_images.
                frame.encoderinfo = {
                    **metadata,
                    'icc_profile': metadata.get('icc_profile'),
                }
            elif len(frames) == 1:
                metadata_options = metadata
            elif metadata != metadata_options:
                if color == 'preserve' and metadata.get(
                    'icc_profile'
                ) != metadata_options.get('icc_profile'):
                    raise SequenceError(
                        'Animation requires one ICC profile; select '
                        'convert-to-sRGB when frame profiles differ'
                    )
                photo.log(
                    'Animation metadata is container-scoped; '
                    f'frame {len(frames) - 1} metadata differs from the first frame\n'
                )
            for warning in warnings:
                photo.log(warning + '\n')
        if (
            info.kind == 'animation'
            and len({frame.size for frame in frames}) != 1
        ):
            raise SequenceError(
                'Animation transforms must produce consistent frame dimensions'
            )
        options.update(metadata_options)
        options.update(save_all=True, append_images=frames[1:])
        if info.kind == 'animation':
            durations = list(info.durations)
            if info.default_image and format != 'PNG':
                raise SequenceError(
                    'Only APNG preserves an animation with a separate poster image'
                )
            if format == 'GIF' and any(
                duration % 10 for duration in durations
            ):
                raise SequenceError(
                    'GIF durations must be multiples of 10 milliseconds'
                )
            options['duration'] = (
                durations[1:]
                if info.default_image and format == 'PNG'
                else durations
            )
            if info.loop is not None and format != 'AVIF':
                options['loop'] = info.loop
            if info.loop is not None and format == 'AVIF':
                raise SequenceError(
                    'AVIF encoder does not preserve loop counts; choose GIF, PNG or WebP'
                )
            if format == 'GIF':
                # Full composited frames replace previous frames; disposal codes
                # are deliberately normalized while rendered playback is retained.
                options.update(disposal=2, optimize=False)
            elif format == 'PNG':
                options.update(
                    default_image=info.default_image, disposal=0, blend=0
                )
        transaction = AtomicOutput(filename, collision_policy)
        with transaction as temporary:
            frames[0].save(temporary, format=format, **options)
            with Image.open(temporary) as encoded:
                expected = len(frames)
                if getattr(encoded, 'n_frames', 1) != expected:
                    raise SequenceError('Encoder changed the frame/page count')
                for index in range(expected):
                    encoded.seek(index)
                    encoded.load()
                    if info.kind == 'animation':
                        expected_duration = (
                            0
                            if info.default_image and index == 0
                            else durations[index]
                        )
                        if (
                            abs(
                                encoded.info.get('duration', 0)
                                - expected_duration
                            )
                            > 0.001
                        ):
                            raise SequenceError('Encoder changed frame timing')
                        if (
                            info.loop is not None
                            and encoded.info.get('loop') != info.loop
                        ):
                            raise SequenceError(
                                'Encoder changed animation loop count'
                            )
                    if encoded.size != frames[index].size:
                        raise SequenceError(
                            'Encoded frame/page dimensions changed'
                        )
        if transaction.committed is not None:
            with Image.open(transaction.committed) as encoded:
                photo.append_to_report(str(transaction.committed), encoded)
            return str(transaction.committed)
    return None
