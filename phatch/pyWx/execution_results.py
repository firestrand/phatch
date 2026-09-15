from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from threading import Condition
from typing import assert_never
from weakref import ReferenceType, ref

from phatch.core.execution_types import ExecutionOutcome, ExecutionResult
from phatch.lib.process import Command, ProcessError
from phatch.lib.reverse_translation import _translate as _
from phatch.lib.system import open_directory_command
from phatch.services.completion import (
    CompletionDispatcher,
    CompletionOwner,
    CompletionReceipt,
)
from phatch.services.report_privacy import (
    ReportPrivacyContext,
    privacy_for_paths,
    redact_path,
    redact_text,
)


@dataclass(frozen=True, slots=True)
class CompletionOwnershipError(RuntimeError):
    first_owner: str
    second_owner: str

    def __str__(self) -> str:
        return (
            "execution result already presented by "
            f"{self.first_owner}, not {self.second_owner}"
        )


@dataclass(slots=True)
class _Presentation:
    result: ExecutionResult | None
    dispatcher: CompletionDispatcher
    finished: bool = False
    result_reference: ReferenceType[ExecutionResult] | None = None

    def matches(self, result: ExecutionResult) -> bool:
        return self.result is result or (
            self.result_reference is not None and self.result_reference() is result
        )


@dataclass(slots=True)
class _PresentationRegistry:
    condition: Condition = field(default_factory=Condition)
    presentations: dict[int, _Presentation] = field(default_factory=dict)


def _presentation_registry(dialog_service) -> _PresentationRegistry:
    registry = getattr(dialog_service, "_completion_presentations", None)
    if registry is not None:
        return registry
    candidate = _PresentationRegistry()
    return dialog_service.__dict__.setdefault("_completion_presentations", candidate)


def _discard_presentation(
    registry: _PresentationRegistry,
    result_key: int,
    presentation: _Presentation,
) -> None:
    with registry.condition:
        if registry.presentations.get(result_key) is presentation:
            del registry.presentations[result_key]


def output_folders(result: ExecutionResult) -> tuple[Path, ...]:
    folders: dict[str, Path] = {}
    for file_result in result.files:
        for output in file_result.outputs:
            if output.survived:
                folder = output.report.path.resolve().parent
                folders.setdefault(str(folder).casefold(), folder)
    return tuple(sorted(folders.values(), key=lambda path: str(path).casefold()))


def _result_privacy(result: ExecutionResult) -> ReportPrivacyContext:
    return privacy_for_paths(
        result.planned_sources,
        tuple(output.report.path for file in result.files for output in file.outputs),
    )


def format_completion(result: ExecutionResult) -> str:
    match result.outcome:
        case ExecutionOutcome.COMPLETED:
            heading = _("Completed")
        case ExecutionOutcome.CANCELLED:
            heading = _("Cancelled")
        case ExecutionOutcome.FAILED:
            heading = _("Failed")
        case unreachable:
            assert_never(unreachable)
    counts = result.counts
    lines = [
        heading,
        "",
        f"{_('Processed')}: {counts.processed}",
        f"{_('Skipped')}: {counts.skipped}",
        f"{_('Failed')}: {counts.failed}",
        f"{_('Cancelled')}: {counts.cancelled}",
        f"{_('Total')}: {counts.total}",
        f"{_('Elapsed')}: {result.elapsed_seconds:.2f}s",
    ]
    privacy = _result_privacy(result)
    if result.issues:
        lines.extend(("", f"{_('Issues')}:"))
        lines.extend(
            redact_text(f"- {issue.message}", privacy) for issue in result.issues
        )
    folders = output_folders(result)
    if folders:
        lines.extend(("", f"{_('Output folders')}:"))
        lines.extend(f"- {redact_path(folder, privacy)}" for folder in folders)
    return "\n".join(lines)


def open_output_folder(
    folder: Path,
    run_command: Callable[[Command], object],
    *,
    platform: str = sys.platform,
) -> None:
    run_command(open_directory_command(folder, platform))


def try_open_output_folder(
    folder: Path, open_directory: Callable[[Path], object]
) -> str | None:
    try:
        open_directory(folder)
    except (FileNotFoundError, NotADirectoryError, ProcessError):
        return _("The output folder is no longer available.")
    return None


