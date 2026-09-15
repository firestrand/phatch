"""Immutable action-document snapshots and transactional editor history."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Final

from phatch.services.action_schema_types import (
    ActionDocument,
    ActionField,
    ActionSpec,
)

HISTORY_LIMIT: Final = 100


@dataclass(frozen=True, slots=True)
class TransactionStateError(RuntimeError):
    """Raised when a transaction is no longer the active editor transaction."""

    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class EditorSnapshot:
    document: ActionDocument
    selected_index: int | None


class _HistoryOwner:
    __slots__ = ()


@dataclass(frozen=True, slots=True)
class HistoryTransaction:
    token: int
    before: EditorSnapshot
    _owner: _HistoryOwner = field(repr=False)


class EditorHistory:
    """Own transient undo/redo state for one canonical action document."""

    def __init__(
        self,
        document: ActionDocument,
        selected_index: int | None = None,
    ) -> None:
        initial = _freeze_snapshot(document, selected_index)
        self._current = initial
        self._checkpoint = _freeze_document(initial.document)
        self._undo: list[EditorSnapshot] = []
        self._redo: list[EditorSnapshot] = []
        self._owner = _HistoryOwner()
        self._active_transaction: HistoryTransaction | None = None
        self._next_token = 0
        self._restoring_depth = 0

    @property
    def current(self) -> EditorSnapshot:
        return self._current

    @property
    def checkpoint(self) -> ActionDocument:
        return self._checkpoint

    @property
    def is_dirty(self) -> bool:
        return self._current.document != self._checkpoint

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)

    @property
    def is_restoring(self) -> bool:
        return self._restoring_depth > 0

    def begin(self) -> HistoryTransaction:
        if self._active_transaction is not None:
            raise TransactionStateError("an editor transaction is already active")
        transaction = HistoryTransaction(self._next_token, self._current, self._owner)
        self._next_token += 1
        self._active_transaction = transaction
        return transaction

    def commit(
        self,
        transaction: HistoryTransaction,
        document: ActionDocument,
        selected_index: int | None,
    ) -> bool:
        self._require_active(transaction)
        self._active_transaction = None
        if self.is_restoring:
            return False
        after = _freeze_snapshot(document, selected_index)
        if after.document == transaction.before.document:
            self._current = after
            return False
        self._undo.append(transaction.before)
        if len(self._undo) > HISTORY_LIMIT:
            del self._undo[0]
        self._current = after
        self._redo.clear()
        return True

    def cancel(self, transaction: HistoryTransaction) -> None:
        self._require_active(transaction)
        self._active_transaction = None

    def undo(self) -> EditorSnapshot:
        self._require_idle()
        if not self._undo:
            return self._current
        self._redo.append(self._current)
        self._current = self._undo.pop()
        return self._current

    def redo(self) -> EditorSnapshot:
        self._require_idle()
        if not self._redo:
            return self._current
        self._undo.append(self._current)
        self._current = self._redo.pop()
        return self._current

    def select(self, selected_index: int | None) -> EditorSnapshot:
        self._current = _freeze_snapshot(self._current.document, selected_index)
        return self._current

    def mark_saved(self) -> None:
        self._checkpoint = _freeze_document(self._current.document)

    def clear(
        self,
        document: ActionDocument,
        selected_index: int | None = None,
    ) -> None:
        self._require_idle()
        current = _freeze_snapshot(document, selected_index)
        self._current = current
        self._checkpoint = _freeze_document(current.document)
        self._undo.clear()
        self._redo.clear()

    @contextmanager
    def restoring(self) -> Iterator[None]:
        self._restoring_depth += 1
        try:
            yield
        finally:
            self._restoring_depth -= 1

    def _require_active(self, transaction: HistoryTransaction) -> None:
        if (
            transaction._owner is not self._owner
            or transaction is not self._active_transaction
        ):
            raise TransactionStateError("editor transaction is not active")

    def _require_idle(self) -> None:
        if self._active_transaction is not None:
            raise TransactionStateError("finish the active editor transaction first")


def _freeze_document(document: ActionDocument) -> ActionDocument:
    return ActionDocument(
        schema_version=document.schema_version,
        description=document.description,
        actions=tuple(
            ActionSpec(
                action_id=action.action_id,
                fields=tuple(
                    ActionField(field_id=field.field_id, value=field.value)
                    for field in action.fields
                ),
            )
            for action in document.actions
        ),
    )


def _freeze_snapshot(
    document: ActionDocument,
    selected_index: int | None,
) -> EditorSnapshot:
    frozen = _freeze_document(document)
    action_count = len(frozen.actions)
    if action_count == 0 or selected_index is None:
        clamped = None
    else:
        clamped = min(max(selected_index, 0), action_count - 1)
    return EditorSnapshot(frozen, clamped)
