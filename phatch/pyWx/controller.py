"""Controller objects that orchestrate GUI state transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, Sequence

from phatch.core import ct


class ActionTree(Protocol):
    """Subset of the action tree API used by the controller."""

    def delete_all_forms(self) -> None: ...

    def append_forms(self, actions: Sequence[Any]) -> bool: ...

    def has_forms(self) -> bool: ...

    def export_forms(self) -> Iterable[Any]: ...

    def append_form_by_label_to_selected(self, label: str) -> None: ...

    def remove_selected_form(self) -> bool: ...

    def move_form_selected_up(self) -> None: ...

    def move_form_selected_down(self) -> None: ...

    def enable_selected_form(self, enabled: bool) -> None: ...

    def is_form_selected(self) -> bool: ...

    def expand_forms(self) -> None: ...

    def collapse_forms(self) -> None: ...

    def enable_collapse_automatic(self, checked: bool) -> None: ...

    def close_popup(self) -> None: ...

    def resize_popup(self) -> None: ...

    def popup_menu(self, menu: object) -> None: ...


@dataclass
class ActionListState:
    """Represents the mutable state of the action list editor."""

    filename: str = ct.UNKNOWN
    description: str = ct.ACTION_LIST_DESCRIPTION
    saved_description: str = ct.ACTION_LIST_DESCRIPTION
    dirty: bool = False
    has_actions: bool = False

    def dirty_indicator(self) -> str:
        """Return the suffix used in the window title."""

        return '*' if self.dirty else ''


class ActionListController:
    """Coordinates state changes for the action list editor."""

    def __init__(self, tree: ActionTree):
        self._tree = tree
        self.state = ActionListState()

    # --- lifecycle -------------------------------------------------
    def new_actionlist(self) -> ActionListState:
        """Reset the editor to an empty action list."""

        self._tree.delete_all_forms()
        self.state = ActionListState()
        return self.state

    def apply_loaded_data(
        self,
        filename: str,
        actions: Sequence[Any],
        description: str,
    ) -> ActionListState:
        """Apply loaded actions/description to the editor and update state."""

        self._tree.delete_all_forms()
        self._tree.append_forms(actions)
        has_actions = bool(self._tree.has_forms())
        clean_description = description or ct.ACTION_LIST_DESCRIPTION
        self.state = ActionListState(
            filename=filename,
            description=clean_description,
            saved_description=clean_description,
            dirty=False,
            has_actions=has_actions,
        )
        return self.state

    # --- accessors -------------------------------------------------
    def export_actions(self) -> Iterable[Any]:
        return self._tree.export_forms()

    def refresh_has_actions(self) -> bool:
        self.state.has_actions = bool(self._tree.has_forms())
        return self.state.has_actions

    # --- state transitions ----------------------------------------
    def mark_dirty(self) -> None:
        self.state.dirty = True

    def mark_clean(self, description: str | None = None) -> None:
        current_description = description if description is not None else self.state.description
        self.state.saved_description = current_description
        self.state.description = current_description
        self.state.dirty = False

    def update_description(self, description: str) -> None:
        self.state.description = description
        self.state.dirty = description != self.state.saved_description

    # --- action modifications ------------------------------------
    def add_action_by_label(self, label: str) -> None:
        self._tree.append_form_by_label_to_selected(label)
        self.state.has_actions = True
        self.mark_dirty()

    def add_action_by_label_to_last(self, label: str) -> None:
        self._tree.append_form_by_label_to_last(label)
        self.state.has_actions = True
        self.mark_dirty()

    def remove_selected_action(self) -> bool:
        removed = self._tree.remove_selected_form()
        if removed:
            self.state.has_actions = bool(self._tree.has_forms())
            if self.state.has_actions:
                self.mark_dirty()
            else:
                self.mark_clean(self.state.description)
        return removed

    def move_selected_action_up(self) -> None:
        self._tree.move_form_selected_up()
        self.mark_dirty()

    def move_selected_action_down(self) -> None:
        self._tree.move_form_selected_down()
        self.mark_dirty()

    def enable_selected_action(self, enabled: bool) -> None:
        self._tree.enable_selected_form(enabled)
        self.mark_dirty()

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

    def show_context_menu(self, menu: object) -> None:
        popup = getattr(self._tree, "popup_menu", None)
        if popup is None:
            popup = getattr(self._tree, "PopupMenu")
        popup(menu)
