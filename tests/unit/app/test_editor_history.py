from __future__ import annotations

from collections.abc import Callable

import pytest

from phatch.services.action_schema_types import (
    SCHEMA_VERSION,
    ActionDocument,
    ActionField,
    ActionSpec,
)
from phatch.services.editor_history import (
    EditorHistory,
    EditorSnapshot,
    TransactionStateError,
)

HistoryState = tuple[EditorSnapshot, ActionDocument, int, int]


def document(description: str, action_count: int = 1) -> ActionDocument:
    actions = tuple(
        ActionSpec(
            f"action_{index}",
            (ActionField("value", str(index)),),
        )
        for index in range(action_count)
    )
    return ActionDocument(SCHEMA_VERSION, description, actions)


def commit(
    history: EditorHistory,
    next_document: ActionDocument,
    selected: int | None = 0,
) -> bool:
    transaction = history.begin()
    return history.commit(transaction, next_document, selected)


def history_state(history: EditorHistory) -> HistoryState:
    return history.current, history.checkpoint, history.undo_count, history.redo_count


def test_distinct_commit_records_one_undoable_snapshot() -> None:
    # Given
    history = EditorHistory(document("before"), 0)

    # When
    changed = commit(history, document("after"))

    # Then
    assert changed is True
    assert history.current.document == document("after")
    assert history.undo_count == 1
    assert history.redo_count == 0


def test_noop_commit_does_not_record_history_but_updates_selection() -> None:
    # Given
    initial = document("same", action_count=2)
    history = EditorHistory(initial, 0)

    # When
    changed = commit(history, initial, selected=1)

    # Then
    assert changed is False
    assert history.current.selected_index == 1
    assert history.undo_count == 0


def test_cancel_keeps_document_stacks_and_checkpoint_unchanged() -> None:
    # Given
    initial = document("initial")
    history = EditorHistory(initial, 0)
    transaction = history.begin()

    # When
    history.cancel(transaction)

    # Then
    assert history.current.document == initial
    assert history.checkpoint == initial
    assert (history.undo_count, history.redo_count) == (0, 0)
    assert history.is_dirty is False


def test_history_retains_exactly_100_committed_edits() -> None:
    # Given
    history = EditorHistory(document("edit-0"), 0)
    for edit in range(1, 101):
        commit(history, document(f"edit-{edit}"))

    # When
    for _ in range(100):
        history.undo()

    # Then
    assert history.current.document == document("edit-0")
    assert history.can_undo is False
    assert history.redo_count == 100


def test_101st_commit_prunes_only_oldest_undo_state() -> None:
    # Given
    history = EditorHistory(document("edit-0"), 0)
    for edit in range(1, 102):
        commit(history, document(f"edit-{edit}"))

    # When
    for _ in range(100):
        history.undo()

    # Then
    assert history.current.document == document("edit-1")
    assert history.can_undo is False


def test_commit_after_undo_invalidates_redo_branch() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    commit(history, document("first"))
    commit(history, document("abandoned"))
    history.undo()

    # When
    commit(history, document("branch"))

    # Then
    assert history.current.document == document("branch")
    assert history.can_redo is False


def test_saved_checkpoint_survives_history_pruning() -> None:
    # Given
    saved = document("saved")
    history = EditorHistory(saved, 0)
    history.mark_saved()

    # When
    for edit in range(101):
        commit(history, document(f"later-{edit}"))

    # Then
    assert history.checkpoint == saved
    assert history.is_dirty is True


@pytest.mark.parametrize(
    ("action_count", "requested", "expected"),
    [(0, 4, None), (3, -5, 0), (3, 8, 2), (3, None, None)],
)
def test_selection_is_clamped_to_document(
    action_count: int,
    requested: int | None,
    expected: int | None,
) -> None:
    # Given / When
    history = EditorHistory(document("selection", action_count), requested)

    # Then
    assert history.current.selected_index == expected


def test_emptying_all_actions_is_dirty_when_checkpoint_had_actions() -> None:
    # Given
    history = EditorHistory(document("same", action_count=1), 0)

    # When
    commit(history, document("same", action_count=0), selected=None)

    # Then
    assert history.is_dirty is True
    assert history.current.selected_index is None


def test_undo_and_redo_cross_saved_checkpoint_by_document_equality() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    commit(history, document("saved"))
    history.mark_saved()
    commit(history, document("later"))

    # When / Then
    history.undo()
    assert history.is_dirty is False
    history.undo()
    assert history.is_dirty is True
    history.redo()
    assert history.is_dirty is False
    history.redo()
    assert history.is_dirty is True


