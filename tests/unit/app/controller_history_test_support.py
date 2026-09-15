from __future__ import annotations

from collections.abc import Mapping, Sequence

from phatch.pyWx.controller import ActionListController
from phatch.pyWx.controller_tree import ActionDump, ContextMenu, LegacyAction
from phatch.services.action_schema_types import (
    SCHEMA_VERSION,
    ActionDocument,
    ActionField,
    ActionSpec,
)


class FakeAction:
    def __init__(
        self,
        action_id: str,
        fields: dict[str, str] | None = None,
    ) -> None:
        self.action_id = action_id
        self.fields = dict(fields or {})

    def dump(self) -> ActionDump:
        return {"label": self.action_id, "fields": self.fields}

    def load(self, fields: Mapping[str, str]) -> None:
        self.fields = dict(fields)


class HistoryTree:
    def __init__(self, actions: list[FakeAction] | None = None) -> None:
        self.actions = list(actions or [])
        self.selected_index = 0 if self.actions else None

    def snapshot_document(self, description: str) -> ActionDocument:
        return ActionDocument(
            SCHEMA_VERSION,
            description,
            tuple(
                ActionSpec(
                    action.action_id,
                    tuple(
                        ActionField(field_id, value)
                        for field_id, value in sorted(action.fields.items())
                    ),
                )
                for action in self.actions
            ),
        )

    def restore_document(
        self,
        document: ActionDocument,
        selected_index: int | None,
    ) -> None:
        self.actions = [
            FakeAction(
                action.action_id,
                {field.field_id: field.value for field in action.fields},
            )
            for action in document.actions
        ]
        self.selected_index = selected_index

    def get_selected_index(self) -> int | None:
        return self.selected_index

    def delete_all_forms(self) -> None:
        self.actions.clear()
        self.selected_index = None

    def append_forms(self, actions: Sequence[LegacyAction]) -> bool:
        for action in actions:
            dumped = action.dump()
            self.actions.append(
                FakeAction(dumped["label"], dict(dumped.get("fields", {})))
            )
        self.selected_index = 0 if self.actions else None
        return bool(self.actions)

    def has_forms(self) -> bool:
        return bool(self.actions)

    def export_forms(self) -> list[FakeAction]:
        return list(self.actions)

    def append_form_by_label_to_selected(self, label: str) -> None:
        self.actions.append(FakeAction(label.casefold()))
        self.selected_index = len(self.actions) - 1

    def append_form_by_label_to_last(self, label: str) -> None:
        self.append_form_by_label_to_selected(label)

    def remove_selected_form(self) -> bool:
        if self.selected_index is None:
            return False
        self.actions.pop(self.selected_index)
        self.selected_index = min(self.selected_index, len(self.actions) - 1)
        if not self.actions:
            self.selected_index = None
        return True

    def move_form_selected_up(self) -> None:
        if self.selected_index is None or self.selected_index == 0:
            return
        index = self.selected_index
        self.actions[index - 1], self.actions[index] = (
            self.actions[index],
            self.actions[index - 1],
        )
        self.selected_index -= 1

    def move_form_selected_down(self) -> None:
        if self.selected_index is None or self.selected_index == len(self.actions) - 1:
            return
        index = self.selected_index
        self.actions[index + 1], self.actions[index] = (
            self.actions[index],
            self.actions[index + 1],
        )
        self.selected_index += 1

    def enable_selected_form(self, enabled: bool) -> None:
        if self.selected_index is not None:
            self.actions[self.selected_index].fields["enabled"] = str(enabled)

    def is_form_selected(self) -> bool:
        return self.selected_index is not None

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

    def popup_menu(self, menu: ContextMenu) -> None:
        return None


def action_ids(controller: ActionListController) -> tuple[str, ...]:
    return tuple(action.action_id for action in controller.current_document.actions)
