# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Atomic batch journals with content-verified resume, never existence-only."""

from collections.abc import Mapping, Sequence
import hashlib
import importlib.metadata
import inspect
import json
from pathlib import Path
import sys
from typing import Any

from PIL import Image, __version__ as pillow_version

from phatch.lib.atomic import AtomicOutput

MAX_MANIFEST_BYTES = 16 * 1024 * 1024
UNSUPPORTED_ACTIONS = frozenset(
    {
        'geek',
        'imagemagick',
        'blender',
        'lossless_jpeg',
        'copy',
        'rename',
        'save_metadata',
        'geotag',
        'time_shift',
        'write_tag',
        'rename_tag',
        'delete_tags',
    }
)
OPERATIONAL_SETTINGS = frozenset(
    {
        'resume',
        '_cancel_callback',
        'manifest_path',
        'report_path',
        'report_paths',
        'dry_run',
        'verbose',
        'interactive',
        'console',
        'capabilities',
        'stop_for_errors',
        'always_show_status_dialog',
        'check_images_first',
        'recipe_path',
    }
)


class ManifestError(ValueError):
    """A corrupt journal or an unsupported resume contract."""


def file_fingerprint(path: Path) -> dict[str, int | str]:
    """Hash in bounded chunks and reject a file changing during the read."""
    digest = hashlib.sha256()
    before = path.stat()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns, before.st_ino) != (
        after.st_size,
        after.st_mtime_ns,
        after.st_ino,
    ):
        raise ManifestError(
            'A file changed while its content was fingerprinted'
        )
    return {
        'size': after.st_size,
        'mtime_ns': after.st_mtime_ns,
        'sha256': digest.hexdigest(),
    }


