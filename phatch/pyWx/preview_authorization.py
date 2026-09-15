from __future__ import annotations

import builtins
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TypeAlias

import wx

from phatch.services.action_schema_types import ActionDocument
from phatch.services.preview_reads import external_preview_reads
from phatch.services.preview_types import PreviewDependencies

_ = getattr(builtins, "_", lambda value: value)


class ReadConfirmationDialog(Protocol):
    def ShowModal(self) -> int: ...

    def GetSelections(self) -> Sequence[int]: ...

    def Destroy(self) -> object: ...


ReadDialogFactory: TypeAlias = Callable[
    [wx.Window, str, str, tuple[str, ...]], ReadConfirmationDialog
]


def create_read_confirmation_dialog(
    parent: wx.Window,
    message: str,
    caption: str,
    choices: tuple[str, ...],
) -> ReadConfirmationDialog:
    return wx.MultiChoiceDialog(parent, message, caption, list(choices))


@dataclass(frozen=True, slots=True)
class PreviewReadAuthorizer:
    dependencies: PreviewDependencies
    dialog_factory: ReadDialogFactory

    def authorize(
        self,
        parent: wx.Window,
        document: ActionDocument,
    ) -> tuple[Path, ...] | None:
        reads = external_preview_reads(document, self.dependencies)
        if not reads:
            return ()
        choices = tuple(
            f"{read.action_id}.{read.field_id}: {read.path.name}" for read in reads
        )
        dialog = self.dialog_factory(
            parent,
            _(
                "This preview needs to read the files below. Select every file "
                "and confirm to authorize this preview only."
            ),
            _("Authorize Preview File Reads"),
            choices,
        )
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return None
            selections = frozenset(dialog.GetSelections())
            if selections != frozenset(range(len(reads))):
                return None
            return tuple(read.path for read in reads)
        finally:
            dialog.Destroy()
