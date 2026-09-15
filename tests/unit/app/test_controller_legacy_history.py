from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from copy import deepcopy

from phatch.pyWx.controller import ActionListController
from phatch.pyWx.controller_tree import ActionDump, ActionTree, ControllerTreeAdapter
from phatch.pyWx.controller_tree import LegacyAction as LegacyActionProtocol
from phatch.services.editor_history import EditorSnapshot


class LegacyAction:
    def __init__(self, label: str, fields: dict[str, str]) -> None:
        self.label = label
        self.fields = fields

    def dump(self) -> ActionDump:
        return {"label": self.label, "fields": deepcopy(self.fields)}

    def load(self, fields: Mapping[str, str]) -> None:
        self.fields = dict(fields)


class LegacyTree:
    def __init__(self) -> None:
        self.actions: list[LegacyActionProtocol] = [
            LegacyAction("Resize", {"Width": "100"})
        ]
        self.selected: int | str | None = 0

    def export_forms(self) -> list[LegacyActionProtocol]:
        return list(self.actions)

    def get_selected_index(self) -> int | str | None:
        return self.selected

    def delete_all_forms(self) -> None:
        self.actions.clear()

    def append_forms(self, actions: Sequence[LegacyActionProtocol]) -> bool:
        self.actions.extend(actions)
        return bool(actions)

    def has_forms(self) -> bool:
        return bool(self.actions)

    def append_form_by_label_to_selected(self, label: str) -> None:
        return None

    def append_form_by_label_to_last(self, label: str) -> None:
        return None

    def remove_selected_form(self) -> bool:
        return False

    def move_form_selected_up(self) -> None:
        return None

    def move_form_selected_down(self) -> None:
        return None

    def enable_selected_form(self, enabled: bool) -> None:
        return None

    def is_form_selected(self) -> bool:
        return self.selected is not None

    def expand_forms(self) -> None:
        return None

    def collapse_forms(self) -> None:
        return None

    def enable_collapse_automatic(self, checked: bool) -> None:
        return None

    def close_popup(self) -> None:
        return None

    def resize_popup(self) -> None:
        return None

    def first_fields(self) -> Mapping[str, str]:
        return self.actions[0].dump().get("fields", {})


class RequiredTree:
    def delete_all_forms(self) -> None:
        return None

    def append_forms(self, actions: Sequence[LegacyActionProtocol]) -> bool:
        return bool(actions)

    def has_forms(self) -> bool:
        return False

    def export_forms(self) -> Iterable[LegacyActionProtocol]:
        return ()

    def append_form_by_label_to_selected(self, label: str) -> None:
        return None

    def append_form_by_label_to_last(self, label: str) -> None:
        return None

    def remove_selected_form(self) -> bool:
        return False

    def move_form_selected_up(self) -> None:
        return None

    def move_form_selected_down(self) -> None:
        return None

    def enable_selected_form(self, enabled: bool) -> None:
        return None

    def is_form_selected(self) -> bool:
        return False

    def expand_forms(self) -> None:
        return None

    def collapse_forms(self) -> None:
        return None

    def enable_collapse_automatic(self, checked: bool) -> None:
        return None

    def close_popup(self) -> None:
        return None

    def resize_popup(self) -> None:
        return None


def test_legacy_actions_roundtrip_through_undo_and_redo() -> None:
    tree = LegacyTree()
    controller = ActionListController(tree)
    transaction = controller.begin_transaction()
    tree.actions[0].load({"Width": "200"})

    assert controller.commit_transaction(transaction) is True
    assert controller.undo() is True
    assert tree.first_fields() == {"Width": "100"}
    assert controller.redo() is True
    assert tree.first_fields() == {"Width": "200"}


def test_invalid_legacy_selection_is_normalized_to_none() -> None:
    tree = LegacyTree()
    tree.selected = "invalid"
    controller = ActionListController(tree)

    assert controller.undo() is False
    assert controller.redo() is False


def test_adapter_handles_tree_without_optional_selection_or_popup_protocols() -> None:
    tree: ActionTree = RequiredTree()
    adapter = ControllerTreeAdapter(tree)

    assert adapter.selected_index() is None
    assert adapter.show_context_menu(object()) is None


def test_legacy_restore_writes_selection_when_supported() -> None:
    class SelectionLegacyTree(LegacyTree):
        def __init__(self) -> None:
            super().__init__()
            self.selections: list[int | None] = []

        def select_index(self, selected_index: int | None) -> None:
            self.selections.append(selected_index)

    tree = SelectionLegacyTree()
    adapter = ControllerTreeAdapter(tree)
    document = adapter.snapshot_document("before")

    adapter.restore_snapshot(EditorSnapshot(document, 0))

    assert tree.selections == [0]
