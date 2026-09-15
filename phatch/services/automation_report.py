from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TextIO

from phatch.lib.capabilities import Capability
from phatch.services.preflight import PreflightResult
from phatch.services.report_privacy import (
    ReportPrivacyContext,
    privacy_for_paths,
    redact_path,
    redact_text,
)
from phatch.services.structured_report import (
    REPORT_VERSION,
    AutomationOutcome,
    exit_code,
)


@dataclass(frozen=True, slots=True)
class ReportDestination:
    report_format: str
    stdout: TextIO
    stderr: TextIO
    privacy: ReportPrivacyContext = field(default_factory=privacy_for_paths)


def write_capabilities(
    capabilities: tuple[Capability, ...], destination: ReportDestination
) -> None:
    privacy = destination.privacy
    data = {
        "report_version": REPORT_VERSION,
        "kind": "capabilities",
        "capabilities": [
            {
                "id": str(capability.identifier),
                "status": capability.status.value,
                "reason_code": capability.reason_code.value,
                "reason": redact_text(capability.reason, privacy),
                "version": capability.version,
                "executable": (
                    redact_path(capability.executable, privacy)
                    if capability.executable is not None
                    else None
                ),
            }
            for capability in capabilities
        ],
    }
    if destination.report_format == "json":
        print(
            json.dumps(data, ensure_ascii=False, sort_keys=True),
            file=destination.stdout,
        )
    else:
        for capability in capabilities:
            reason = redact_text(capability.reason, privacy)
            print(
                f"{capability.identifier}: {capability.status.value} ({reason})",
                file=destination.stdout,
            )


def write_preflight(
    result: PreflightResult,
    outcome: AutomationOutcome,
    destination: ReportDestination,
) -> None:
    privacy = destination.privacy.with_paths(result.inputs, result.outputs)
    data = {
        "report_version": REPORT_VERSION,
        "kind": "preflight",
        "outcome": outcome.value,
        "inputs": [redact_path(path, privacy) for path in result.inputs],
        "planned_outputs": [redact_path(path, privacy) for path in result.outputs],
        "conflicts": [redact_path(path, privacy) for path in result.conflicts],
        "unavailable_capabilities": [
            str(capability.identifier) for capability in result.unavailable_capabilities
        ],
        "unsafe_operations": [
            redact_text(operation, privacy) for operation in result.unsafe_operations
        ],
        "invalid_fields": [
            redact_text(field_name, privacy) for field_name in result.invalid_fields
        ],
        "estimated_work": result.estimated_work,
    }
    if destination.report_format == "json":
        print(
            json.dumps(data, ensure_ascii=False, sort_keys=True),
            file=destination.stdout,
        )
    else:
        print(f"Outcome: {outcome.value}", file=destination.stdout)
        print(f"Inputs: {len(result.inputs)}", file=destination.stdout)
        print(f"Planned outputs: {len(result.outputs)}", file=destination.stdout)
        print(f"Estimated work: {result.estimated_work}", file=destination.stdout)


def write_failure(
    outcome: AutomationOutcome,
    diagnostic: str,
    destination: ReportDestination,
) -> int:
    safe_diagnostic = redact_text(diagnostic, destination.privacy)
    print(safe_diagnostic, file=destination.stderr)
    if destination.report_format == "json":
        print(
            json.dumps(
                {
                    "report_version": REPORT_VERSION,
                    "kind": "error",
                    "outcome": outcome.value,
                    "issues": [safe_diagnostic],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=destination.stdout,
        )
    return exit_code(outcome)
