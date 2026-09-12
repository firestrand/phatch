from __future__ import annotations

import json
from typing import TextIO

from phatch.lib.capabilities import Capability
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import AutomationOutcome, exit_code


def write_capabilities(
    capabilities: tuple[Capability, ...], report_format: str, stdout: TextIO
) -> None:
    data = {
        "report_version": 1,
        "kind": "capabilities",
        "capabilities": [
            {
                "id": str(capability.identifier),
                "status": capability.status.value,
                "reason_code": capability.reason_code.value,
                "reason": capability.reason,
                "version": capability.version,
                "executable": (
                    str(capability.executable)
                    if capability.executable is not None
                    else None
                ),
            }
            for capability in capabilities
        ],
    }
    if report_format == "json":
        print(json.dumps(data, ensure_ascii=False, sort_keys=True), file=stdout)
    else:
        for capability in capabilities:
            print(
                f"{capability.identifier}: {capability.status.value} "
                f"({capability.reason})",
                file=stdout,
            )


def write_preflight(
    result: PreflightResult,
    outcome: AutomationOutcome,
    report_format: str,
    stdout: TextIO,
) -> None:
    data = {
        "report_version": 1,
        "kind": "preflight",
        "outcome": outcome.value,
        "inputs": [str(path) for path in result.inputs],
        "planned_outputs": [str(path) for path in result.outputs],
        "conflicts": [str(path) for path in result.conflicts],
        "unavailable_capabilities": [
            str(capability.identifier) for capability in result.unavailable_capabilities
        ],
        "unsafe_operations": list(result.unsafe_operations),
        "invalid_fields": list(result.invalid_fields),
        "estimated_work": result.estimated_work,
    }
    if report_format == "json":
        print(json.dumps(data, ensure_ascii=False, sort_keys=True), file=stdout)
    else:
        print(f"Outcome: {outcome.value}", file=stdout)
        print(f"Inputs: {len(result.inputs)}", file=stdout)
        print(f"Planned outputs: {len(result.outputs)}", file=stdout)
        print(f"Estimated work: {result.estimated_work}", file=stdout)


def write_failure(
    outcome: AutomationOutcome,
    diagnostic: str,
    report_format: str,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    print(diagnostic, file=stderr)
    if report_format == "json":
        print(
            json.dumps(
                {
                    "report_version": 1,
                    "kind": "error",
                    "outcome": outcome.value,
                    "issues": [diagnostic],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=stdout,
        )
    return exit_code(outcome)
