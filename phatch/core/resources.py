# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only external-file identities shared by previews and resume."""

from collections.abc import Iterator, Mapping, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any

from PIL import Image

from phatch.core.manifests import file_fingerprint


class ResourceError(ValueError):
    """A dependency cannot be resolved without executing a workflow."""


def _resource_fields(actions: Sequence[Any]) -> list[tuple[str, str, Any]]:
    # Legacy plugins use lib.formField, which has distinct class identities.
    legacy = import_module('lib.formField')
    modern = import_module('phatch.lib.formField')
    result = []
    for action in actions:
        declared = getattr(action, 'resource_fields', ())
        if not isinstance(declared, (tuple, list)) or not all(
            isinstance(label, str) for label in declared
        ):
            raise ResourceError(
                'resource_fields must be a list of field labels'
            )
        fields = action._get_fields() if hasattr(action, '_get_fields') else {}
        if any(label not in fields for label in declared):
            raise ResourceError(
                f'{action.label} declares an unknown resource field'
            )
        for label, field in fields.items():
            if (
                isinstance(field, (legacy.ReadFileField, modern.ReadFileField))
                or label in declared
            ):
                result.append((action.label, label, field))
    return result


def resource_identity(
    actions: Sequence[Any],
    variables: Mapping[str, Any],
    *,
    fingerprints: dict[str, object] | None = None,
    fingerprint: bool = True,
) -> tuple[dict[str, object], bool]:
    """Fingerprint declared file fields; mark unknown expressions unresolved.

    Only simple variable substitution is performed. Plugin application and
    expression evaluation never run while determining dependencies.
    """
    from phatch.core.batch import _template

    legacy = import_module('lib.formField')
    modern = import_module('phatch.lib.formField')
    identities: dict[str, object] = {}
    fingerprints = {} if fingerprints is None else fingerprints
    resolved = True
    for action, label, field in _resource_fields(actions):
        value = _template(field.get_as_string(), variables)
        if value is None:
            resolved = False
            continue
        try:
            if (
                isinstance(field, (legacy.FontFileField, modern.FontFileField))
                and field.dictionary is None
            ):
                fonts = import_module(
                    'lib.fonts'
                    if isinstance(field, legacy.FontFileField)
                    else 'phatch.lib.fonts'
                )
                field.dictionary = dict(
                    fonts.font_dictionary(write_cache=False)
                )
            path = field.to_python(value, label)
            if path:
                resource = Path(path).expanduser().resolve()
                name = str(resource)
                if name not in fingerprints:
                    fingerprints[name] = (
                        file_fingerprint(resource) if fingerprint else None
                    )
                identities[name] = fingerprints[name]
        except Exception as exc:  # Legacy/plugin field conversion boundary.
            if not fingerprint:
                resolved = False
                continue
            raise ResourceError(
                f'Cannot fingerprint {action}.{label}: {exc}'
            ) from exc
    return identities, resolved


def _input_resource_contexts(
    source: Path,
    context: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> Iterator[dict[str, Any]]:
    """Yield file context without evaluating dynamic action expressions."""
    from phatch.lib.metadata import InfoFile

    root = context.get('root') or source.parent
    variables = InfoFile(vars=list(InfoFile.possible_vars)).dump(
        (str(source), str(root))
    )
    index = context.get('index', 0)
    repeat = settings.get('repeat', 1)
    with Image.open(source) as image:
        count = getattr(image, 'n_frames', 1)
        policy = settings.get(
            'page_policy' if image.format == 'TIFF' else 'animation_policy'
        )
    if count > settings.get('max_sequence_frames', 1000):
        raise ResourceError(
            'Sequence exceeds the resource-resolution frame limit'
        )
    frame_count = count if policy in {'extract', 'preserve'} else 1
    for repeat_index in range(repeat):
        for frame_index in range(frame_count):
            variables.update(
                index=index * repeat + repeat_index,
                imageindex=index,
                repeatindex=repeat_index,
                folderindex=context.get('folder_index', 0),
                frameindex=frame_index,
                framecount=count,
            )
            yield variables.copy()


def input_resource_identity(
    actions: Sequence[Any],
    source: Path,
    context: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> dict[str, object]:
    """Fingerprint every resolved repeat/frame dependency for verified resume."""
    if not _resource_fields(actions):
        return {}
    identities: dict[str, object] = {}
    for variables in _input_resource_contexts(source, context, settings):
        fingerprints, resolved = resource_identity(
            actions, variables, fingerprints=identities
        )
        if not resolved:
            raise ResourceError(
                'Cannot resolve resource expression from file/index context; use a resolved path or run without a manifest'
            )
        identities.update(fingerprints)
    stable = {}
    for name, content in identities.items():
        resource = Path(name)
        logical = None
        for key in ('PHATCH_DATA_PATH', 'PHATCH_IMAGE_PATH', 'PHATCH_LOCALE_PATH', 'PHATCH_DOCS_PATH'):
            root = settings.get(key)
            if root and resource.is_relative_to(Path(root)):
                logical = key + '/' + str(resource.relative_to(Path(root)))
                break
        if logical is None:
            stable[name] = content
        else:
            stable[logical] = {key: value for key, value in content.items() if key != 'mtime_ns'}
    return stable


def input_resource_paths(
    actions: Sequence[Any],
    source: Path,
    context: Mapping[str, Any],
    settings: Mapping[str, Any],
) -> tuple[set[Path], bool]:
    """Resolve known read paths for planning without hashing resource contents."""
    if not _resource_fields(actions):
        return set(), True
    paths: set[Path] = set()
    resolved = True
    for variables in _input_resource_contexts(source, context, settings):
        identities, known = resource_identity(
            actions, variables, fingerprint=False
        )
        paths.update(Path(name) for name in identities)
        resolved = resolved and known
    return paths, resolved