def present_completion(
    dialog_service,
    result: ExecutionResult,
    owner: CompletionOwner,
    *,
    dispatcher: CompletionDispatcher | None = None,
) -> CompletionReceipt:
    active_dispatcher = dispatcher or CompletionDispatcher(owner)
    if active_dispatcher.owner != owner:
        raise CompletionOwnershipError(active_dispatcher.owner, owner)
    registry = _presentation_registry(dialog_service)
    result_key = id(result)
    while True:
        with registry.condition:
            previous = registry.presentations.get(result_key)
            if previous is None or not previous.matches(result):
                presentation = _Presentation(result, active_dispatcher)
                registry.presentations[result_key] = presentation
                break
            if previous.dispatcher.owner != owner:
                raise CompletionOwnershipError(previous.dispatcher.owner, owner)
            if previous.finished:
                return previous.dispatcher.receipt
            registry.condition.wait()
    try:
        privacy = _result_privacy(result)
        dialog_service.set_report(
            [
                (
                    report.filename,
                    report.width,
                    report.height,
                    report.mode,
                    redact_path(report.source, privacy),
                )
                for report in result.report
            ]
        )
        dialog_service.show_execution_result(result, format_completion(result))
        receipt = active_dispatcher.complete()
    except Exception:
        with registry.condition:
            if registry.presentations.get(result_key) is presentation:
                del registry.presentations[result_key]
            registry.condition.notify_all()
        raise
    with registry.condition:
        presentation.finished = True
        presentation.result_reference = ref(
            result,
            lambda _reference: _discard_presentation(
                registry,
                result_key,
                presentation,
            ),
        )
        presentation.result = None
        registry.condition.notify_all()
    return receipt


def show_result_dialog(
    parent, result: ExecutionResult, message: str, wx, system
) -> None:
    folders = output_folders(result)
    dialog = wx.Dialog(
        parent,
        title=_("Batch Result"),
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    body = wx.BoxSizer(wx.VERTICAL)
    heading_text, _separator, details_text = message.partition("\n")
    heading = wx.StaticText(dialog, label=heading_text)
    heading_font = heading.GetFont()
    heading_font.MakeBold()
    heading_font.SetPointSize(heading_font.GetPointSize() + 2)
    heading.SetFont(heading_font)
    heading.SetMinSize((480, -1))
    heading.SetMaxSize((480, -1))
    heading.Wrap(480)
    body.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 16)
    details = wx.TextCtrl(
        dialog,
        value=details_text.lstrip(),
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE | wx.TE_WORDWRAP,
    )
    details.SetMinSize((480, 260))
    details.SetMaxSize((480, -1))
    body.Add(details, 1, wx.EXPAND | wx.ALL, 16)
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    open_button = wx.Button(dialog, label=_("Open Output Folder"))
    close_button = wx.Button(dialog, wx.ID_CLOSE, _("Close"))
    open_button.Enable(any(folder.is_dir() for folder in folders))
    buttons.Add(open_button, 0, wx.RIGHT, 8)
    buttons.Add(close_button)
    body.Add(buttons, 0, wx.ALIGN_RIGHT | wx.LEFT | wx.RIGHT | wx.BOTTOM, 16)
    dialog.SetSizerAndFit(body)
    dialog.SetMinSize(dialog.GetSize())
    dialog.SetEscapeId(wx.ID_CLOSE)

    def open_selected(_event) -> None:
        available = tuple(folder for folder in folders if folder.is_dir())
        if not available:
            open_button.Disable()
            details.AppendText("\n\n" + _("The output folder is no longer available."))
            return
        selected = available[0]
        if len(available) > 1:
            chooser = wx.SingleChoiceDialog(
                dialog,
                _("Choose an output folder to open."),
                _("Output Folders"),
                tuple(str(folder) for folder in available),
            )
            try:
                if chooser.ShowModal() != wx.ID_OK:
                    return
                selected = available[chooser.GetSelection()]
            finally:
                chooser.Destroy()
        error = try_open_output_folder(selected, system.open_directory)
        if error is not None:
            open_button.Disable()
            details.AppendText("\n\n" + error)

    open_button.Bind(wx.EVT_BUTTON, open_selected)
    close_button.Bind(wx.EVT_BUTTON, lambda _event: dialog.EndModal(wx.ID_CLOSE))
    try:
        dialog.ShowModal()
    finally:
        dialog.Destroy()
