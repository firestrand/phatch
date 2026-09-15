from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy
from typing import NotRequired, Protocol, TypedDict, runtime_checkable

from phatch.services.action_schema import normalize_identifier
from phatch.services.action_schema_types import (
    SCHEMA_VERSION,
    ActionDocument,
    ActionField,
    ActionSpec,
)
from phatch.services.editor_history import EditorSnapshot


class ActionDump(TypedDict):
    label: str
    fields: NotRequired[Mapping[str, str]]


class LegacyAction(Protocol):
    def dump(self) -> ActionDump: ...

    def load(self, fields: Mapping[str, str]) -> None: ...


class ContextMenu(Protocol):
    pass


class ActionTree(Protocol):
    def delete_all_forms(self) -> None: ...

    def append_forms(self, actions: Sequence[LegacyAction]) -> bool: ...

    def has_forms(self) -> bool: ...

    def export_forms(self) -> Iterable[LegacyAction]: ...

    def append_form_by_label_to_selected(self, label: str) -> None: ...

    def append_form_by_label_to_last(self, label: str) -> None: ...

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


@runtime_checkable
class SnapshotTree(Protocol):
    def snapshot_document(self, description: str) -> ActionDocument: ...


@runtime_checkable
class RestoreTree(Protocol):
    def restore_document(
        self,
        document: ActionDocument,
        selected_index: int | None,
    ) -> None: ...


@runtime_checkable
class ReadSelectionTree(Protocol):
    def get_selected_index(self) -> int | str | None: ...


@runtime_checkable
class WriteSelectionTree(Protocol):
    def select_index(self, selected_index: int | None) -> None: ...


@runtime_checkable
class PopupTree(Protocol):
    def popup_menu(self, menu: ContextMenu) -> None: ...


@runtime_checkable
class LegacyPopupTree(Protocol):
    def PopupMenu(self, menu: ContextMenu) -> None: ...


class ControllerTreeAdapter:
    def __init__(self, tree: ActionTree) -> None:
        self._tree = tree
        self._templates: dict[str, LegacyAction] = {}

    def selected_index(self) -> int | None:
        match self._tree:
            case ReadSelectionTree() as tree:
                match tree.get_selected_index():
                    case int() as selected_index:
                        return selected_index
                    case None | str():
                        return None
            case _:
                return None

    def snapshot_document(self, description: str) -> ActionDocument:
        match self._tree:
            case SnapshotTree() as tree:
                return tree.snapshot_document(description)
            case _:
                return self._snapshot_legacy(description)

    def restore_snapshot(self, snapshot: EditorSnapshot) -> None:
        match self._tree:
            case RestoreTree() as tree:
                tree.restore_document(snapshot.document, snapshot.selected_index)
            case _:
                self._restore_legacy(snapshot)

    def show_context_menu(self, menu: ContextMenu) -> None:
        match self._tree:
            case PopupTree() as tree if callable(tree.popup_menu):
                tree.popup_menu(menu)
            case LegacyPopupTree() as tree:
                tree.PopupMenu(menu)
            case _:
                return

    def _snapshot_legacy(self, description: str) -> ActionDocument:
        specs: list[ActionSpec] = []
        for action in self._tree.export_forms():
            dumped = action.dump()
            action_id = normalize_identifier(dumped["label"])
            fields = tuple(
                ActionField(normalize_identifier(label), value)
                for label, value in dumped.get("fields", {}).items()
            )
            specs.append(ActionSpec(action_id, fields))
            self._templates[action_id] = deepcopy(action)
        return ActionDocument(SCHEMA_VERSION, description, tuple(specs))

    def _restore_legacy(self, snapshot: EditorSnapshot) -> None:
        actions: list[LegacyAction] = []
        for spec in snapshot.document.actions:
            action = deepcopy(self._templates[spec.action_id])
            dumped_fields = action.dump().get("fields", {})
            labels = {normalize_identifier(label): label for label in dumped_fields}
            action.load({labels[field.field_id]: field.value for field in spec.fields})
            actions.append(action)
        self._tree.delete_all_forms()
        self._tree.append_forms(actions)
        match self._tree:
            case WriteSelectionTree() as tree:
                tree.select_index(snapshot.selected_index)
            case _:
                return
