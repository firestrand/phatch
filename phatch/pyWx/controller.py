"""Controller objects that orchestrate GUI state transitions."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from phatch.core import ct
from phatch.pyWx.controller_history import ActionListState, ControllerHistory
from phatch.pyWx.controller_tree import (
    ActionTree,
    ContextMenu,
    ControllerTreeAdapter,
    LegacyAction,
)
from phatch.services.action_list import ActionListService
from phatch.services.action_schema_types import ActionDocument
from phatch.services.editor_history import HistoryTransaction
from phatch.services.preflight import PreflightRequest, PreflightResult


class PreflightProvider(Protocol):
    def preflight(self, request: PreflightRequest) -> PreflightResult: ...


class ActionListController:
    """Coordinates state changes for the action list editor."""

    def __init__(
        self,
        tree: ActionTree,
        action_service: PreflightProvider | None = None,
    ):
        self._tree = tree
        self._tree_adapter = ControllerTreeAdapter(tree)
        self._action_service = action_service or ActionListService()
        initial_state = ActionListState()
        self._editor = ControllerHistory(
            self._tree_adapter.snapshot_document(initial_state.description),
            self._tree_adapter.selected_index(),
            self._tree_adapter.restore_snapshot,
        )

    @property
    def state(self) -> ActionListState:
        return self._editor.state

    @state.setter
    def state(self, state: ActionListState) -> None:
        self._editor.state = state

    def preflight(self, request: PreflightRequest) -> PreflightResult:
        return self._action_service.preflight(request)

    # --- lifecycle -------------------------------------------------
    def new_actionlist(self) -> ActionListState:
        """Reset the editor to an empty action list."""

        self._tree.delete_all_forms()
        state = ActionListState()
        self._editor.reset(
            state,
            self._tree_adapter.snapshot_document(state.description),
            self._tree_adapter.selected_index(),
        )
        return self.state

    def apply_loaded_data(
        self,
        filename: str,
        actions: Sequence[LegacyAction],
        description: str,
    ) -> ActionListState:
        """Apply loaded actions/description to the editor and update state."""

        self._tree.delete_all_forms()
        self._tree.append_forms(actions)
        has_actions = bool(self._tree.has_forms())
        clean_description = description or ct.ACTION_LIST_DESCRIPTION
        state = ActionListState(
            filename=filename,
            description=clean_description,
            saved_description=clean_description,
            dirty=False,
            has_actions=has_actions,
        )
        document = self._tree_adapter.snapshot_document(clean_description)
        selected_index = self._tree_adapter.selected_index()
        self._editor.reset(state, document, selected_index)
        return self.state

    # --- accessors -------------------------------------------------
    def export_actions(self) -> Iterable[LegacyAction]:
        return self._tree.export_forms()

    def refresh_has_actions(self) -> bool:
        self.state.has_actions = bool(self._tree.has_forms())
        return self.state.has_actions

    @property
    def current_document(self) -> ActionDocument:
        return self._editor.current_document

    @property
    def checkpoint(self) -> ActionDocument:
        return self._editor.checkpoint

    @property
    def can_undo(self) -> bool:
        return self._editor.can_undo

    @property
    def can_redo(self) -> bool:
        return self._editor.can_redo

    @property
    def is_restoring(self) -> bool:
        return self._editor.is_restoring

    def add_history_listener(self, listener: Callable[[], None]) -> None:
        self._editor.add_listener(listener)

    def remove_history_listener(self, listener: Callable[[], None]) -> None:
        self._editor.remove_listener(listener)

    def begin_transaction(self) -> HistoryTransaction:
        return self._editor.begin()

    def commit_transaction(self, transaction: HistoryTransaction) -> bool:
        return self._editor.commit(
            transaction,
            self._tree_adapter.snapshot_document(self.state.description),
            self._tree_adapter.selected_index(),
        )

    def cancel_transaction(self, transaction: HistoryTransaction) -> None:
        self._editor.cancel(transaction)

    def undo(self) -> bool:
        return self._editor.undo()

    def redo(self) -> bool:
        return self._editor.redo()

    def begin_open(self) -> None:
        self._editor.begin_open()

    def finish_open(self, *, success: bool) -> None:
        self._editor.finish_open(success=success)

    def begin_save(self) -> None:
        self._editor.begin_save()

    def finish_save(self, *, success: bool) -> None:
        self._editor.finish_save(
            success=success,
            document=self._tree_adapter.snapshot_document(self.state.description),
            selected_index=self._tree_adapter.selected_index(),
        )

    # --- state transitions ----------------------------------------
    def mark_dirty(self) -> None:
        transaction = self._editor.begin()
        self.commit_transaction(transaction)

    def mark_clean(self, description: str | None = None) -> None:
        current_description = (
            description if description is not None else self.state.description
        )
        self.state.saved_description = current_description
        self.state.description = current_description
        self.state.dirty = False
        if self._editor.saving or self._editor.opening:
            return
        self._editor.mark_saved(
            self._tree_adapter.snapshot_document(current_description),
            self._tree_adapter.selected_index(),
        )

    def update_description(self, description: str) -> None:
        transaction = self._editor.begin()
        self.state.description = description
        self.commit_transaction(transaction)

    # --- action modifications ------------------------------------
    def add_action_by_label(self, label: str) -> None:
        transaction = self._editor.begin()
        self._tree.append_form_by_label_to_selected(label)
        self.commit_transaction(transaction)

    def add_action_by_label_to_last(self, label: str) -> None:
        transaction = self._editor.begin()
        self._tree.append_form_by_label_to_last(label)
        self.commit_transaction(transaction)

    def remove_selected_action(self) -> bool:
        transaction = self._editor.begin()
        removed = self._tree.remove_selected_form()
        if removed:
            self.commit_transaction(transaction)
        else:
            self._editor.cancel(transaction)
        return removed

    def move_selected_action_up(self) -> None:
        transaction = self._editor.begin()
        self._tree.move_form_selected_up()
        self.commit_transaction(transaction)

    def move_selected_action_down(self) -> None:
        transaction = self._editor.begin()
        self._tree.move_form_selected_down()
        self.commit_transaction(transaction)

    def enable_selected_action(self, enabled: bool) -> None:
        transaction = self._editor.begin()
        self._tree.enable_selected_form(enabled)
        self.commit_transaction(transaction)

    def has_selected_action(self) -> bool:
        return self._tree.is_form_selected()

    def expand_all(self) -> None:
        self._tree.expand_forms()

    def collapse_all(self) -> None:
        self._tree.collapse_forms()

    def enable_collapse_automatic(self, checked: bool) -> None:
        self._tree.enable_collapse_automatic(checked)

    def has_forms(self) -> bool:
        return self._tree.has_forms()

    def close_context_popup(self) -> None:
        self._tree.close_popup()

    def resize_popup(self) -> None:
        self._tree.resize_popup()

    def show_context_menu(self, menu: ContextMenu) -> None:
        self._tree_adapter.show_context_menu(menu)
