from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Final, NoReturn, TextIO, assert_never

from phatch.core.action_registry import (
    ActionCatalogSources,
    ActionRegistryBuildFailure,
    ActionRegistryBuildSuccess,
    build_action_registry,
)
from phatch.core.cli import add_cli_options
from phatch.core.settings import DEFAULT_SETTINGS
from phatch.data.info import INFO
from phatch.lib.capabilities import Capability
from phatch.lib.capability_probes import foundation_capability_registry
from phatch.lib.executables import ExecutableLookup
from phatch.lib.image_codecs import codec_registry_capabilities
from phatch.lib.subprocess_runner import StdlibProcessRunner
from phatch.services.action_schema import (
    RegistrySchemaCatalog,
    SchemaValidationError,
    construct_document_actions,
    migrate_action_list,
    parse_action_list,
)
from phatch.services.automation_report import (
    write_capabilities,
    write_failure,
    write_preflight,
)
from phatch.services.preflight import (
    PreflightRequest,
    PreflightService,
    PreflightValidationError,
)
from phatch.services.structured_report import (
    AutomationOutcome,
    ExitCode,
    exit_code,
)

from .automation_execution import (
    AutomationExecutionRequest,
    execute_automation,
)

_STRUCTURED_FLAGS: Final = frozenset(
    {"--dry-run", "--report-format", "--resume", "--capabilities", "--max-workers"}
)


class AutomationArgumentError(ValueError):
    pass


class _AutomationArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise AutomationArgumentError(message)


def is_automation_request(arguments: tuple[str, ...]) -> bool:
    return any(argument.split("=", 1)[0] in _STRUCTURED_FLAGS for argument in arguments)


def report_format_from_arguments(arguments: tuple[str, ...]) -> str:
    for index, argument in enumerate(arguments):
        if argument == "--report-format" and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith("--report-format="):
            return argument.partition("=")[2]
    return "text"


def run_automation_cli(
    arguments: tuple[str, ...],
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = _AutomationArgumentParser(prog="phatch")
    info = {"name": str(INFO["name"]), "version": str(INFO["version"])}
    add_cli_options(parser, DEFAULT_SETTINGS, info)
    parser.add_argument("paths", nargs="*")
    try:
        options = parser.parse_args(arguments)
    except AutomationArgumentError as error:
        return write_failure(
            AutomationOutcome.VALIDATION_FAILURE,
            str(error),
            report_format_from_arguments(arguments),
            stdout,
            stderr,
        )
    if options.capabilities and not options.paths:
        capabilities = _capabilities()
        write_capabilities(capabilities, options.report_format, stdout)
        return ExitCode.SUCCESS
    if not options.paths:
        return write_failure(
            AutomationOutcome.VALIDATION_FAILURE,
            "No action list provided.",
            options.report_format,
            stdout,
            stderr,
        )
    action_list = Path(options.paths[0])
    input_paths = tuple(Path(path) for path in options.paths[1:])
    try:
        parsed = parse_action_list(action_list.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SchemaValidationError) as error:
        return write_failure(
            AutomationOutcome.VALIDATION_FAILURE,
            str(error),
            options.report_format,
            stdout,
            stderr,
        )
    registry_result = _build_registry()
    match registry_result:
        case ActionRegistryBuildFailure(issues=issues):
            return write_failure(
                AutomationOutcome.PROCESSING_FAILURE,
                "; ".join(issue.message for issue in issues),
                options.report_format,
                stdout,
                stderr,
            )
        case ActionRegistryBuildSuccess(registry=registry):
            pass
        case unreachable:
            assert_never(unreachable)
    catalog = RegistrySchemaCatalog(registry)
    try:
        document = migrate_action_list(parsed, catalog)
        actions = construct_document_actions(document, catalog, registry)
    except SchemaValidationError as error:
        return write_failure(
            AutomationOutcome.VALIDATION_FAILURE,
            str(error),
            options.report_format,
            stdout,
            stderr,
        )
    capabilities = _capabilities()
    try:
        preflight = PreflightService().build(
            PreflightRequest(
                document,
                input_paths,
                capabilities,
                options.recursive,
                catalog,
            )
        )
    except PreflightValidationError as error:
        return write_failure(
            AutomationOutcome.VALIDATION_FAILURE,
            str(error),
            options.report_format,
            stdout,
            stderr,
        )
    if options.dry_run:
        outcome = (
            AutomationOutcome.UNAVAILABLE_CAPABILITY
            if preflight.unavailable_capabilities
            else AutomationOutcome.VALIDATION_FAILURE
            if preflight.unsafe_operations or preflight.invalid_fields
            else AutomationOutcome.SUCCESS
        )
        write_preflight(preflight, outcome, options.report_format, stdout)
        return exit_code(outcome)
    if preflight.unavailable_capabilities:
        write_preflight(
            preflight,
            AutomationOutcome.UNAVAILABLE_CAPABILITY,
            options.report_format,
            stdout,
        )
        return ExitCode.UNAVAILABLE_CAPABILITY
    return execute_automation(
        AutomationExecutionRequest(
            actions,
            input_paths,
            document,
            preflight,
            options,
        ),
        stdout,
        stderr,
    )


def _build_registry() -> ActionRegistryBuildSuccess | ActionRegistryBuildFailure:
    from phatch import actions

    package_path = Path(actions.__file__).parent
    sources = ActionCatalogSources(
        built_in=tuple(package_path.glob("*.py")),
        user=(),
        built_in_package="phatch.actions",
    )
    return build_action_registry(sources)


def _capabilities() -> tuple[Capability, ...]:
    lookup = ExecutableLookup(path=os.environ.get("PATH"))
    return (
        *foundation_capability_registry(lookup, StdlibProcessRunner()).probe_all(),
        *codec_registry_capabilities(),
    )