def test_selection_restores_without_participating_in_dirty_equality() -> None:
    # Given
    initial = document("initial", action_count=2)
    history = EditorHistory(initial, 0)
    commit(history, document("changed", action_count=2), selected=1)

    # When / Then
    assert history.undo().selected_index == 0
    history.select(1)
    assert history.is_dirty is False
    assert history.redo().selected_index == 1


def test_history_owns_detached_canonical_document_snapshots() -> None:
    # Given
    initial = document("initial")
    changed = document("changed")
    history = EditorHistory(initial, 0)

    # When
    commit(history, changed)

    # Then
    assert history.current.document == changed
    assert history.current.document is not changed
    assert history.current.document.actions is not changed.actions
    assert history.current.document.actions[0] is not changed.actions[0]
    assert history.current.document.actions[0].fields is not changed.actions[0].fields


def test_restoration_scope_suppresses_callback_commits() -> None:
    # Given
    initial = document("initial")
    history = EditorHistory(initial, 0)

    # When
    with history.restoring():
        changed = commit(history, document("callback"))
        restoring_inside_scope = history.is_restoring

    # Then
    assert changed is False
    assert restoring_inside_scope is True
    assert history.is_restoring is False
    assert history.current.document == initial
    assert history.undo_count == 0


def test_transaction_cannot_be_committed_after_cancel() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    transaction = history.begin()
    history.cancel(transaction)

    # When / Then
    with pytest.raises(TransactionStateError):
        history.commit(transaction, document("invalid"), 0)


def test_second_transaction_cannot_begin_while_one_is_active() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    transaction = history.begin()

    # When / Then
    with pytest.raises(
        TransactionStateError,
        match="an editor transaction is already active",
    ):
        history.begin()
    history.cancel(transaction)


def test_only_active_transaction_can_be_cancelled() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    first = history.begin()
    history.cancel(first)
    active = history.begin()

    # When / Then
    with pytest.raises(TransactionStateError):
        history.cancel(first)
    history.cancel(active)


def test_foreign_transaction_with_overlapping_token_cannot_cancel() -> None:
    # Given
    initial = document("same")
    source = EditorHistory(initial, 0)
    target = EditorHistory(initial, 0)
    foreign = source.begin()
    target_transaction = target.begin()
    before = history_state(target)

    # When / Then
    assert foreign.token == target_transaction.token == 0
    assert foreign != target_transaction
    with pytest.raises(TransactionStateError):
        target.cancel(foreign)
    assert history_state(target) == before
    target.cancel(target_transaction)
    source.cancel(foreign)


def test_foreign_transaction_with_overlapping_token_cannot_commit() -> None:
    # Given
    source = EditorHistory(document("source"), 0)
    target = EditorHistory(document("target"), 0)
    foreign = source.begin()
    target_transaction = target.begin()
    before = history_state(target)

    # When / Then
    with pytest.raises(TransactionStateError):
        target.commit(foreign, document("injected"), 0)
    assert history_state(target) == before
    target.cancel(target_transaction)
    source.cancel(foreign)


def test_stale_transaction_cannot_commit_over_newer_active_transaction() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    stale = history.begin()
    history.cancel(stale)
    active = history.begin()
    before = history_state(history)

    # When / Then
    with pytest.raises(TransactionStateError):
        history.commit(stale, document("replayed"), 0)
    assert history_state(history) == before
    history.cancel(active)


def test_undo_and_redo_are_noops_when_their_stacks_are_empty() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)

    # When
    undone = history.undo()
    redone = history.redo()

    # Then
    assert undone == history.current
    assert redone == history.current


@pytest.mark.parametrize(
    "operation",
    [
        EditorHistory.undo,
        EditorHistory.redo,
        lambda history: history.clear(document("opened")),
    ],
)
def test_restoration_operations_require_idle_transaction(
    operation: Callable[[EditorHistory], EditorSnapshot | None],
) -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    transaction = history.begin()

    # When / Then
    with pytest.raises(
        TransactionStateError,
        match="finish the active editor transaction first",
    ):
        operation(history)
    history.cancel(transaction)


def test_save_moves_checkpoint_without_clearing_history() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    commit(history, document("saved"))

    # When
    history.mark_saved()

    # Then
    assert history.is_dirty is False
    assert history.undo_count == 1
    assert history.checkpoint == document("saved")


def test_clear_replaces_document_checkpoint_and_both_stacks() -> None:
    # Given
    history = EditorHistory(document("initial"), 0)
    commit(history, document("edited"))
    history.undo()

    # When
    history.clear(document("opened", action_count=0), selected_index=9)

    # Then
    assert history.current.document == document("opened", action_count=0)
    assert history.current.selected_index is None
    assert history.checkpoint == document("opened", action_count=0)
    assert (history.undo_count, history.redo_count) == (0, 0)
    assert history.is_dirty is False
