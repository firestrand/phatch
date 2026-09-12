from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO, assert_never

from phatch.console.console import Frame
from phatch.core import config
from phatch.core.execution_types import RecoveryConfiguration
from phatch.core.resource_config import packaged_config_paths
from phatch.core.settings import create_settings
from phatch.services.action_schema import ActionDocument, SchemaValidationError
from phatch.services.automation_report import write_failure
from phatch.services.legacy_execution import apply_actions_to_photos
from phatch.services.legacy_recovery import execute_with_recovery
from phatch.services.legacy_types import LegacyActionObject
from phatch.services.parallel_save import (
    build_image_jobs,
    execute_parallel_save,
)
from phatch.services.parallel_save_spec import (
    ParallelSaveSettings,
    ParallelSaveUnsupported,
    SaveJobSpec,
    select_parallel_save,
)
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import (
    AutomationOutcome,
    execution_report,
    exit_code,
)


@dataclass(frozen=True, slots=True)
class AutomationExecutionRequest:
    actions: tuple[LegacyActionObject, ...]
    paths: tuple[Path, ...]
    document: ActionDocument
    preflight: PreflightResult
    options: argparse.Namespace


def execute_automation(
    request: AutomationExecutionRequest,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    actions = request.actions
    paths = request.paths
    document = request.document
    preflight = request.preflight
    options = request.options

    try:
        with packaged_config_paths() as resource_paths:
            config_paths = config.init_config_paths(resource_paths)
            config.verify_app_user_paths()
            settings = create_settings(config_paths, options)
            settings["stop_for_errors"] = False
            settings["always_show_status_dialog"] = False
            legacy_paths = [str(path) for path in paths]
            receiver = Frame.receiver(settings, stderr)
            try:
                selection = select_parallel_save(
                    document,
                    preflight,
                    ParallelSaveSettings(
                        options.max_workers,
                        options.overwrite_existing_images,
                        bool(options.resume),
                        options.no_save,
                        int(settings["repeat"]),
                    ),
                )
                match selection:
                    case SaveJobSpec() as spec:
                        jobs = build_image_jobs(spec, preflight)
                        result, batch = execute_parallel_save(jobs, options.max_workers)
                        if options.verbose:
                            print(
                                "execution_mode=process "
                                f"requested_workers={options.max_workers} "
                                f"effective_workers={batch.max_workers} "
                                "worker_pids="
                                + ",".join(str(pid) for pid in batch.worker_pids),
                                file=stderr,
                            )
                    case ParallelSaveUnsupported(reason=constraint):
                        if options.resume:
                            result = execute_with_recovery(
                                actions,
                                settings,
                                RecoveryConfiguration(Path(options.resume).resolve()),
                                legacy_paths,
                            )
                        else:
                            result = apply_actions_to_photos(
                                actions, settings, legacy_paths
                            )
                        if options.verbose:
                            print(
                                "execution_mode=serial "
                                f"requested_workers={options.max_workers} "
                                f"parallel_constraint={constraint}",
                                file=stderr,
                            )
                    case unreachable:
                        assert_never(unreachable)
            finally:
                receiver.unsubscribe_all()
    except (OSError, SchemaValidationError) as error:
        return write_failure(
            AutomationOutcome.PROCESSING_FAILURE,
            str(error),
            options.report_format,
            stdout,
            stderr,
        )
    report = execution_report(result)
    if options.report_format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=stdout)
    else:
        print(f"Outcome: {report['outcome']}", file=stdout)
        print(f"Files: {len(report['files'])}", file=stdout)
    return exit_code(AutomationOutcome(report["outcome"]))
