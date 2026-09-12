from __future__ import annotations

import multiprocessing
import os
import sys
import tempfile
from concurrent.futures import CancelledError, Future, ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
from dataclasses import replace
from importlib.machinery import ModuleSpec
from importlib.util import find_spec
from multiprocessing.process import BaseProcess
from pathlib import Path
from types import ModuleType

from phatch.services.parallel_image_jobs import (
    ImageJob,
    ImageJobBatchResult,
    ImageJobFailure,
    ImageJobResult,
    _execute_image_job,
    _initialize_worker,
)


def execute_process_image_jobs(
    jobs: tuple[ImageJob, ...],
    max_workers: int,
    memory_budget_bytes: int,
) -> ImageJobBatchResult:
    coordinator_pid = os.getpid()
    bounded_jobs = tuple(
        replace(job, memory_budget_bytes=memory_budget_bytes) for job in jobs
    )
    admitted = tuple(
        job for job in bounded_jobs if job.estimated_memory_bytes <= memory_budget_bytes
    )
    rejected = tuple(
        ImageJobFailure(
            job.index,
            job.source,
            job.destination,
            job.stage,
            "estimated decoded memory exceeds memory budget of "
            f"{memory_budget_bytes} bytes",
            coordinator_pid,
        )
        for job in bounded_jobs
        if job.estimated_memory_bytes > memory_budget_bytes
    )
    largest_job_bytes = max((job.estimated_memory_bytes for job in admitted), default=1)
    memory_workers = max(1, memory_budget_bytes // largest_job_bytes)
    effective_workers = min(max_workers, memory_workers, max(1, len(admitted)))
    if not admitted:
        results: tuple[ImageJobResult, ...] = rejected
    elif effective_workers == 1:
        _initialize_worker(None)
        results = (*(_execute_image_job(job) for job in admitted), *rejected)
    else:
        results = _execute_pool(admitted, rejected, effective_workers)
    ordered = tuple(sorted(results, key=lambda result: result.index))
    worker_pids = tuple(
        sorted({result.worker_pid for result in ordered if result.worker_pid})
    )
    return ImageJobBatchResult(ordered, worker_pids, coordinator_pid, effective_workers)


def _execute_pool(
    admitted: tuple[ImageJob, ...],
    rejected: tuple[ImageJobFailure, ...],
    effective_workers: int,
) -> tuple[ImageJobResult, ...]:
    with tempfile.TemporaryDirectory(prefix="phatch-worker-pids-") as raw_registry:
        registry = Path(raw_registry)
        existing_process_ids = frozenset(
            process.pid for process in multiprocessing.active_children()
        )
        main_module, original_spec, original_path = _install_spawn_bootstrap()
        executor: ProcessPoolExecutor | None = None
        futures: dict[Future[ImageJobResult], ImageJob] = {}
        completed: list[ImageJobResult] = list(rejected)
        pool_failed = False
        aborting = True
        try:
            try:
                executor = _create_executor(effective_workers, registry)
                for job in admitted:
                    futures[executor.submit(_execute_image_job, job)] = job
            except (BrokenProcessPool, RuntimeError) as error:
                pool_failed = True
                completed.extend(_finished_results(futures))
                completed.extend(_unresolved_failures(admitted, completed, error))
            if not pool_failed:
                for future in as_completed(futures):
                    job = futures[future]
                    try:
                        completed.append(future.result())
                    except BrokenProcessPool as error:
                        pool_failed = True
                        completed.extend(
                            _unresolved_failures(admitted, completed, error)
                        )
                        break
                    except CancelledError as error:
                        completed.append(_future_failure(job, error))
                    except (
                        ArithmeticError,
                        BufferError,
                        EOFError,
                        ImportError,
                        LookupError,
                        MemoryError,
                        OSError,
                        RuntimeError,
                        TypeError,
                        ValueError,
                    ) as error:
                        completed.append(_future_failure(job, error))
            aborting = False
        finally:
            main_module.__spec__ = original_spec
            sys.path[:] = original_path
            if executor is None:
                if aborting or pool_failed:
                    _terminate_workers(_new_worker_processes(existing_process_ids))
            elif aborting:
                _cancel_futures(futures)
                workers = _new_worker_processes(existing_process_ids)
                executor.shutdown(wait=False, cancel_futures=True)
                _terminate_workers(workers)
            else:
                if pool_failed:
                    _cancel_futures(futures)
                executor.shutdown(wait=True, cancel_futures=pool_failed)
        return tuple(completed)


def _create_executor(max_workers: int, registry: Path) -> ProcessPoolExecutor:
    return ProcessPoolExecutor(
        max_workers=max_workers,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=_initialize_worker,
        initargs=(registry,),
    )


def _install_spawn_bootstrap() -> tuple[ModuleType, ModuleSpec | None, tuple[str, ...]]:
    main_module = sys.modules["__main__"]
    original_spec = main_module.__spec__
    original_path = tuple(sys.path)
    package_directory = Path(__file__).resolve().parents[1]
    sys.path[:] = [
        entry for entry in sys.path if Path(entry or ".").resolve() != package_directory
    ]
    main_module.__spec__ = find_spec("phatch.services.parallel_worker_bootstrap")
    return main_module, original_spec, original_path


def _cancel_futures(futures: dict[Future[ImageJobResult], ImageJob]) -> None:
    for future in futures:
        future.cancel()


def _future_failure(job: ImageJob, error: BaseException) -> ImageJobFailure:
    return ImageJobFailure(
        job.index,
        job.source,
        job.destination,
        job.stage,
        f"image worker failed: {error}",
        0,
    )


def _unresolved_failures(
    jobs: tuple[ImageJob, ...],
    completed: list[ImageJobResult],
    error: BaseException,
) -> tuple[ImageJobFailure, ...]:
    completed_indices = {result.index for result in completed}
    return tuple(
        ImageJobFailure(
            job.index,
            job.source,
            job.destination,
            job.stage,
            f"image worker pool terminated: {error}",
            0,
        )
        for job in jobs
        if job.index not in completed_indices
    )


def _finished_results(
    futures: dict[Future[ImageJobResult], ImageJob],
) -> tuple[ImageJobResult, ...]:
    results: list[ImageJobResult] = []
    for future, job in futures.items():
        if not future.done():
            continue
        try:
            results.append(future.result())
        except CancelledError as error:
            results.append(_future_failure(job, error))
        except (
            ArithmeticError,
            BufferError,
            EOFError,
            ImportError,
            LookupError,
            MemoryError,
            OSError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as error:
            results.append(_future_failure(job, error))
    return tuple(results)


def _new_worker_processes(
    existing_process_ids: frozenset[int | None],
) -> tuple[BaseProcess, ...]:
    return tuple(
        process
        for process in multiprocessing.active_children()
        if process.pid not in existing_process_ids
    )


def _terminate_workers(processes: tuple[BaseProcess, ...]) -> None:
    for process in processes:
        if process.is_alive():
            process.terminate()
    for process in processes:
        process.join(timeout=1.0)
    for process in processes:
        if process.is_alive():
            process.kill()
            process.join(timeout=1.0)
