from __future__ import annotations

import argparse
import io
import json
import sys
from dataclasses import dataclass
from uuid import UUID

import pytest

from phatch.console import console
from phatch.core import api
from phatch.core.execution_types import ExecutionOutcome, ExecutionResult
from phatch.services import automation_execution
from phatch.services.action_schema import ActionDocument
from phatch.services.automation_cli import run_automation_cli
from phatch.services.automation_execution import AutomationExecutionRequest
from phatch.services.completion import (
    CompletionDispatcher,
    CompletionOwnerMismatchError,
    collect_completion_events,
    completion_dispatch,
)
from phatch.services.parallel_save_spec import ParallelSaveUnsupported
from phatch.services.preflight import PreflightResult
from phatch.services.structured_report import ExitCode

ROUTES = (
    (ExecutionOutcome.COMPLETED, "Completed", "success", ExitCode.SUCCESS),
    (
        ExecutionOutcome.FAILED,
        "Failed",
        "processing_failure",
        ExitCode.PROCESSING_FAILURE,
    ),
    (
        ExecutionOutcome.CANCELLED,
        "Cancelled",
        "user_cancellation",
        ExitCode.USER_CANCELLATION,
    ),
)


def test_completion_dispatcher_emits_one_receipt_for_repeated_completion() -> None:
    receipts = []
    with collect_completion_events(receipts.append):
        dispatcher = CompletionDispatcher("gui")
        first = dispatcher.complete()
        second = dispatcher.complete()

    assert first is second
    assert receipts == [first]


def test_nested_completion_scope_reuses_the_entrypoint_request() -> None:
    receipts = []
    with (
        collect_completion_events(receipts.append),
        completion_dispatch("automation") as outer,
        completion_dispatch("automation") as inner,
    ):
        assert inner is outer

    assert receipts == [outer.receipt]


def test_nested_completion_scope_rejects_a_different_owner() -> None:
    with (
        completion_dispatch("automation"),
        pytest.raises(CompletionOwnerMismatchError),
        completion_dispatch("gui"),
    ):
        pass


def test_completion_sink_failure_does_not_fail_the_request() -> None:
    def failing_sink(_receipt) -> None:
        raise RuntimeError("observer failed")

    with collect_completion_events(failing_sink), completion_dispatch("automation"):
        pass


def test_completion_sink_failure_does_not_mask_the_request_error() -> None:
    def failing_sink(_receipt) -> None:
        raise RuntimeError("observer failed")

    with (
        collect_completion_events(failing_sink),
        pytest.raises(ValueError, match="request failed"),
        completion_dispatch("automation"),
    ):
        raise ValueError("request failed")


@pytest.mark.parametrize(("outcome", "heading", "_report", "_exit_code"), ROUTES)
def test_human_console_public_route_emits_one_terminal_completion(
    monkeypatch: pytest.MonkeyPatch,
    outcome: ExecutionOutcome,
    heading: str,
    _report: str,
    _exit_code: ExitCode,
) -> None:
    output = io.StringIO()
    receipts = []
    settings = {"verbose": False, "interactive": False}
    monkeypatch.setattr(console.Frame, "_pubsub", lambda self: None)
    monkeypatch.setattr(
        api,
        "open_actionlist",
        lambda _path, registry=None: ({"actions": []}, ""),
    )
    monkeypatch.setattr(
        api,
        "apply_actions_to_photos",
        lambda _actions, _settings, paths=None: ExecutionResult(outcome, ()),
    )

    with collect_completion_events(receipts.append):
        frame = console.Frame(
            "actions.phatch", [], settings, output=output, registry={}
        )

    assert frame.result.outcome is outcome
    assert output.getvalue().splitlines().count(heading) == 1
    assert "notification" not in output.getvalue().lower()
    assert len(receipts) == 1
    assert receipts[0].owner == "console"
    assert UUID(receipts[0].request_id).version == 4
    sys.stdout.write(
        json.dumps(
            {
                "owner": receipts[0].owner,
                "outcome": outcome.value,
                "request_id": receipts[0].request_id,
                "terminal_count": output.getvalue().splitlines().count(heading),
            },
            sort_keys=True,
        )
        + "\n"
    )


