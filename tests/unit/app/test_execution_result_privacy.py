from pathlib import Path

from phatch.core.execution_types import (
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    OutputRecord,
    ReportFile,
)
from phatch.pyWx.execution_results import format_completion, present_completion


def _private_result() -> ExecutionResult:
    source = Path("/Volumes/private-client/input/source.png")
    output = Path("/Volumes/private-client/output/result.png")
    return ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source,),
        (
            FileResult(
                source,
                FileOutcome.PROCESSED,
                outputs=(OutputRecord(ReportFile(source, output, 10, 8, "RGB")),),
            ),
        ),
    )


class CapturingDialogs:
    def __init__(self) -> None:
        self.report: list[tuple[str, int | None, int | None, str | None, str]] = []
        self.message = ""

    def set_report(
        self,
        report: list[tuple[str, int | None, int | None, str | None, str]],
    ) -> None:
        self.report = report

    def show_execution_result(self, result: ExecutionResult, message: str) -> None:
        self.message = message


def test_completion_text_redacts_private_output_folder() -> None:
    message = format_completion(_private_result())

    assert "/Volumes/private-client" not in message
    assert "<output>" in message


def test_presented_report_redacts_private_source_path() -> None:
    dialogs = CapturingDialogs()

    present_completion(dialogs, _private_result(), "gui")

    assert dialogs.report == [("result.png", 10, 8, "RGB", "<input>/source.png")]
    assert "/Volumes/private-client" not in dialogs.message
