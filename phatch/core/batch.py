# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Reusable batch execution, output planning and explicit result contracts.

Plugins are the legacy dynamic boundary. Planning inspects their serialized
fields and never calls their initialization or processing methods.
"""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing.context import BaseContext
import logging
from pathlib import Path
import re
import time
from typing import Any, Literal, Protocol

from PIL import Image

from phatch.lib.atomic import AtomicOutput, RENAME_ATTEMPTS
from phatch.lib.odict import ReadOnlyDict

logger = logging.getLogger(__name__)


class BatchAction(Protocol):
    """Contract implemented by existing action plugins."""

    label: str
    metadata: list[str]
    valid_last: bool
    tags: list[str]

    def is_enabled(self) -> bool: ...
    def dump(self) -> dict[str, Any]: ...
    def init(self) -> object: ...
    def apply(
        self, photo: Any, setting: Callable[[str], Any], cache: dict[str, Any]
    ) -> Any: ...


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    severity: Literal['error', 'warning'] = 'error'


@dataclass(frozen=True)
class Failure:
    action: str
    kind: str
    message: str


@dataclass
class FileResult:
    source: Path
    status: str = 'not_started'
    outputs: list[Path] = field(default_factory=list)
    failures: list[Failure] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    elapsed: float = 0.0
    resumed: bool = False
    artifacts: list[Path] = field(default_factory=list)


@dataclass
class BatchResult:
    status: str = 'success'
    files: list[FileResult] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    elapsed: float = 0.0
    reserved_paths: list[Path] = field(default_factory=list)
    execution: dict[str, int | str] = field(
        default_factory=lambda: {'backend': 'serial', 'effective_workers': 1}
    )

    @property
    def succeeded(self) -> int:
        return sum(item.status == 'success' for item in self.files)

    @property
    def failed(self) -> int:
        return sum(item.status == 'failed' for item in self.files)

    @property
    def skipped(self) -> int:
        return sum(item.status == 'skipped' for item in self.files)

    @property
    def exit_code(self) -> int:
        return {
            'success': 0,
            'partial_failure': 1,
            'failed': 1,
            'invalid_setup': 2,
            'cancelled': 130,
        }[self.status]

    def to_dict(
        self, *, include_paths: bool = False, include_details: bool = False
    ) -> dict[str, object]:
        """Serialize without absolute paths or plugin payloads by default."""

        def path(value: Path) -> str:
            return str(value) if include_paths else value.name

        return {
            'schema_version': 1,
            'status': self.status,
            'exit_code': self.exit_code,
            'succeeded': self.succeeded,
            'failed': self.failed,
            'skipped': self.skipped,
            'elapsed_seconds': self.elapsed,
            'execution': self.execution,
            'issues': [
                {
                    'code': item.code,
                    'severity': item.severity,
                    'message': item.message,
                }
                for item in self.issues
            ],
            'files': [
                {
                    'source': path(item.source),
                    'status': item.status,
                    'resumed': item.resumed,
                    'outputs': [path(output) for output in item.outputs],
                    'artifacts': [path(output) for output in item.artifacts],
                    'elapsed_seconds': item.elapsed,
                    'warnings': item.warnings
                    if include_details
                    else ['Processing warning'] * len(item.warnings),
                    'failures': [
                        {
                            'action': failure.action,
                            'kind': failure.kind,
                            'message': failure.message
                            if include_details
                            else 'Processing failed',
                        }
                        for failure in item.failures
                    ],
                }
                for item in self.files
            ],
        }

    def write_report(
        self, filename: Path | str, *, include_paths: bool = False
    ) -> None:
        import json

        target = Path(filename).resolve()
        protected = {path.resolve() for path in self.reserved_paths}
        for item in self.files:
            protected.update(
                path.resolve()
                for path in [item.source, *item.outputs, *item.artifacts]
            )
        if target in protected:
            raise ValueError(
                'Report destination overlaps an input or batch output'
            )
        with AtomicOutput(filename) as temporary:
            temporary.write_text(
                json.dumps(self.to_dict(include_paths=include_paths), indent=2)
                + '\n',
                encoding='utf-8',
            )


@dataclass(frozen=True)
class Destination:
    path: Path
    policy: str
    action: str
    artifact: bool = False
    requested_path: Path | None = None


@dataclass
class PlannedFile:
    source: Path
    destinations: list[Destination] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)
    root: Path | None = None
    folder_index: int = 0


@dataclass
class BatchPlan:
    files: list[PlannedFile] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    resource_paths: list[Path] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == 'error' for issue in self.issues)

    def to_dict(self, *, include_paths: bool = False) -> dict[str, object]:
        def path(value: Path) -> str:
            return str(value) if include_paths else value.name

        return {
            'schema_version': 1,
            'valid': self.valid,
            'issues': [
                {
                    'code': issue.code,
                    'severity': issue.severity,
                    'message': issue.message,
                }
                for issue in self.issues
            ],
            'files': [
                {
                    'source': path(item.source),
                    'destinations': [
                        {
                            'path': path(dest.path),
                            'policy': dest.policy,
                            'action': dest.action,
                            'artifact': dest.artifact,
                        }
                        for dest in item.destinations
                    ],
                    'unresolved': item.unresolved,
                }
                for item in self.files
            ],
        }


@dataclass(frozen=True)
class ProgressEvent:
    source: Path
    input_index: int
    input_count: int
    action_index: int
    action_count: int
    action: str = ''


def _settings(settings: Mapping[str, Any] | None) -> dict[str, Any]:
    from phatch.core.settings import DEFAULT_SETTINGS

    result = dict(DEFAULT_SETTINGS)
    result.update(settings or {})
    return result


def _collect(
    inputs: Iterable[Path | str], recursive: bool, extensions: Sequence[str]
) -> tuple[list[Path], list[Issue]]:
    files: list[Path] = []
    issues: list[Issue] = []
    seen: set[Path] = set()
    supported = {'.' + ext.lower().lstrip('.') for ext in extensions}
    for value in inputs:
        source = Path(value).expanduser().resolve()
        if source.is_dir():
            candidates = sorted(
                source.rglob('*') if recursive else source.iterdir()
            )
            candidates = [
                p
                for p in candidates
                if p.is_file() and p.suffix.lower() in supported
            ]
        elif source.is_file():
            candidates = [source]
        else:
            issues.append(Issue('missing_input', 'An input does not exist'))
            continue
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate not in seen:
                seen.add(candidate)
                files.append(candidate)
    if not files and not issues:
        issues.append(Issue('empty_input', 'No input images were selected'))
    return files, issues


def _template(value: str, variables: Mapping[str, object]) -> str | None:
    """Expand simple variables; expressions stay unresolved during planning."""
    unresolved = False

    def substitute(match: re.Match[str]) -> str:
        nonlocal unresolved
        variable = match.group(1)
        if variable not in variables:
            unresolved = True
            return match.group(0)
        return str(variables[variable])

    result = re.sub(r'<([^<>]+)>', substitute, value)
    return None if unresolved or '<' in result or '>' in result else result


def plan_batch(
    actions: Sequence[BatchAction],
    inputs: Iterable[Path | str],
    settings: Mapping[str, Any] | None = None,
) -> BatchPlan:
    """Plan known save paths without executing, initializing or writing."""
    options = _settings(settings)
    if (
        type(options.get('workers', 1)) is not int
        or not 1 <= options.get('workers', 1) <= 64
    ):
        return BatchPlan(
            issues=[
                Issue(
                    'invalid_workers',
                    'Workers must be an integer from 1 to 64',
                )
            ]
        )
    from phatch.core.sequences import SequenceError, workflow_settings

    try:
        options = workflow_settings(actions, options)
    except SequenceError as exc:
        return BatchPlan(issues=[Issue('invalid_sequence', str(exc))])
    inputs = list(inputs)
    files, issues = _collect(
        inputs, options['recursive'], options['extensions']
    )
    if options.get('_selected_inputs') is not None:
        selected = {
            Path(value).resolve() for value in options['_selected_inputs']
        }
        files = [source for source in files if source in selected]
    plan = BatchPlan(issues=issues)
    reserved: set[Path] = set()
    all_sources = set(files)
    artifact_paths = [
        Path(options[key]).expanduser().resolve()
        for key in ('report_path', 'recipe_path', 'manifest_path')
        if options.get(key)
    ]
    artifacts = set(artifact_paths)
    if len(artifacts) != len(artifact_paths):
        plan.issues.append(
            Issue('artifact_collision', 'Batch artifacts share a path')
        )
    if artifacts.intersection(all_sources):
        plan.issues.append(
            Issue('artifact_collision', 'A batch artifact overlaps an input')
        )
    repeat = options['repeat']
    if not isinstance(repeat, int) or isinstance(repeat, bool) or repeat < 1:
        plan.issues.append(
            Issue('invalid_repeat', 'Repeat must be a positive integer')
        )
        return plan
    folder_counts: dict[Path, int] = {}
    Image.init()
    for index, source in enumerate(files):
        root = source.parent
        for value in inputs:
            candidate = Path(value).expanduser().resolve()
            if candidate.is_dir() and source.is_relative_to(candidate):
                root = candidate
                break
        folder_index = folder_counts.get(source.parent, 0)
        folder_counts[source.parent] = folder_index + 1
        item = PlannedFile(source, root=root, folder_index=folder_index)
        plan.files.append(item)
        date = datetime.fromtimestamp(source.stat().st_mtime)
        variables: dict[str, object] = {
            'path': str(source),
            'folder': str(root),
            'root': str(root.parent),
            'foldername': root.name,
            'filename': source.stem,
            'type': source.suffix.lstrip('.'),
            'subfolder': str(source.parent.relative_to(root)).replace(
                '.', '', 1
            )
            if source.parent == root
            else str(source.parent.relative_to(root)),
            'index': index * repeat,
            'imageindex': index,
            'folderindex': folder_index,
            'repeatindex': 0,
            'year': date.year,
            'month': date.month,
            'day': date.day,
        }
        from phatch.lib.metadata import DESKTOP_FOLDER

        variables['desktop'] = DESKTOP_FOLDER
        try:
            with Image.open(source) as image:
                variables.update(
                    width=image.width,
                    height=image.height,
                    size=image.size,
                    mode=image.mode,
                    format=image.format,
                )
                image.verify()
        except (OSError, ValueError) as exc:
            plan.issues.append(Issue('invalid_image', type(exc).__name__))
            continue
        from phatch.core.sequences import (
            SequenceError,
            inspect_sequence,
            validate_workflow,
        )

        try:
            sequence = inspect_sequence(source, options)
            sequence_policy = validate_workflow(
                sequence,
                [action for action in actions if action.is_enabled()],
                options,
            )
        except (SequenceError, OSError, ValueError) as exc:
            plan.issues.append(Issue('invalid_sequence', str(exc)))
            continue
        variables.update(frameindex=0, framecount=sequence.count)
        original_variables = variables.copy()
        for repeat_index in range(repeat):
            variables = original_variables.copy()
            variables.update(
                index=index * repeat + repeat_index, repeatindex=repeat_index
            )
            frame_variables = variables.copy()
            frame_indices = (
                range(sequence.count)
                if sequence.count > 1 and sequence_policy == 'extract'
                else range(1)
            )
            for frame_index in frame_indices:
                variables = frame_variables.copy()
                variables['frameindex'] = frame_index
                variables.update(
                    width=sequence.sizes[frame_index][0],
                    height=sequence.sizes[frame_index][1],
                    size=sequence.sizes[frame_index],
                )
                for action in actions:
                    if not action.is_enabled():
                        continue
                    if type(action).__module__ not in {
                        'actions.save',
                        'phatch.actions.save',
                        'actions.variants',
                        'phatch.actions.variants',
                    }:
                        # Geometry/metadata after arbitrary transformations is unknown.
                        for key in ('width', 'height', 'size', 'mode'):
                            variables.pop(key, None)
                        continue
                    fields = action.dump()['fields']
                    expansions = [(fields, False)]
                    if type(action).__module__.endswith('.variants'):
                        from phatch.core.variants import (
                            VariantValidationError,
                            planning_fields,
                        )

                        try:
                            expansions = planning_fields(fields)
                        except VariantValidationError as exc:
                            plan.issues.append(
                                Issue('invalid_variants', str(exc))
                            )
                            continue
                    for fields, artifact in expansions:
                        folder = _template(fields['In'], variables)
                        name = _template(fields['File Name'], variables)
                        extension = _template(fields['As'], variables)
                        if folder is None or name is None or extension is None:
                            item.unresolved.append(action.label)
                            continue
                        if type(action).__module__.endswith('.variants') and (
                            not name or Path(name).name != name or '\\' in name
                        ):
                            plan.issues.append(
                                Issue(
                                    'invalid_variants',
                                    'Variant output names cannot contain directories',
                                )
                            )
                            continue
                        from phatch.lib.imtools import get_format

                        from phatch.core.capabilities import (
                            UnsupportedCodecError,
                            resolve_encoder,
                        )

                        if not artifact:
                            encoder = get_format(extension)
                            try:
                                resolved = resolve_encoder(
                                    encoder,
                                    fields.get('Format Fallback', 'error'),
                                )
                            except (UnsupportedCodecError, ValueError) as exc:
                                plan.issues.append(
                                    Issue(
                                        'unsupported_codec',
                                        str(exc),
                                    )
                                )
                                continue
                            if resolved != encoder:
                                extension = 'png'
                                plan.issues.append(
                                    Issue(
                                        'format_fallback',
                                        'Explicit PNG fallback will be used',
                                        'warning',
                                    )
                                )
                        if (
                            sequence.count > 1
                            and sequence_policy == 'preserve'
                            and not artifact
                        ):
                            from phatch.core.sequences import (
                                ANIMATION_FORMATS,
                                PAGE_FORMATS,
                            )

                            supported = (
                                PAGE_FORMATS
                                if sequence.kind == 'pages'
                                else ANIMATION_FORMATS
                            )
                            if (
                                resolved not in supported
                                or (
                                    resolved == 'AVIF'
                                    and sequence.loop is not None
                                )
                                or (
                                    sequence.default_image
                                    and resolved != 'PNG'
                                )
                            ):
                                plan.issues.append(
                                    Issue(
                                        'invalid_sequence',
                                        'Requested encoder cannot preserve this sequence',
                                    )
                                )
                                continue
                        target = (
                            Path(folder) / (name + '.' + extension)
                        ).resolve()
                        if sequence.count > 1 and sequence_policy == 'extract':
                            from phatch.core.sequences import extraction_path

                            target = extraction_path(target, frame_index)
                        requested_target = target
                        policy = fields.get('Collision Policy', 'inherit')
                        if policy == 'inherit':
                            policy = options.get('collision_policy') or (
                                'replace'
                                if options['overwrite_existing_images']
                                else 'skip'
                            )
                        if target in all_sources:
                            plan.issues.append(
                                Issue(
                                    'source_overlap',
                                    'An output overlaps an input',
                                    'error'
                                    if options.get('manifest_path')
                                    or type(action).__module__.endswith(
                                        '.variants'
                                    )
                                    else 'warning',
                                )
                            )
                        if policy == 'rename':
                            original = target
                            for suffix in range(RENAME_ATTEMPTS):
                                target = (
                                    original
                                    if suffix == 0
                                    else original.with_name(
                                        f'{original.stem}-{suffix}{original.suffix}'
                                    )
                                )
                                if (
                                    target not in reserved
                                    and not target.exists()
                                ):
                                    break
                            else:
                                plan.issues.append(
                                    Issue(
                                        'collision',
                                        'Rename collision limit exceeded',
                                    )
                                )
                                continue
                        elif target in reserved and policy != 'skip':
                            plan.issues.append(
                                Issue(
                                    'collision',
                                    'Multiple inputs share an output path',
                                )
                            )
                        elif (
                            target.exists()
                            and policy == 'fail'
                            and not options.get('resume')
                        ):
                            plan.issues.append(
                                Issue('collision', 'An output already exists')
                            )
                        if target in artifacts:
                            plan.issues.append(
                                Issue(
                                    'artifact_collision',
                                    'A batch artifact overlaps an output',
                                )
                            )
                        reserved.add(target)
                        item.destinations.append(
                            Destination(
                                target,
                                policy,
                                action.label,
                                artifact,
                                requested_target,
                            )
                        )
    from phatch.core.resources import ResourceError, input_resource_paths

    resources: set[Path] = set()
    for index, item in enumerate(plan.files):
        try:
            paths, resolved = input_resource_paths(
                [action for action in actions if action.is_enabled()],
                item.source,
                {
                    'index': index,
                    'root': item.root,
                    'folder_index': item.folder_index,
                },
                options,
            )
            resources.update(paths)
            if not resolved:
                plan.issues.append(
                    Issue(
                        'unresolved_resource',
                        'Resource paths require runtime expressions',
                        'warning',
                    )
                )
        except (ResourceError, OSError, ValueError):
            plan.issues.append(
                Issue(
                    'unresolved_resource',
                    'Resource paths could not be resolved without execution',
                    'warning',
                )
            )
    plan.resource_paths = sorted(resources)
    if resources.intersection(artifacts | reserved):
        plan.issues.append(
            Issue(
                'resource_overlap',
                'A destination overlaps a workflow resource',
            )
        )
    return plan


def _photo(
    source: Path,
    actions: Sequence[BatchAction],
    index: int,
    repeat_index: int,
    repeat: int,
    root: Path | None = None,
    folder_index: int = 0,
    frame_index: int = 0,
) -> Any:
    from phatch.core import api, pil
    from phatch.lib import metadata

    variables = (
        set(pil.BASE_VARS)
        .union(api.get_vars(actions))
        .difference({'frameindex', 'framecount'})
    )
    file_vars, other_vars = metadata.InfoFile.split_vars(list(variables))
    info = metadata.InfoFile(vars=file_vars).dump(
        (str(source), str(root or source.parent))
    )
    info.update(
        index=index * repeat + repeat_index,
        imageindex=index,
        folderindex=folder_index,
        repeatindex=repeat_index,
    )
    return pil.Photo(
        info,
        metadata.InfoExtract(
            vars=list(pil.split_vars_static_dynamic(other_vars)[0])
        ),
        frame_index=frame_index,
    )


def run_batch(
    actions: Sequence[BatchAction],
    inputs: Iterable[Path | str],
    settings: Mapping[str, Any] | None = None,
    *,
    progress: Callable[[ProgressEvent], None] | None = None,
    cancel: Callable[[], bool] | None = None,
    on_error: Callable[[Failure, Path], str] | None = None,
    mp_context: BaseContext | None = None,
) -> BatchResult:
    """Execute actions with explicit results, isolated input state and cleanup."""
    started = time.perf_counter()
    options = _settings(settings)
    enabled = [action for action in actions if action.is_enabled()]
    from phatch.core.sequences import SequenceError, workflow_settings

    try:
        options = workflow_settings(enabled, options)
    except SequenceError as exc:
        return BatchResult(
            status='invalid_setup',
            issues=[Issue('invalid_sequence', str(exc))],
        )
    plan = options.get('_worker_plan') or plan_batch(enabled, inputs, options)
    result = BatchResult(
        files=[FileResult(item.source) for item in plan.files],
        issues=list(plan.issues),
        reserved_paths=[
            dest.path for item in plan.files for dest in item.destinations
        ]
        + plan.resource_paths,
    )
    result.reserved_paths.extend(
        Path(options[key]).expanduser().resolve()
        for key in ('recipe_path', 'manifest_path')
        if options.get(key)
    )
    if not enabled:
        result.issues.append(Issue('empty_recipe', 'No actions are enabled'))
    elif not (
        enabled[-1].valid_last
        or options['no_save']
        or all('file' in action.tags for action in enabled)
    ):
        result.issues.append(
            Issue('missing_save', 'Recipe needs a final Save action')
        )
    from phatch.core import api
    from phatch.lib import formField

    if (
        plan.valid
        and enabled
        and formField.get_safe()
        and api.assert_safe(enabled)
    ):
        result.issues.append(
            Issue('unsafe_recipe', 'Recipe is unsafe in Safe Mode')
        )
    if any(issue.severity == 'error' for issue in result.issues):
        result.status = 'invalid_setup'
        result.elapsed = time.perf_counter() - started
        return result
    from phatch.core.manifests import (
        BatchManifest,
        ManifestError,
        job_identity,
    )

    manifest = None
    if options.get('resume') and not options.get('manifest_path'):
        result.issues.append(
            Issue('invalid_manifest', 'Resume requires a manifest path')
        )
        result.status = 'invalid_setup'
        return result
    if options.get('manifest_path'):
        try:
            manifest = BatchManifest(
                options['manifest_path'],
                job_identity(enabled, options),
                resume=options['resume'],
                actions=enabled,
                settings=options,
            )
        except (ManifestError, OSError) as exc:
            result.issues.append(Issue('invalid_manifest', str(exc)))
            result.status = 'invalid_setup'
            return result
    if options.get('workers', 1) != 1 and not options.get('_worker_execution'):
        from phatch.core.workers import run_parallel

        return run_parallel(
            enabled,
            plan,
            options,
            result,
            manifest,
            progress=progress,
            cancel=cancel,
            on_error=on_error,
            mp_context=mp_context,
        )
    try:
        for action in enabled:
            action.init()
    except (
        Exception
    ) as exc:  # Plugin setup is an intentional isolation boundary.
        logger.warning('Action initialization failed: %s', type(exc).__name__)
        result.issues.append(
            Issue('plugin_setup', 'An action could not initialize')
        )
        result.status = 'invalid_setup'
        return result
    options['_cancel_callback'] = cancel
    for local_index, item in enumerate(result.files):
        index = options.get('_input_index', local_index)
        if cancel and cancel():
            result.status = 'cancelled'
            break
        input_started = time.perf_counter()
        item.status = 'success'
        continue_on_error = False
        cache: dict[str, Any] = {}
        manifest_key = None
        for repeat_index in range(options['repeat']):
            photo = None
            label = 'Open image'
            try:
                if manifest is not None and repeat_index == 0:
                    label = 'Manifest'
                    manifest_key, _ = manifest.key(
                        item.source,
                        {
                            'index': index,
                            'root': plan.files[local_index].root,
                            'folder_index': plan.files[
                                local_index
                            ].folder_index,
                        },
                    )
                    verified = (
                        manifest.verified_outputs(item.source, manifest_key)
                        if options['resume']
                        else None
                    )
                    if verified is not None:
                        item.outputs = verified
                        item.artifacts = manifest.verified_artifacts(
                            item.source, manifest_key
                        )
                        item.status = 'skipped'
                        item.resumed = True
                        break
                    manifest.begin(item.source, manifest_key)
                    label = 'Open image'
                photo = _photo(
                    item.source,
                    enabled,
                    index,
                    repeat_index,
                    options['repeat'],
                    plan.files[local_index].root,
                    plan.files[local_index].folder_index,
                )
                if options.get('_planned_destinations') is not None:
                    from collections import deque

                    photo.planned_destinations = {
                        key: deque(values)
                        for key, values in options[
                            '_planned_destinations'
                        ].items()
                    }
                from phatch.core.sequences import (
                    attach_sequence,
                    inspect_sequence,
                    validate_workflow,
                )

                sequence = inspect_sequence(item.source, options, cancel)
                sequence_policy = validate_workflow(sequence, enabled, options)
                members = [photo]
                attach_sequence(
                    photo,
                    members,
                    sequence,
                    sequence_policy if sequence.count > 1 else 'first',
                    cancel,
                )
                if sequence.count > 1 and sequence_policy in {
                    'extract',
                    'preserve',
                }:
                    for frame_index in range(1, sequence.count):
                        if cancel and cancel():
                            raise InterruptedError(
                                'Sequence decoding cancelled'
                            )
                        members.append(
                            _photo(
                                item.source,
                                enabled,
                                index,
                                repeat_index,
                                options['repeat'],
                                plan.files[local_index].root,
                                plan.files[local_index].folder_index,
                                frame_index,
                            )
                        )
                    for member in members:
                        if hasattr(photo, 'planned_destinations'):
                            member.planned_destinations = (
                                photo.planned_destinations
                            )
                    attach_sequence(
                        photo, members, sequence, sequence_policy, cancel
                    )
                for action_index, action in enumerate(enabled):
                    if cancel and cancel():
                        item.status = 'cancelled'
                        result.status = 'cancelled'
                        break
                    label = action.label
                    if progress:
                        progress(
                            ProgressEvent(
                                item.source,
                                index * options['repeat'] + repeat_index,
                                options.get('_input_count', len(result.files))
                                * options['repeat'],
                                action_index,
                                len(enabled),
                                label,
                            )
                        )
                    if cancel and cancel():
                        item.status = 'cancelled'
                        result.status = 'cancelled'
                        break
                    try:
                        from phatch.core.sequences import apply_action

                        photo = apply_action(
                            photo, action, ReadOnlyDict(options), cache
                        )
                    except Exception as exc:  # Isolate plugin execution only.
                        if (
                            isinstance(exc, InterruptedError)
                            and cancel
                            and cancel()
                        ):
                            item.status = 'cancelled'
                            result.status = 'cancelled'
                            break
                        failure = Failure(label, type(exc).__name__, str(exc))
                        item.failures.append(failure)
                        item.status = 'failed'
                        decision = (
                            on_error(failure, item.source)
                            if on_error
                            else 'stop'
                        )
                        if decision == 'abort':
                            result.status = 'cancelled'
                        elif decision in {'skip', 'ignore'}:
                            continue_on_error = True
                        if decision != 'ignore':
                            break
                    warning = photo.get_log()
                    if warning:
                        item.warnings.append(warning)
                        photo.clear_log()
                item.outputs.extend(
                    Path(report['path']) for report in photo.report_files
                )
                item.artifacts.extend(
                    Path(path) for path in photo.report_artifacts
                )
                if item.outputs and item.status == 'skipped':
                    item.status = 'success'
                if not item.outputs and plan.files[local_index].destinations:
                    item.status = (
                        'skipped' if item.status == 'success' else item.status
                    )
            except (
                Exception
            ) as exc:  # Isolate one input; shutdown signals propagate.
                interrupted = (
                    isinstance(exc, InterruptedError) and cancel and cancel()
                )
                item.status = 'cancelled' if interrupted else 'failed'
                if interrupted:
                    result.status = 'cancelled'
                else:
                    item.failures.append(
                        Failure(label, type(exc).__name__, str(exc))
                    )
                if photo is not None:
                    item.outputs.extend(
                        Path(report['path']) for report in photo.report_files
                    )
                if photo is not None:
                    item.artifacts.extend(
                        Path(path) for path in photo.report_artifacts
                    )
                if on_error and not interrupted:
                    decision = on_error(item.failures[-1], item.source)
                    continue_on_error = decision in {'skip', 'ignore'}
                    if decision == 'abort':
                        result.status = 'cancelled'
                logger.warning(
                    'Input processing failed in %s: %s',
                    label,
                    type(exc).__name__,
                )
                break
            finally:
                if photo is not None:
                    from phatch.core.sequences import close_sequence

                    close_sequence(photo)
            if result.status == 'cancelled':
                break
        if (
            manifest is not None
            and manifest_key is not None
            and not item.resumed
        ):
            try:
                complete = (
                    item.status == 'success'
                    and manifest_key
                    == manifest.key(
                        item.source,
                        {
                            'index': index,
                            'root': plan.files[local_index].root,
                            'folder_index': plan.files[
                                local_index
                            ].folder_index,
                        },
                    )[0]
                )
                if item.status == 'success' and not complete:
                    raise ManifestError(
                        'Source or resources changed during processing; completion was not recorded'
                    )
                manifest.finish(
                    item.source,
                    manifest_key,
                    item.outputs,
                    complete=complete,
                    artifacts=item.artifacts,
                    expected_images=sum(
                        not destination.artifact
                        for destination in plan.files[local_index].destinations
                    ),
                    expected_artifacts=sum(
                        destination.artifact
                        for destination in plan.files[local_index].destinations
                    ),
                )
            except (ManifestError, OSError) as exc:
                item.status = 'failed'
                item.failures.append(
                    Failure('Manifest', type(exc).__name__, str(exc))
                )
        item.elapsed = time.perf_counter() - input_started
        if result.status == 'cancelled' or (
            item.status == 'failed'
            and options['stop_for_errors']
            and not continue_on_error
        ):
            break
    if result.status != 'cancelled' and result.failed:
        result.status = (
            'partial_failure'
            if result.succeeded or any(item.outputs for item in result.files)
            else 'failed'
        )
    result.elapsed = time.perf_counter() - started
    return result
