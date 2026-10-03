# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Configured image-only workflow rendering without ordinary output writes."""

from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, replace
import hashlib
from io import BytesIO
from importlib import import_module
import json
from pathlib import Path
import threading
import time
from typing import Any, Protocol

from PIL import Image

from phatch.core.batch import BatchAction, Failure, _photo, _settings
from phatch.core.manifests import file_fingerprint, job_identity
from phatch.lib.odict import ReadOnlyDict

PURE_ACTIONS = frozenset(
    {
        'autocontrast',
        'background',
        'border',
        'brightness',
        'canvas',
        'color_to_alpha',
        'colorize',
        'contour',
        'contrast',
        'convert_mode',
        'crop',
        'desaturate',
        'effect',
        'equalize',
        'fit',
        'grid',
        'highlight',
        'invert',
        'mask',
        'maximum',
        'median',
        'minimum',
        'mirror',
        'offset',
        'perspective',
        'posterize',
        'rank',
        'reflection',
        'rotate',
        'round',
        'saturation',
        'scale',
        'shadow',
        'sketch',
        'solarize',
        'text',
        'transpose',
        'warm_up',
        'watermark',
    }
)


class PreviewError(ValueError):
    """An invalid request or an exceeded preview resource bound."""


class PreviewAction(BatchAction, Protocol):
    """Legacy action forms provide serialization for an immutable snapshot."""

    def load(self, fields: Mapping[str, str]) -> list[str]: ...
    def _get_fields(self) -> Mapping[str, Any]: ...
    def get_field(
        self, label: str, info: Mapping[str, Any] | None = None
    ) -> Any: ...


@dataclass(frozen=True)
class PreviewOptions:
    size: tuple[int, int] = (512, 512)
    intermediates: bool = True
    full_resolution: bool = False
    crop: tuple[int, int, int, int] | None = None
    max_source_pixels: int = 50_000_000
    max_result_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        if len(self.size) != 2 or any(
            type(value) is not int or not 1 <= value <= 4096
            for value in self.size
        ):
            raise PreviewError(
                'Preview size must have two dimensions from 1 to 4096'
            )
        if self.crop is not None and (
            len(self.crop) != 4
            or any(type(value) is not int for value in self.crop)
            or self.crop[0] < 0
            or self.crop[1] < 0
            or self.crop[2] <= self.crop[0]
            or self.crop[3] <= self.crop[1]
        ):
            raise PreviewError(
                'Crop must be a positive rectangle in full-resolution coordinates'
            )
        for value in (self.max_source_pixels, self.max_result_bytes):
            if type(value) is not int or value < 1:
                raise PreviewError(
                    'Preview resource bounds must be positive integers'
                )


@dataclass(frozen=True)
class PreviewImage:
    label: str
    size: tuple[int, int]
    png: bytes

    def open(self) -> Image.Image:
        """Return a caller-owned image with no dependency on a live stream."""
        with Image.open(BytesIO(self.png)) as image:
            return image.copy()


@dataclass(frozen=True)
class PreviewResult:
    status: str
    before: PreviewImage | None = None
    after: PreviewImage | None = None
    steps: tuple[PreviewImage, ...] = ()
    skipped: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    failure: Failure | None = None
    approximate: bool = False
    cache_hit: bool = False
    cache_key: str = ''
    elapsed: float = 0.0

    @property
    def byte_size(self) -> int:
        images = list(self.steps)
        if self.before:
            images.append(self.before)
        if self.after:
            images.append(self.after)
        return sum(len(image.png) for image in images)


def preview_safe(action: BatchAction) -> bool:
    """Built-ins are audited explicitly; custom actions require an opt-in."""
    module = type(action).__module__
    if module.startswith(('phatch.actions.', 'actions.')):
        return module.rsplit('.', 1)[-1] in PURE_ACTIONS
    return getattr(action, 'preview_safe', False) is True


def snapshot_actions(actions: Sequence[PreviewAction]) -> list[PreviewAction]:
    """Copy only serialized form state, so GUI edits cannot mutate a render."""
    snapshots = []
    for action in actions:
        if not action.is_enabled():
            continue
        if not preview_safe(action):
            # Skipped actions are never constructed, initialized or executed.
            snapshots.append(action)
            continue
        snapshot = type(action)()
        snapshot.load(action.dump()['fields'])
        legacy_fields = import_module('lib.formField')
        for field in snapshot._get_fields().values():
            field.safe = True
            if isinstance(field, legacy_fields.FontFileField):
                legacy_fonts = import_module('lib.fonts')
                field.dictionary = dict(
                    legacy_fonts.font_dictionary(write_cache=False)
                )
        snapshots.append(snapshot)
    return snapshots


