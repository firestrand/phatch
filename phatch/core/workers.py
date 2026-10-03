# Copyright (C) 2007-2008 www.stani.be
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded process jobs with parent-owned progress, decisions and journals."""

from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import (
    Future,
    ProcessPoolExecutor,
    wait,
    FIRST_COMPLETED,
)
from dataclasses import dataclass
from concurrent.futures.process import BrokenProcessPool
from importlib import import_module
import multiprocessing
import os
from multiprocessing.connection import Connection
from multiprocessing.context import BaseContext
from pathlib import Path
import time
from typing import Any, Literal

from PIL import Image

from phatch.core.batch import (
    BatchAction,
    BatchPlan,
    BatchResult,
    Failure,
    FileResult,
    Issue,
    PlannedFile,
    ProgressEvent,
)
from phatch.core.manifests import (
    BatchManifest,
    ManifestError,
)
from phatch.lib.atomic import OutputPhase


@dataclass(frozen=True)
class WorkerEvent:
    index: int
    kind: Literal['ready', 'progress', 'error', 'output', 'output_finished']
    progress: ProgressEvent | None = None
    failure: Failure | None = None
    source: Path | None = None
    temporary: Path | None = None
    target: Path | None = None


@dataclass(frozen=True)
class OwnedOutput:
    temporary: Path
    target: Path
    device: int
    inode: int
    artifact: bool
    descriptor: int


@dataclass(frozen=True)
class WorkerJob:
    index: int
    file: PlannedFile
    actions: tuple[tuple[str, dict[str, Any]], ...]
    settings: dict[str, Any]
    decisions: Connection
    acknowledge_progress: bool
    request_errors: bool
    resource_dictionaries: tuple[dict[str, dict[str, str]], ...] = ()


# multiprocessing synchronization objects are a deliberate IPC boundary.
_CANCEL: Any = None


class _Cancellation:
    """A parent-only write makes every child reader permanently ready."""

    def __init__(self, context: BaseContext) -> None:
        self.reader, self.writer = context.Pipe(duplex=False)
        self.cancelled = False

    def is_set(self) -> bool:
        return self.cancelled

    def set(self) -> None:
        if not self.cancelled:
            self.writer.send_bytes(b'cancel')
            self.cancelled = True

    def close(self) -> None:
        self.reader.close()
        self.writer.close()


@dataclass(frozen=True)
class _CancellationView:
    reader: Connection

    def is_set(self) -> bool:
        # Never consume the notification: all workers must observe it.
        return self.reader.poll()


def _initialize(cancel: Connection, address_limit: int) -> None:
    global _CANCEL
    _CANCEL = _CancellationView(cancel)
    import resource

    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = (
        min(address_limit, hard)
        if hard != resource.RLIM_INFINITY
        else address_limit
    )
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
    from phatch.core import api

    api.import_actions()


def _emit(connection: Connection, event: WorkerEvent) -> bool:
    if _CANCEL.is_set():
        return False
    try:
        connection.send(event)
    except (BrokenPipeError, EOFError, OSError):
        return False
    return True


def _response(connection: Connection, fallback: str) -> str:
    while not _CANCEL.is_set():
        if connection.poll(0.05):
            return connection.recv()
    return fallback


def _execute(job: WorkerJob) -> BatchResult:
    if (
        not _emit(job.decisions, WorkerEvent(job.index, 'ready'))
        or _response(job.decisions, 'cancel') != 'continue'
    ):
        raise RuntimeError('Worker startup handshake was cancelled')
    from phatch.core.batch import run_batch
    from phatch.core import api
    from phatch.lib.atomic import observe_outputs

    actions = []
    for action_index, (module, fields) in enumerate(job.actions):
        built_in = module.startswith(('phatch.actions.', 'actions.'))
        action_type = (
            api.ACTION_IDS.get('phatch.actions.' + module.rsplit('.', 1)[-1])
            if built_in
            else getattr(import_module(module), 'Action')
        )
        if action_type is None:
            raise ValueError('Worker cannot find the requested plugin')
        action = action_type()
        invalid = action.load(fields)
        if invalid:
            raise ValueError('Worker could not reconstruct action fields')
        if job.resource_dictionaries:
            for label, dictionary in job.resource_dictionaries[
                action_index
            ].items():
                action._get_fields()[label].dictionary = dict(dictionary)
        actions.append(action)
    settings = dict(job.settings)
    settings.update(
        _worker_execution=True,
        _worker_plan=BatchPlan(files=[job.file]),
        _input_index=job.index,
        manifest_path=None,
        resume=False,
        report_path=None,
    )
    destinations: dict[str, list[Path]] = {}
    for destination in job.file.destinations:
        requested = str(
            (destination.requested_path or destination.path).resolve()
        )
        destinations.setdefault(requested, []).append(destination.path)
    settings['_planned_destinations'] = destinations

    def progress(event: ProgressEvent) -> None:
        if job.acknowledge_progress and _emit(
            job.decisions, WorkerEvent(job.index, 'progress', progress=event)
        ):
            _response(job.decisions, 'cancel')

    def on_error(failure: Failure, source: Path) -> str:
        if job.request_errors and _emit(
            job.decisions,
            WorkerEvent(job.index, 'error', failure=failure, source=source),
        ):
            return _response(job.decisions, 'abort')
        return 'stop'

    def register_output(
        phase: OutputPhase, temporary: Path, target: Path
    ) -> None:
        if phase == 'finished':
            _emit(
                job.decisions,
                WorkerEvent(job.index, 'output_finished', temporary=temporary),
            )
            return
        if (
            not _emit(
                job.decisions,
                WorkerEvent(
                    job.index, 'output', temporary=temporary, target=target
                ),
            )
            or _response(job.decisions, 'cancel') != 'continue'
        ):
            raise RuntimeError('Output registration was cancelled')

    try:
        with observe_outputs(register_output):
            return run_batch(
                actions,
                [job.file.source],
                settings,
                progress=progress,
                cancel=_CANCEL.is_set,
                on_error=on_error,
            )
    finally:
        job.decisions.close()


def _estimate(file: PlannedFile, options: Mapping[str, Any]) -> int:
    # Conservative admission reservation for decoded pixels and several native
    # working/export copies, plus interpreter/plugin state. RLIMIT_AS is the
    # enforcement boundary when transforms exceed this estimate.
    with Image.open(file.source) as image:
        count = getattr(image, 'n_frames', 1)
        total = 0
        for index in range(count):
            image.seek(index)
            total += image.width * image.height
    return 64 * 1024 * 1024 + total * 32


def run_parallel(
    actions: Sequence[BatchAction],
    plan: BatchPlan,
    options: Mapping[str, Any],
    result: BatchResult,
    manifest: BatchManifest | None,
    *,
    progress: Callable[[ProgressEvent], None] | None,
    cancel: Callable[[], bool] | None,
    on_error: Callable[[Failure, Path], str] | None,
    mp_context: BaseContext | None = None,
) -> BatchResult:
    started = time.perf_counter()
    requested = options.get('workers', 1)
    budget_mb = options.get('memory_budget_mb', 2048)
    try:
        if type(requested) is not int or not 1 <= requested <= 64:
            raise ValueError('Workers must be an integer from 1 to 64')
        if type(budget_mb) is not int or budget_mb < 128:
            raise ValueError(
                'Worker memory budget must be an integer of at least 128 MiB'
            )
        import resource

        if not hasattr(resource, 'RLIMIT_AS'):
            raise ValueError(
                'This platform cannot enforce worker address-space limits'
            )
        from phatch.core.workflow_preview import PURE_ACTIONS

        snapshots = []
        for action in actions:
            module = type(action).__module__
            builtin = module.startswith(('phatch.actions.', 'actions.'))
            if (
                not (
                    builtin
                    and module.rsplit('.', 1)[-1]
                    in PURE_ACTIONS | {'save', 'variants'}
                )
                and getattr(action, 'parallel_safe', False) is not True
            ):
                raise ValueError(
                    f'Action {action.label} does not support independent workers'
                )
            if '<locals>' in type(action).__qualname__:
                raise ValueError(
                    'Worker actions must be importable from a module'
                )
            snapshots.append((module, action.dump()['fields']))
        sources = {file.source.resolve() for file in plan.files}
        if any(
            destination.path.resolve() in sources
            and destination.policy != 'skip'
            for file in plan.files
            for destination in file.destinations
        ):
            raise ValueError(
                'Independent workers cannot overwrite batch inputs'
            )
        if any(file.unresolved for file in plan.files):
            raise ValueError(
                'Worker output paths must be fully resolved by preflight'
            )
        budget = budget_mb * 1024 * 1024
        maximum = max(
            (_estimate(file, options) for file in plan.files),
            default=64 * 1024 * 1024,
        )
        effective = min(requested, len(plan.files), budget // maximum)
        if effective < 1:
            raise ValueError(
                'Worker budget is too small for an input; raise memory_budget_mb'
            )
        address_limit = budget // effective
    except (ValueError, OSError, ImportError) as exc:
        result.status = 'invalid_setup'
        result.issues.append(Issue('invalid_workers', str(exc)))
        return result
    context = mp_context or multiprocessing.get_context('spawn')
    cancellation = _Cancellation(context)
    pending: dict[Future[BatchResult], tuple[int, Connection, Connection]] = {}
    journal_state: dict[int, tuple[str, dict[str, int | str]]] = {}
    next_index = 0
    stopped = False
    maximum_pending = 0
    continue_after_error: set[int] = set()
    owned_outputs: dict[int, dict[Path, OwnedOutput]] = {}
    recovered_outputs: dict[int, list[tuple[Path, bool]]] = {}

    def recover_output(index: int, transaction: OwnedOutput) -> None:
        identity = transaction.device, transaction.inode
        try:
            if transaction.target.exists():
                stat = transaction.target.lstat()
                if (stat.st_dev, stat.st_ino) == identity:
                    recovered_outputs.setdefault(index, []).append(
                        (transaction.target, transaction.artifact)
                    )
            if transaction.temporary.exists():
                stat = transaction.temporary.lstat()
                if (stat.st_dev, stat.st_ino) == identity:
                    transaction.temporary.unlink()
        except OSError as exc:
            result.files[index].warnings.append(
                f'Worker output recovery failed: {exc}'
            )
        finally:
            os.close(transaction.descriptor)

    def cancelled() -> bool:
        return cancellation.is_set() or bool(cancel and cancel())

    def handle_events() -> None:
        for index, receiver, child_connection in tuple(pending.values()):
            while receiver.poll():
                try:
                    event = receiver.recv()
                except (EOFError, OSError):
                    break
                handle_event(event, receiver, child_connection)

    def handle_event(
        event: WorkerEvent, receiver: Connection, child_connection: Connection
    ) -> None:
        if event.kind == 'ready':
            # The child has received its descriptor. Closing our duplicate
            # allows EOF if it dies during a subsequent message write.
            child_connection.close()
        if event.kind == 'output_finished':
            transaction = owned_outputs.get(event.index, {}).pop(
                event.temporary, None
            )
            if transaction is not None:
                recover_output(event.index, transaction)
            return
        decision = 'continue'
        if event.kind == 'output':
            destination = next(
                (
                    dest
                    for dest in plan.files[event.index].destinations
                    if dest.path == event.target
                ),
                None,
            )
            if destination is None or event.temporary is None:
                decision = 'cancel'
            else:
                try:
                    descriptor = os.open(
                        event.temporary, os.O_RDONLY | os.O_NOFOLLOW
                    )
                    try:
                        stat = os.fstat(descriptor)
                    except BaseException:
                        os.close(descriptor)
                        raise
                except OSError:
                    # Cancellation may have already unwound __enter__.
                    decision = 'cancel'
                else:
                    owned_outputs.setdefault(event.index, {})[
                        event.temporary
                    ] = OwnedOutput(
                        event.temporary,
                        destination.path,
                        stat.st_dev,
                        stat.st_ino,
                        destination.artifact,
                        descriptor,
                    )
        elif (
            event.kind == 'progress'
            and progress
            and event.progress is not None
        ):
            progress(event.progress)
        elif (
            event.kind == 'error'
            and on_error
            and event.failure is not None
            and event.source is not None
        ):
            decision = on_error(event.failure, event.source)
            if decision in {'skip', 'ignore'}:
                continue_after_error.add(event.index)
            if decision == 'abort':
                cancellation.set()
        if cancelled():
            cancellation.set()
            decision = 'cancel'
        try:
            receiver.send(decision)
        except (BrokenPipeError, EOFError, OSError):
            pass

    try:
        with ProcessPoolExecutor(
            max_workers=effective,
            mp_context=context,
            initializer=_initialize,
            initargs=(cancellation.reader, address_limit),
        ) as executor:
            try:
                while next_index < len(plan.files) or pending:
                    if cancelled():
                        cancellation.set()
                        result.status = 'cancelled'
                        stopped = True
                    handle_events()
                    while (
                        not stopped
                        and len(pending) < effective
                        and next_index < len(plan.files)
                    ):
                        index = next_index
                        next_index += 1
                        file = plan.files[index]
                        if manifest is not None:
                            try:
                                key, fingerprint = manifest.key(
                                    file.source,
                                    {
                                        'index': index,
                                        'root': file.root,
                                        'folder_index': file.folder_index,
                                    },
                                )
                                verified = (
                                    manifest.verified_outputs(file.source, key)
                                    if options.get('resume')
                                    else None
                                )
                                if verified is not None:
                                    result.files[index] = FileResult(
                                        file.source,
                                        status='skipped',
                                        outputs=verified,
                                        artifacts=manifest.verified_artifacts(
                                            file.source, key
                                        ),
                                        resumed=True,
                                    )
                                    continue
                                manifest.begin(file.source, key)
                                journal_state[index] = key, fingerprint
                            except (ManifestError, OSError) as exc:
                                result.files[index].status = 'failed'
                                result.files[index].failures.append(
                                    Failure(
                                        'Manifest',
                                        type(exc).__name__,
                                        str(exc),
                                    )
                                )
                                stopped = bool(options['stop_for_errors'])
                                continue
                        parent_connection, child_connection = context.Pipe()
                        settings = dict(options)
                        settings['_input_count'] = len(plan.files)
                        job = WorkerJob(
                            index,
                            file,
                            tuple(snapshots),
                            settings,
                            child_connection,
                            progress is not None,
                            on_error is not None,
                            tuple(
                                {
                                    label: dict(field.dictionary)
                                    for label, field in getattr(
                                        action, '_get_fields', lambda: {}
                                    )().items()
                                    if isinstance(
                                        getattr(field, 'dictionary', None),
                                        Mapping,
                                    )
                                }
                                for action in actions
                            ),
                        )
                        try:
                            future = executor.submit(_execute, job)
                        except BrokenProcessPool as exc:
                            parent_connection.close()
                            child_connection.close()
                            result.files[index] = FileResult(
                                file.source,
                                status='failed',
                                failures=[
                                    Failure(
                                        'Worker', type(exc).__name__, str(exc)
                                    )
                                ],
                            )
                            stopped = True
                            break
                        pending[future] = (
                            index,
                            parent_connection,
                            child_connection,
                        )
                        maximum_pending = max(maximum_pending, len(pending))
                    if not pending:
                        if stopped:
                            break
                        continue
                    completed, _ = wait(
                        pending, timeout=0.005, return_when=FIRST_COMPLETED
                    )
                    handle_events()
                    for future in completed:
                        index, connection, child_connection = pending.pop(
                            future
                        )
                        connection.close()
                        child_connection.close()
                        try:
                            outcome = future.result()
                            result.files[index] = (
                                outcome.files[0]
                                if outcome.files
                                else FileResult(
                                    plan.files[index].source,
                                    status='failed',
                                    failures=[
                                        Failure(
                                            'Worker setup',
                                            'SetupError',
                                            'Worker setup failed',
                                        )
                                    ],
                                )
                            )
                            result.issues.extend(outcome.issues)
                        except (
                            Exception
                        ) as exc:  # Isolate a worker/process failure.
                            if isinstance(exc, BrokenProcessPool):
                                stopped = True
                            result.files[index] = FileResult(
                                plan.files[index].source,
                                status='failed',
                                failures=[
                                    Failure(
                                        'Worker', type(exc).__name__, str(exc)
                                    )
                                ],
                            )
                        item = result.files[index]
                        if manifest is not None and index in journal_state:
                            key, fingerprint = journal_state[index]
                            try:
                                complete = (
                                    item.status == 'success'
                                    and key
                                    == manifest.key(
                                        item.source,
                                        {
                                            'index': index,
                                            'root': plan.files[index].root,
                                            'folder_index': plan.files[
                                                index
                                            ].folder_index,
                                        },
                                    )[0]
                                )
                                if item.status == 'success' and not complete:
                                    raise ManifestError(
                                        'Source or resources changed during worker processing'
                                    )
                                manifest.finish(
                                    item.source,
                                    key,
                                    item.outputs,
                                    artifacts=item.artifacts,
                                    complete=complete,
                                    expected_images=sum(
                                        not destination.artifact
                                        for destination in plan.files[
                                            index
                                        ].destinations
                                    ),
                                    expected_artifacts=sum(
                                        destination.artifact
                                        for destination in plan.files[
                                            index
                                        ].destinations
                                    ),
                                )
                            except (ManifestError, OSError) as exc:
                                item.status = 'failed'
                                item.failures.append(
                                    Failure(
                                        'Manifest',
                                        type(exc).__name__,
                                        str(exc),
                                    )
                                )
                        if item.status == 'cancelled':
                            cancellation.set()
                            result.status = 'cancelled'
                            stopped = True
                        elif (
                            item.status == 'failed'
                            and options['stop_for_errors']
                            and index not in continue_after_error
                        ):
                            stopped = True
            except BaseException:
                cancellation.set()
                raise
    finally:
        cancellation.set()
        # Executor shutdown has completed: no child can still write these
        # files. Held descriptors prevent inode reuse while detecting commits
        # and avoid deleting another writer's replacement at the temp path.
        for index, transactions in owned_outputs.items():
            for transaction in transactions.values():
                recover_output(index, transaction)
        for index, recovered in recovered_outputs.items():
            item = result.files[index]
            for path, artifact in recovered:
                outputs = item.artifacts if artifact else item.outputs
                if path not in outputs:
                    outputs.append(path)
        if manifest is not None:
            for index, (key, _) in journal_state.items():
                item = result.files[index]
                if item.status == 'success':
                    continue
                try:
                    manifest.finish(
                        item.source,
                        key,
                        item.outputs,
                        artifacts=item.artifacts,
                        complete=False,
                    )
                except (ManifestError, OSError) as exc:
                    item.warnings.append(
                        f'Worker journal recovery failed: {exc}'
                    )
        for _, connection, child_connection in pending.values():
            connection.close()
            child_connection.close()
        cancellation.close()
    if result.status != 'cancelled' and result.failed:
        result.status = (
            'partial_failure'
            if result.succeeded or any(item.outputs for item in result.files)
            else 'failed'
        )
    result.execution = {
        'backend': 'process',
        'requested_workers': requested,
        'effective_workers': effective,
        'max_in_flight': maximum_pending,
        'worker_memory_budget_bytes': budget,
        'per_worker_address_space_limit_bytes': address_limit,
    }
    result.elapsed = time.perf_counter() - started
    return result
