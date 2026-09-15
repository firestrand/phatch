import gc
import weakref
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Lock
from time import sleep

import pytest

from phatch.core.execution_types import (
    ExecutionIssue,
    ExecutionOutcome,
    ExecutionResult,
    FileOutcome,
    FileResult,
    IssueSeverity,
    IssueStage,
    OutputRecord,
    ReportFile,
    RollbackState,
)
from phatch.lib import system
from phatch.pyWx.execution_results import (
    CompletionOwnershipError,
    format_completion,
    open_output_folder,
    output_folders,
    present_completion,
    try_open_output_folder,
)
from phatch.services.completion import CompletionDispatcher


def test_output_folders_use_only_surviving_canonical_parents(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    first = tmp_path / "A folder" / "first.png"
    second = tmp_path / "b-folder" / "second.png"
    duplicate = tmp_path / "A folder" / "duplicate.png"
    removed = tmp_path / "removed" / "gone.png"
    failed_source = tmp_path / "failed.png"
    removed_issue = ExecutionIssue(
        IssueStage.ACTION_EXECUTION,
        IssueSeverity.ERROR,
        "removed",
        failed_source,
    )
    result = ExecutionResult(
        ExecutionOutcome.COMPLETED,
        (source, failed_source),
        (
            FileResult(
                source,
                FileOutcome.PROCESSED,
                outputs=(
                    OutputRecord(ReportFile(source, second)),
                    OutputRecord(ReportFile(source, duplicate)),
                    OutputRecord(ReportFile(source, first)),
                ),
            ),
            FileResult(
                failed_source,
                FileOutcome.FAILED,
                issues=(removed_issue,),
                outputs=(
                    OutputRecord(ReportFile(failed_source, removed), survived=False),
                ),
                rollback=RollbackState.COMPLETED,
            ),
        ),
        issues=(removed_issue,),
    )

    assert output_folders(result) == (
        (tmp_path / "A folder").resolve(),
        (tmp_path / "b-folder").resolve(),
    )


def test_open_output_folder_preserves_metacharacters_as_one_argv_element(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "photos; $(touch nope)"
    folder.mkdir()
    commands = []

    open_output_folder(folder, commands.append, platform="darwin")

    assert commands[0].argv == ("open", str(folder.resolve()))


def test_open_output_folder_rejects_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        open_output_folder(tmp_path / "missing", lambda command: None)


@pytest.mark.parametrize(
    ("platform", "executable"),
    (("darwin", "open"), ("win32", "explorer.exe"), ("linux", "xdg-open")),
)
def test_open_directory_command_uses_platform_argv(
    tmp_path: Path, platform: str, executable: str
) -> None:
    folder = tmp_path / "output folder;safe"
    folder.mkdir()

    command = system.open_directory_command(folder, platform)

    assert command.argv == (executable, str(folder.resolve()))


def test_completion_uses_typed_counts_instead_of_discovered_file_count() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())

    assert "Processed: 0" in format_completion(result)
    assert "Completed" in format_completion(result)


def test_present_completion_suppresses_duplicate_for_same_owner() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())

    class Dialogs:
        def __init__(self) -> None:
            self.presentations = []

        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            self.presentations.append((presented, message))

    dialogs = Dialogs()

    first = present_completion(dialogs, result, "gui")
    second = present_completion(dialogs, result, "gui")

    assert second is first
    assert len(dialogs.presentations) == 1


def test_present_completion_suppresses_concurrent_duplicate_for_same_owner() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())

    class Dialogs:
        def __init__(self) -> None:
            self.presentation_count = 0
            self.count_lock = Lock()

        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            with self.count_lock:
                self.presentation_count += 1
            sleep(0.05)

    dialogs = Dialogs()
    with ThreadPoolExecutor(max_workers=2) as executor:
        receipts = tuple(
            executor.map(
                lambda _index: present_completion(dialogs, result, "gui"),
                range(2),
            )
        )

    assert receipts[0] is receipts[1]
    assert dialogs.presentation_count == 1


def test_concurrent_duplicate_waits_for_presentation_to_finish() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())
    presentation_started = Event()
    release_presentation = Event()

    class Dialogs:
        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            presentation_started.set()
            assert release_presentation.wait(timeout=1)

    dialogs = Dialogs()
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(present_completion, dialogs, result, "gui")
        assert presentation_started.wait(timeout=1)
        second = executor.submit(present_completion, dialogs, result, "gui")
        sleep(0.05)
        assert not second.done()
        release_presentation.set()

        assert second.result(timeout=1) is first.result(timeout=1)


def test_failed_presentation_can_be_retried() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())

    class Dialogs:
        def __init__(self) -> None:
            self.attempts = 0

        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            self.attempts += 1
            if self.attempts == 1:
                raise RuntimeError("dialog failed")

    dialogs = Dialogs()

    with pytest.raises(RuntimeError, match="dialog failed"):
        present_completion(dialogs, result, "gui")

    receipt = present_completion(dialogs, result, "gui")

    assert receipt.owner == "gui"
    assert dialogs.attempts == 2


def test_completed_presentation_does_not_retain_result() -> None:
    class Dialogs:
        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            return None

    dialogs = Dialogs()
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())
    result_reference = weakref.ref(result)

    present_completion(dialogs, result, "gui")
    del result
    gc.collect()

    assert result_reference() is None
    assert not dialogs.__dict__["_completion_presentations"].presentations


def test_present_completion_rejects_second_owner_for_same_result() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())

    class Dialogs:
        def set_report(self, report) -> None:
            return None

        def show_execution_result(self, presented, message: str) -> None:
            return None

    dialogs = Dialogs()
    present_completion(dialogs, result, "gui")

    with pytest.raises(CompletionOwnershipError):
        present_completion(dialogs, result, "droplet")


def test_present_completion_rejects_dispatcher_for_another_owner() -> None:
    result = ExecutionResult(ExecutionOutcome.COMPLETED, ())
    dispatcher = CompletionDispatcher("droplet")

    with pytest.raises(
        CompletionOwnershipError,
        match="already presented by droplet, not gui",
    ):
        present_completion(object(), result, "gui", dispatcher=dispatcher)


@pytest.mark.parametrize(
    ("outcome", "heading"),
    (
        (ExecutionOutcome.COMPLETED, "Completed"),
        (ExecutionOutcome.CANCELLED, "Cancelled"),
        (ExecutionOutcome.FAILED, "Failed"),
    ),
)
def test_completion_formats_every_terminal_outcome(
    outcome: ExecutionOutcome, heading: str
) -> None:
    result = ExecutionResult(outcome, ())

    assert format_completion(result).splitlines()[0] == heading


def test_completion_redacts_private_issue_details(tmp_path: Path) -> None:
    private = tmp_path / "client" / "photo.png"
    issue = ExecutionIssue(
        IssueStage.PHOTO_OPEN,
        IssueSeverity.ERROR,
        f"cannot open {private}; token=secret-value",
    )
    result = ExecutionResult(ExecutionOutcome.FAILED, (), issues=(issue,))

    message = format_completion(result)

    assert str(tmp_path) not in message
    assert "secret-value" not in message
    assert "<redacted>" in message


def test_folder_disappearance_returns_actionable_error(tmp_path: Path) -> None:
    folder = tmp_path / "vanished"

    def missing(_folder: Path) -> None:
        raise FileNotFoundError(folder)

    assert try_open_output_folder(folder, missing) == (
        "The output folder is no longer available."
    )