def _frame(
    image: Image.Image, label: str, options: PreviewOptions
) -> PreviewImage:
    output = image.copy()
    try:
        if options.crop is not None:
            left, top, right, bottom = options.crop
            if left >= output.width or top >= output.height:
                raise PreviewError('Crop is outside an intermediate image')
            cropped = output.crop(
                (
                    left,
                    top,
                    min(right, output.width),
                    min(bottom, output.height),
                )
            )
            output.close()
            output = cropped
        output.thumbnail(options.size, Image.Resampling.LANCZOS)
        # Transport only pixels; metadata payloads never enter preview results.
        transparency = output.info.get('transparency')
        output.info.clear()
        if output.mode == 'P' and transparency is not None:
            output.info['transparency'] = transparency
        if output.mode not in {
            '1',
            'L',
            'LA',
            'P',
            'RGB',
            'RGBA',
            'I',
            'I;16',
        }:
            converted = output.convert('RGB')
            output.close()
            output = converted
        with BytesIO() as stream:
            output.save(stream, format='PNG')
            payload = stream.getvalue()
        return PreviewImage(label, output.size, payload)
    finally:
        output.close()


def _resource_identity(
    actions: Sequence[PreviewAction], source: Path
) -> tuple[dict[str, object], bool]:
    """Resolve read-only file fields; disable caching for unresolved resources."""
    from phatch.core.resources import resource_identity
    from phatch.lib.metadata import InfoFile

    variables = InfoFile(vars=list(InfoFile.possible_vars)).dump(
        (str(source), str(source.parent))
    )
    with Image.open(source) as image:
        count = getattr(image, 'n_frames', 1)
    variables.update(
        index=0,
        imageindex=0,
        folderindex=0,
        repeatindex=0,
        frameindex=0,
        framecount=count,
    )
    return resource_identity(actions, variables)