def test_human_console_early_validation_failure_emits_one_internal_completion() -> None:
    output = io.StringIO()
    receipts = []
    settings = {"verbose": False, "interactive": False}

    with (
        collect_completion_events(receipts.append),
        pytest.raises(SystemExit),
    ):
        console.Frame("", [], settings, output=output, registry={})

    assert output.getvalue() == ""
    assert len(receipts) == 1
    assert receipts[0].owner == "console"
    assert UUID(receipts[0].request_id).version == 4


@dataclass(slots=True)
class Receiver:
    unsubscribed: int = 0

    def unsubscribe_all(self) -> None:
        self.unsubscribed += 1


@pytest.mark.parametrize(("outcome", "_heading", "report", "exit_code"), ROUTES)
def test_automation_public_route_emits_one_uncontaminated_json_completion(
    monkeypatch: pytest.MonkeyPatch,
    outcome: ExecutionOutcome,
    _heading: str,
    report: str,
    exit_code: ExitCode,
) -> None:
    options = argparse.Namespace(
        report_format="json",
        max_workers=1,
        overwrite_existing_images=False,
        resume=None,
        no_save=True,
        verbose=False,
    )
    request = AutomationExecutionRequest(
        (),
        (),
        ActionDocument.from_values("", ()),
        PreflightResult((), (), (), (), (), (), 0),
        options,
    )
    receiver = Receiver()
    monkeypatch.setattr(
        automation_execution.config,
        "verify_app_user_paths",
        lambda: None,
    )
    monkeypatch.setattr(
        automation_execution.Frame,
        "receiver",
        classmethod(lambda cls, settings, output: receiver),
    )
    monkeypatch.setattr(
        automation_execution,
        "select_parallel_save",
        lambda *_args: ParallelSaveUnsupported("matrix"),
    )
    monkeypatch.setattr(
        automation_execution,
        "apply_actions_to_photos",
        lambda _actions, _settings, _paths: ExecutionResult(outcome, ()),
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    receipts = []

    with collect_completion_events(receipts.append):
        actual_exit = automation_execution.execute_automation(request, stdout, stderr)

    payload = json.loads(stdout.getvalue())
    assert actual_exit == exit_code
    assert payload["outcome"] == report
    assert stdout.getvalue().count("\n") == 1
    assert stderr.getvalue() == ""
    assert receiver.unsubscribed == 1
    assert len(receipts) == 1
    assert receipts[0].owner == "automation"
    assert UUID(receipts[0].request_id).version == 4
    sys.stdout.write(
        json.dumps(
            {
                "owner": receipts[0].owner,
                "outcome": outcome.value,
                "report_version": payload["report_version"],
                "request_id": receipts[0].request_id,
                "stdout_newlines": stdout.getvalue().count("\n"),
            },
            sort_keys=True,
        )
        + "\n"
    )


def test_automation_prevalidation_emits_internal_receipt_without_json_pollution() -> (
    None
):
    stdout = io.StringIO()
    stderr = io.StringIO()
    receipts = []

    with collect_completion_events(receipts.append):
        actual_exit = run_automation_cli(
            ("--report-format=json",),
            stdout,
            stderr,
        )

    payload = json.loads(stdout.getvalue())
    assert actual_exit == ExitCode.VALIDATION_FAILURE
    assert payload["report_version"] == 2
    assert payload["outcome"] == "validation_failure"
    assert stdout.getvalue().count("\n") == 1
    assert "request_id" not in payload
    assert len(receipts) == 1
    assert receipts[0].owner == "automation"
    assert UUID(receipts[0].request_id).version == 4
