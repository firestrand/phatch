"""History and lifecycle state for the action-list controller."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from phatch.core import ct
from phatch.services.action_schema_types import ActionDocument
from phatch.services.editor_history import (
    EditorHistory,
    EditorSnapshot,
    HistoryTransaction,
)


@dataclass(slots=True)
class ActionListState:
    """Mutable display state synchronized from canonical editor history."""

    filename: str = ct.UNKNOWN
    description: str = ct.ACTION_LIST_DESCRIPTION
    saved_description: str = ct.ACTION_LIST_DESCRIPTION
    dirty: bool = False
    has_actions: bool = False

    def dirty_indicator(self) -> str:
        return "*" if self.dirty else ""


class ControllerHistory:
    """Coordinate editor history with save and open lifecycle transitions."""

    def __init__(
        self,
        document: ActionDocument,
        selected_index: int | None,
        restore: Callable[[EditorSnapshot], None],
    ) -> None:
        self.state = ActionListState()
        self._history = EditorHistory(document, selected_index)
        self._restore = restore
        self._listeners: list[Callable[[], None]] = []
        self._open_state: ActionListState | None = None
        self._open_document: ActionDocument | None = None
        self._open_selection: int | None = None
        self._save_state: ActionListState | None = None

    @property
    def current_document(self) -> ActionDocument:
        return self._history.current.document

    @property
    def checkpoint(self) -> ActionDocument:
        return self._history.checkpoint

    @property
    def can_undo(self) -> bool:
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        return self._history.can_redo

    @property
    def is_restoring(self) -> bool:
        return self._history.is_restoring

    @property
    def opening(self) -> bool:
        return self._open_state is not None

    @property
    def saving(self) -> bool:
        return self._save_state is not None

    def add_listener(self, listener: Callable[[], None]) -> None:
        if listener not in self._listeners:
            self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def begin(self) -> HistoryTransaction:
        return self._history.begin()

    def commit(
        self,
        transaction: HistoryTransaction,
        document: ActionDocument,
        selected_index: int | None,
    ) -> bool:
        changed = self._history.commit(transaction, document, selected_index)
        self.sync_state()
        if changed:
            self._notify()
        return changed

    def cancel(self, transaction: HistoryTransaction) -> None:
        self._history.cancel(transaction)
        self._apply_restore(transaction.before)
        self.sync_state()

    def undo(self) -> bool:
        before = self._history.current
        snapshot = self._history.undo()
        if snapshot == before:
            return False
        self._apply_restore(snapshot)
        self.sync_state()
        self._notify()
        return True

    def redo(self) -> bool:
        before = self._history.current
        snapshot = self._history.redo()
        if snapshot == before:
            return False
        self._apply_restore(snapshot)
        self.sync_state()
        self._notify()
        return True

    def reset(
        self,
        state: ActionListState,
        document: ActionDocument,
        selected_index: int | None,
    ) -> None:
        self.state = state
        if self.opening:
            self._open_document = document
            self._open_selection = selected_index
            return
        self._history.clear(document, selected_index)
        self.sync_state()
        self._notify()

    def begin_open(self) -> None:
        self._open_state = replace(self.state)
        self.state = replace(self.state)
        self._open_document = None
        self._open_selection = None

    def finish_open(self, *, success: bool) -> None:
        previous_state = self._open_state
        document = self._open_document
        selected_index = self._open_selection
        self._open_state = None
        self._open_document = None
        self._open_selection = None
        if success and document is not None:
            self._history.clear(document, selected_index)
            self.sync_state()
            self._notify()
            return
        if previous_state is not None:
            self.state = previous_state
            self._apply_restore(self._history.current)
            self.sync_state()

    def begin_save(self) -> None:
        self._save_state = replace(self.state)
        self.state = replace(self.state)

    def finish_save(
        self,
        *,
        success: bool,
        document: ActionDocument,
        selected_index: int | None,
    ) -> None:
        previous_state = self._save_state
        self._save_state = None
        if success:
            transaction = self._history.begin()
            self._history.commit(transaction, document, selected_index)
            self._history.mark_saved()
            self.sync_state()
            self._notify()
            return
        if previous_state is not None:
            self.state = previous_state
            self.sync_state()

    def mark_saved(
        self,
        document: ActionDocument,
        selected_index: int | None,
    ) -> None:
        transaction = self._history.begin()
        changed = self._history.commit(transaction, document, selected_index)
        self._history.mark_saved()
        self.sync_state()
        if changed:
            self._notify()

    def sync_state(self) -> None:
        self.state.description = self._history.current.document.description
        self.state.saved_description = self._history.checkpoint.description
        self.state.dirty = self._history.is_dirty
        self.state.has_actions = bool(self._history.current.document.actions)

    def _notify(self) -> None:
        for listener in tuple(self._listeners):
            listener()

    def _apply_restore(self, snapshot: EditorSnapshot) -> None:
        with self._history.restoring():
            self._restore(snapshot)