def _normalized(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Path):
        return str(value.resolve())
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ManifestError('Manifest setting keys must be strings')
        return {key: _normalized(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    raise ManifestError(
        'A setting cannot be represented in a resume fingerprint'
    )


def _identity(value: Any) -> str:
    try:
        serialized = json.dumps(
            _normalized(value),
            sort_keys=True,
            separators=(',', ':'),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ManifestError(
            'Cannot fingerprint the batch configuration'
        ) from exc
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


def job_identity(actions: Sequence[Any], settings: Mapping[str, Any]) -> str:
    """Fingerprint recipe, settings, plugin implementation and engine code."""
    plugins = []
    for action in actions:
        module = type(action).__module__
        built_in = module.startswith(('phatch.actions.', 'actions.'))
        if (built_in and module.rsplit('.', 1)[-1] in UNSUPPORTED_ACTIONS) or (
            not built_in and getattr(action, 'resumable', False) is not True
        ):
            raise ManifestError(
                'An action does not declare a resumable contract'
            )
        definition = action.dump()
        implementation = inspect.getsourcefile(type(action))
        if not implementation:
            raise ManifestError('Cannot fingerprint an action implementation')
        plugins.append(
            {
                'module': module.removeprefix('phatch.'),
                'definition': definition,
                'version': str(getattr(action, 'version', 'unknown')),
                'code': file_fingerprint(Path(implementation)),
            }
        )
    root = Path(__file__).resolve().parents[1]
    engine = {
        str(path.relative_to(root)): file_fingerprint(path)
        for folder in ('core', 'lib')
        for path in sorted((root / folder).rglob('*.py'))
    }
    return _identity(
        {
            'actions': plugins,
            'settings': {
                key: value
                for key, value in settings.items()
                if key not in OPERATIONAL_SETTINGS
            },
            'engine': engine,
            'pillow': pillow_version,
            'python': list(sys.version_info[:3]),
            'dependencies': sorted(
                (distribution.metadata['Name'], distribution.version)
                for distribution in importlib.metadata.distributions()
            ),
        }
    )


class BatchManifest:
    """One journal owned by one running batch; records commit only on success."""

    def __init__(
        self,
        path: Path | str,
        identity: str,
        *,
        resume: bool = False,
        actions: Sequence[Any] = (),
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.identity = identity
        self.actions = tuple(actions)
        self.settings = dict(settings or {})
        self.records: dict[str, Any] = {}
        if resume:
            self._load()

    def _load(self) -> None:
        try:
            with self.path.open('rb') as stream:
                raw = stream.read(MAX_MANIFEST_BYTES + 1)
            if len(raw) > MAX_MANIFEST_BYTES:
                raise ManifestError('Manifest exceeds the size limit')
            document = json.loads(raw)
        except (OSError, ValueError, RecursionError) as exc:
            raise ManifestError(
                'Cannot read manifest; select an existing valid journal or start a new job'
            ) from exc
        if (
            not isinstance(document, dict)
            or document.get('schema_version') != 1
        ):
            raise ManifestError('Unsupported manifest schema')
        records = document.get('records')
        if not isinstance(records, dict) or len(records) > 100000:
            raise ManifestError('Invalid manifest records')
        for key, record in records.items():
            if not isinstance(key, str) or not isinstance(record, dict):
                raise ManifestError('Invalid manifest record')
            identity = record.get('key')
            if (
                not isinstance(identity, str)
                or len(identity) != 64
                or any(
                    character not in '0123456789abcdef'
                    for character in identity
                )
            ):
                raise ManifestError('Invalid manifest fingerprint')
            if record.get('status') not in {
                'running',
                'complete',
                'incomplete',
            }:
                raise ManifestError('Invalid manifest completion state')
            outputs = record.get('outputs', [])
            if (
                not isinstance(outputs, list)
                or len(outputs) > 10000
                or any(
                    not isinstance(item, dict)
                    or not isinstance(item.get('path'), str)
                    or not isinstance(item.get('fingerprint'), dict)
                    or not isinstance(item.get('kind', 'image'), str)
                    or item.get('kind', 'image') not in {'image', 'artifact'}
                    for item in outputs
                )
            ):
                raise ManifestError('Invalid manifest output records')
        self.records = records

    def key(
        self, source: Path, context: Mapping[str, Any]
    ) -> tuple[str, dict[str, int | str]]:
        fingerprint = file_fingerprint(source)
        from phatch.core.resources import (
            ResourceError,
            input_resource_identity,
        )

        try:
            resources = input_resource_identity(
                self.actions, source, context, self.settings
            )
        except ResourceError as exc:
            raise ManifestError(str(exc)) from exc
        return _identity(
            {
                'job': self.identity,
                'source': str(source),
                'content': fingerprint,
                'context': context,
                'resources': resources,
            }
        ), fingerprint

    def verified_outputs(self, source: Path, key: str) -> list[Path] | None:
        record = self.records.get(str(source))
        if (
            not record
            or record.get('key') != key
            or record['status'] != 'complete'
        ):
            return None
        outputs = []
        for item in record.get('outputs', []):
            output = Path(item['path'])
            try:
                if file_fingerprint(output) != item['fingerprint']:
                    return None
                if item.get('kind', 'image') == 'artifact':
                    with output.open('rb') as stream:
                        raw = stream.read(MAX_MANIFEST_BYTES + 1)
                    if len(raw) > MAX_MANIFEST_BYTES:
                        return None
                    json.loads(raw)
                else:
                    with Image.open(output) as image:
                        image.verify()
            except (OSError, ValueError, RecursionError):
                return None
            if item.get('kind', 'image') == 'image':
                outputs.append(output)
        return outputs or None

    def verified_artifacts(self, source: Path, key: str) -> list[Path]:
        if self.verified_outputs(source, key) is None:
            return []
        return [
            Path(item['path'])
            for item in self.records[str(source)]['outputs']
            if item.get('kind') == 'artifact'
        ]

    def begin(self, source: Path, key: str) -> None:
        self.records[str(source)] = {
            'key': key,
            'status': 'running',
            'outputs': [],
        }
        self.save()

    def finish(
        self,
        source: Path,
        key: str,
        outputs: Sequence[Path],
        *,
        complete: bool,
        artifacts: Sequence[Path] = (),
        expected_images: int | None = None,
        expected_artifacts: int | None = None,
    ) -> None:
        # Filename skips do not prove recipe provenance. A mixed job must not
        # become resumable merely because some other destinations committed.
        complete = (
            complete
            and (expected_images is None or len(outputs) == expected_images)
            and (
                expected_artifacts is None
                or len(artifacts) == expected_artifacts
            )
        )
        self.records[str(source)] = {
            'key': key,
            'status': 'complete' if complete and outputs else 'incomplete',
            'outputs': [
                {
                    'path': str(path.resolve()),
                    'kind': kind,
                    'fingerprint': file_fingerprint(path),
                }
                for kind, paths in (
                    ('image', outputs),
                    ('artifact', artifacts),
                )
                for path in paths
            ]
            if complete
            else [],
        }
        self.save()

    def save(self) -> None:
        serialized = (
            json.dumps(
                {'schema_version': 1, 'records': self.records},
                indent=2,
                sort_keys=True,
            )
            + '\n'
        )
        if len(serialized.encode('utf-8')) > MAX_MANIFEST_BYTES:
            raise ManifestError('Manifest exceeds the size limit')
        with AtomicOutput(self.path) as temporary:
            temporary.write_text(serialized, encoding='utf-8')