class PreviewRenderer:
    """A bounded in-memory cache; each render owns its photo and action state."""

    def __init__(self, *, cache_bytes: int = 64 * 1024 * 1024) -> None:
        if type(cache_bytes) is not int or cache_bytes < 0:
            raise PreviewError('Cache bound must be a nonnegative integer')
        self.cache_bytes = cache_bytes
        self._cache: OrderedDict[str, PreviewResult] = OrderedDict()
        self._bytes = 0
        self._lock = threading.Lock()

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._bytes = 0

    def render(
        self,
        source: Path | str,
        actions: Sequence[PreviewAction],
        options: PreviewOptions | None = None,
        settings: Mapping[str, Any] | None = None,
        *,
        cancel: Callable[[], bool] | None = None,
        progress: Callable[[int, str], None] | None = None,
    ) -> PreviewResult:
        """Render safe configured steps; cancellation never caches a result."""
        started = time.perf_counter()
        options = options or PreviewOptions()
        source = Path(source).expanduser().resolve()
        photo = None
        before = after = None
        steps: list[PreviewImage] = []
        warnings = []
        skipped = tuple(
            action.label
            for action in actions
            if action.is_enabled() and not preview_safe(action)
        )
        key = ''
        label = 'Open image'
        try:
            if cancel and cancel():
                return PreviewResult('cancelled', skipped=skipped)
            enabled = [
                action
                for action in snapshot_actions(actions)
                if preview_safe(action)
            ]
            if len(enabled) > 100:
                raise PreviewError('At most 100 preview steps are supported')
            from phatch.core import api

            if api.assert_safe(enabled):
                raise PreviewError('Preview requires safe action expressions')
            settings = _settings(settings)
            fingerprint = file_fingerprint(source)
            # Pure custom actions may opt into preview without promising resume.
            builtin = all(
                type(action).__module__.startswith(
                    ('phatch.actions.', 'actions.')
                )
                for action in enabled
            )
            resources, cacheable = _resource_identity(enabled, source)
            identity = (
                job_identity(enabled, settings)
                if builtin and cacheable
                else None
            )
            if identity is not None:
                key = hashlib.sha256(
                    json.dumps(
                        {
                            'source': str(source),
                            'fingerprint': fingerprint,
                            'recipe': identity,
                            'resources': resources,
                            'options': asdict(options),
                            'skipped': skipped,
                        },
                        sort_keys=True,
                    ).encode('utf-8')
                ).hexdigest()
                with self._lock:
                    cached = self._cache.get(key)
                    if cached:
                        self._cache.move_to_end(key)
                        return replace(
                            cached,
                            cache_hit=True,
                            elapsed=time.perf_counter() - started,
                        )
            with Image.open(source) as header:
                if header.width * header.height > options.max_source_pixels:
                    raise PreviewError(
                        'Source exceeds the configured preview pixel limit'
                    )
                frame_count = getattr(header, 'n_frames', 1)
                if frame_count > 1:
                    warnings.append('Preview shows the first frame or page')
            photo = _photo(source, enabled, 0, 0, 1)
            dict.update(photo.info, frameindex=0, framecount=frame_count)
            original_size = photo.info['size']
            full = options.full_resolution or options.crop is not None
            if not full:
                for layer in photo.layers.values():
                    layer.image.thumbnail(
                        options.size, Image.Resampling.LANCZOS
                    )
                warnings.append(
                    'Thumbnail processing approximates pixel-based effects and metadata expressions'
                )
            image = photo.get_flattened_image()
            try:
                before = _frame(image, 'Before', options)
            finally:
                image.close()
            used_bytes = len(before.png)
            cache: dict[str, Any] = {}
            for index, action in enumerate(enabled):
                label = action.label
                if progress:
                    progress(index, label)
                if cancel and cancel():
                    return PreviewResult(
                        'cancelled',
                        before=before,
                        skipped=skipped,
                        warnings=tuple(warnings),
                        elapsed=time.perf_counter() - started,
                    )
                action.init()
                previous = [layer.image for layer in photo.layers.values()]
                try:
                    photo = action.apply(photo, ReadOnlyDict(settings), cache)
                finally:
                    current = [layer.image for layer in photo.layers.values()]
                    for old_image in previous:
                        if all(old_image is not image for image in current):
                            old_image.close()
                if any(
                    layer.image.width * layer.image.height
                    > options.max_source_pixels
                    for layer in photo.layers.values()
                ):
                    raise PreviewError(
                        'A workflow step exceeds the preview pixel limit'
                    )
                log = photo.get_log()
                if log:
                    warnings.append(log)
                    photo.clear_log()
                image = photo.get_flattened_image()
                try:
                    after = _frame(image, label, options)
                finally:
                    image.close()
                if options.intermediates:
                    steps.append(after)
                    used_bytes += len(after.png)
                if used_bytes + len(after.png) > options.max_result_bytes:
                    raise PreviewError(
                        'Preview exceeds the configured result byte limit'
                    )
            if cancel and cancel():
                return PreviewResult(
                    'cancelled',
                    skipped=skipped,
                    elapsed=time.perf_counter() - started,
                )
            if file_fingerprint(source) != fingerprint:
                raise PreviewError('Source changed during preview rendering')
            if _resource_identity(enabled, source)[0] != resources:
                raise PreviewError(
                    'A resource changed during preview rendering'
                )
            result = PreviewResult(
                'success',
                before,
                after or before,
                tuple(steps),
                skipped,
                tuple(warnings),
                approximate=not full and before.size != original_size,
                cache_key=key,
                elapsed=time.perf_counter() - started,
            )
            if result.byte_size > options.max_result_bytes:
                raise PreviewError(
                    'Preview exceeds the configured result byte limit'
                )
            if key and result.byte_size <= self.cache_bytes:
                with self._lock:
                    existing = self._cache.pop(key, None)
                    if existing:
                        self._bytes -= existing.byte_size
                    self._cache[key] = result
                    self._bytes += result.byte_size
                    while self._bytes > self.cache_bytes:
                        _, evicted = self._cache.popitem(last=False)
                        self._bytes -= evicted.byte_size
            return result
        except (
            Exception
        ) as exc:  # Preview is an intentional plugin isolation boundary.
            return PreviewResult(
                'failed',
                before=before,
                skipped=skipped,
                warnings=tuple(warnings),
                failure=Failure(label, type(exc).__name__, str(exc)),
                elapsed=time.perf_counter() - started,
            )
        finally:
            if photo is not None:
                for layer in photo.layers.values():
                    layer.image.close()
                photo.close()
