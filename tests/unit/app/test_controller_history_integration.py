from phatch.pyWx.controller import ActionListController
from tests.unit.app.controller_history_test_support import (
    FakeAction,
    HistoryTree,
    action_ids,
)


def test_add_undo_redo_restores_document_selection_and_notifies() -> None:
    # Given
    tree = HistoryTree([FakeAction("resize")])
    controller = ActionListController(tree)
    notifications: list[tuple[bool, bool, bool]] = []
    controller.add_history_listener(
        lambda: notifications.append(
            (controller.can_undo, controller.can_redo, controller.state.dirty)
        )
    )

    # When / Then
    controller.add_action_by_label("Crop")
    assert action_ids(controller) == ("resize", "crop")
    assert tree.selected_index == 1
    assert controller.state.dirty is True
    assert controller.undo() is True
    assert action_ids(controller) == ("resize",)
    assert tree.selected_index == 0
    assert controller.state.dirty is False
    assert controller.redo() is True
    assert action_ids(controller) == ("resize", "crop")
    assert notifications == [
        (True, False, True),
        (False, True, False),
        (True, False, True),
    ]


def test_cancel_transaction_restores_tree_without_history_entry() -> None:
    # Given
    tree = HistoryTree([FakeAction("resize")])
    controller = ActionListController(tree)
    transaction = controller.begin_transaction()
    tree.actions.append(FakeAction("invalid"))

    # When
    controller.cancel_transaction(transaction)

    # Then
    assert action_ids(controller) == ("resize",)
    assert [action.action_id for action in tree.actions] == ["resize"]
    assert controller.can_undo is False


def test_remove_last_action_remains_dirty_against_nonempty_checkpoint() -> None:
    # Given
    tree = HistoryTree([FakeAction("resize")])
    controller = ActionListController(tree)

    # When
    removed = controller.remove_selected_action()

    # Then
    assert removed is True
    assert controller.current_document.actions == ()
    assert controller.state.dirty is True


def test_remove_action_marks_dirty_when_actions_remain() -> None:
    # Given
    tree = HistoryTree([FakeAction("resize"), FakeAction("crop")])
    controller = ActionListController(tree)

    # When
    removed = controller.remove_selected_action()

    # Then
    assert removed is True
    assert controller.state.has_actions is True
    assert controller.state.dirty is True


def test_noop_transaction_does_not_notify_or_create_history() -> None:
    # Given
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    notifications: list[None] = []
    controller.add_history_listener(lambda: notifications.append(None))
    transaction = controller.begin_transaction()

    # When
    changed = controller.commit_transaction(transaction)

    # Then
    assert changed is False
    assert controller.can_undo is False
    assert notifications == []


def test_mark_clean_keeps_history_and_moves_checkpoint() -> None:
    # Given
    controller = ActionListController(HistoryTree([FakeAction("resize")]))
    controller.add_action_by_label("Crop")

    # When
    controller.mark_clean()
    controller.add_action_by_label("Scale")
    controller.undo()

    # Then
    assert controller.state.dirty is False
    assert action_ids(controller) == ("resize", "crop")
    assert controller.can_undo is True


def test_description_is_an_undoable_document_edit() -> None:
    # Given
    controller = ActionListController(HistoryTree())

    # When
    controller.update_description("Changed")

    # Then
    assert controller.current_document.description == "Changed"
    assert controller.state.dirty is True
    assert controller.undo() is True
    assert controller.current_document.description != "Changed"
